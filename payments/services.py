"""
支付与费用服务层：优惠券计算/领取/使用/退回、支付流水、财务报表。

优惠券满足使用条件后按面额/折扣抵扣；押金不计入平台收入，
财务报表收入 = 租金 + 违约金 - 租金退款。
"""
import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum

from payments.models import Coupon, Payment, UserCoupon


# ==================== 优惠券 ====================

def calc_coupon_discount(coupon, amount):
    """
    计算优惠券抵扣金额：未使用优惠券、不满足门槛/失效时返回 0。
    支持传入 Coupon 模板或 UserCoupon（自动取模板）。
    """
    if coupon is None:
        return Decimal('0')
    template = coupon.coupon if hasattr(coupon, 'coupon') else coupon
    if not template.is_valid(amount):
        return Decimal('0')
    if template.discount_type == 'fixed':
        # 满减券：抵扣面额，不超过应付金额
        return min(template.value, amount)
    # 折扣券：value=8.5 表示 85 折，抵扣 = 金额 × (1 - 0.85)
    rate = template.value / Decimal('10')
    discount = amount * (Decimal('1') - rate)
    return discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_user_valid_coupons(user):
    """
    获取用户当前可用的优惠券：未使用且模板有效、满足最低门槛按 0 门槛展示。
    """
    today = datetime.date.today()
    return UserCoupon.objects.filter(
        user=user,
        is_used=False,
        coupon__is_active=True,
        coupon__start_date__lte=today,
        coupon__end_date__gte=today,
    ).select_related('coupon').order_by('-claimed_at')


def get_user_coupons(user, status=''):
    """
    按状态返回用户优惠券 queryset（供「我的优惠券」状态按钮组筛选）。
    status 为空表示全部；status 取值见 UserCoupon.STATUS_CHOICES。
    注意：UserCoupon.status 是 @property，不能用于 ORM filter，故此处用底层字段条件。
    """
    today = datetime.date.today()
    base = UserCoupon.objects.filter(user=user).select_related('coupon')
    if status == 'unused':
        return base.filter(
            is_used=False, coupon__end_date__gte=today
        ).order_by('-claimed_at')
    if status == 'used':
        return base.filter(is_used=True).order_by('-used_at')
    if status == 'expired':
        return base.filter(
            is_used=False, coupon__end_date__lt=today
        ).order_by('-claimed_at')
    return base.order_by('-claimed_at')


def get_user_coupon_by_id(user, coupon_id):
    """按 ID 获取用户可用优惠券，不存在或已使用返回 None。"""
    uc = UserCoupon.objects.filter(
        user=user, id=coupon_id, is_used=False
    ).select_related('coupon').first()
    if uc is None or not uc.coupon.is_active:
        return None
    return uc


def occupy_coupon(user_coupon, user, order):
    """下单时占用优惠券：标记为已使用并记录订单。"""
    user_coupon.is_used = True
    user_coupon.order_id = order.id
    user_coupon.used_at = datetime.datetime.now()
    user_coupon.save(update_fields=['is_used', 'order_id', 'used_at'])


def release_coupon(user_coupon_id, user):
    """取消订单后退回优惠券：恢复为未使用状态。"""
    UserCoupon.objects.filter(
        id=user_coupon_id, user=user, is_used=True
    ).update(is_used=False, order_id=None, used_at=None)


def claim_coupon(user, coupon_id):
    """
    用户领取优惠券：校验模板有效性、发行量、是否已领取。
    返回 (success, message)。
    """
    coupon = Coupon.objects.filter(pk=coupon_id, is_active=True).first()
    if coupon is None:
        return False, '优惠券不存在或已停用'
    today = datetime.date.today()
    if not (coupon.start_date <= today <= coupon.end_date):
        return False, '优惠券不在领取时间范围内'
    if coupon.claimed_count >= coupon.total_count:
        return False, '优惠券已领完'
    if UserCoupon.objects.filter(user=user, coupon=coupon).exists():
        return False, '您已领取过该优惠券'
    UserCoupon.objects.create(user=user, coupon=coupon)
    Coupon.objects.filter(pk=coupon.pk).update(claimed_count=coupon.claimed_count + 1)
    return True, '优惠券领取成功'


# ==================== 支付流水 ====================

def create_payment(order, payment_type, amount, method='模拟支付'):
    """创建支付/退款流水（模拟支付，不产生真实交易）。"""
    if amount <= 0:
        return None
    return Payment.objects.create(
        order=order,
        user=order.user,
        amount=amount,
        payment_type=payment_type,
        method=method,
        status='success',
    )


def get_user_bills(user):
    """查询用户历史消费明细（支付流水，按时间倒序）。"""
    return Payment.objects.filter(user=user).select_related('order').order_by('-created_at')


# ==================== 财务报表 ====================

def get_revenue_stats(days=14):
    """
    近 days 天收入统计：每日收入趋势与收入构成。
    收入 = 租金 + 违约金 - 租金退款（押金不计入收入）。
    """
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days - 1)
    payments = Payment.objects.filter(created_at__date__gte=start)

    # 每日收入趋势
    daily = {}
    for offset in range(days):
        day = start + datetime.timedelta(days=offset)
        rents = payments.filter(
            created_at__date=day, payment_type='rent'
        ).aggregate(s=Sum('amount'))['s'] or 0
        fines = payments.filter(
            created_at__date=day, payment_type='fine'
        ).aggregate(s=Sum('amount'))['s'] or 0
        refunds = payments.filter(
            created_at__date=day, payment_type='rent_refund'
        ).aggregate(s=Sum('amount'))['s'] or 0
        daily[day.isoformat()] = float(rents + fines - refunds)

    # 收入构成（含押金、退款展示）
    composition = {}
    for ptype, label in [
        ('rent', '租金收入'), ('deposit', '押金'), ('fine', '违约金'),
        ('deposit_refund', '押金退还'), ('rent_refund', '租金退款'),
    ]:
        value = payments.filter(payment_type=ptype).aggregate(s=Sum('amount'))['s'] or 0
        composition[label] = float(value)

    total_income = sum(daily.values())
    return {'daily': daily, 'composition': composition, 'total_income': total_income}

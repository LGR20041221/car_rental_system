"""
订单服务层：租期冲突校验、金额计算、订单创建与状态流转。

负责订单全生命周期业务：
- 租期冲突校验（边界相触允许）
- 按价格计算链组装订单金额（原价 → 动态 → 优惠券 → 应付 + 押金）
- 待支付超时取消、到期自动开始租期、超期自动标记逾期并计算违约金
"""
import datetime
import random

from django.utils import timezone

# 占用车辆时间段的订单状态（冲突校验口径）
CONFLICT_STATUSES = ['paid', 'renting', 'to_return', 'overdue', 'abnormal']
# 计入销量的订单状态（用于热门推荐，排除已取消/待支付）
SALES_STATUSES = ['paid', 'renting', 'to_return', 'completed', 'overdue', 'abnormal']


def generate_order_no():
    """生成唯一订单号：CR + 时间戳 + 随机三位数。"""
    ts = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'CR{ts}{random.randint(100, 999)}'


def check_conflict(vehicle, start_date, end_date, exclude_order=None):
    """
    校验车辆在 [取车日期, 还车日期] 区间内是否与其他有效订单冲突。

    边界相触允许：前一订单还车时间 ≤ 后一订单取车时间视为无冲突。
    返回第一个冲突订单，无冲突返回 None。
    """
    from orders.models import Order
    qs = Order.objects.filter(vehicle=vehicle, status__in=CONFLICT_STATUSES)
    if exclude_order is not None:
        qs = qs.exclude(pk=exclude_order.pk)
    # 区间重叠：已有订单的取车时间 < 新区间还车时间 且 已有订单还车时间 > 新区间取车时间
    return qs.filter(start_date__lt=end_date, end_date__gt=start_date).first()


def find_available_slot(vehicle, start_date, end_date, max_search=60):
    """
    冲突时给出可预约的最近空闲时间段。

    从目标取车日期开始向后扫描，跳过冲突区间，
    返回第一个满足需求天数的空闲 [开始日期, 结束日期]，找不到返回 (None, None)。
    """
    from orders.models import Order
    desired_days = (end_date - start_date).days + 1
    today = datetime.date.today()
    end_bound = today + datetime.timedelta(days=max_search)
    intervals = list(
        Order.objects.filter(
            vehicle=vehicle, status__in=CONFLICT_STATUSES, end_date__gte=today
        ).order_by('start_date').values_list('start_date', 'end_date')
    )
    candidate = start_date
    while candidate <= end_bound:
        slot_end = candidate + datetime.timedelta(days=desired_days - 1)
        jump = None
        for (cs, ce) in intervals:
            # 与候选区间冲突则跳到该冲突区间之后
            if cs < slot_end and ce >= candidate:
                jump = ce + datetime.timedelta(days=1)
                break
        if jump is None:
            return candidate, slot_end
        candidate = jump
    return None, None


def calculate_order_amounts(vehicle, start_date, end_date, coupon=None):
    """
    按价格计算链组装订单金额：
    原价总额 → 动态租金总额 → 优惠券抵扣 → 应付租金（最低 0）→ 押金 → 应付总额。
    """
    from payments.services import calc_coupon_discount
    from pricing.services import calculate_price, get_deposit

    price_info = calculate_price(vehicle, start_date, end_date)
    coupon_discount = calc_coupon_discount(coupon, price_info['dynamic_total'])
    payable_rent = max(price_info['dynamic_total'] - coupon_discount, 0)
    deposit = get_deposit(vehicle)
    total_amount = payable_rent + deposit
    return {
        'days': price_info['days'],
        'base_rent': price_info['base_total'],
        'dynamic_rent': price_info['dynamic_total'],
        'coupon_discount': coupon_discount,
        'payable_rent': payable_rent,
        'deposit': deposit,
        'total_amount': total_amount,
    }


def create_order(user, vehicle, start_date, end_date, pickup_location, return_location, coupon=None):
    """
    创建订单：先做租期冲突校验，再计算金额并落库，最后占用优惠券。

    返回 (order, error_message)；error_message 非空时 order 为 None。
    """
    from orders.models import Order
    from payments.services import occupy_coupon

    conflict = check_conflict(vehicle, start_date, end_date)
    if conflict:
        return None, '该车辆在所选时间段已被占用'
    amounts = calculate_order_amounts(vehicle, start_date, end_date, coupon)
    order = Order.objects.create(
        order_no=generate_order_no(),
        user=user,
        vehicle=vehicle,
        start_date=start_date,
        end_date=end_date,
        days=amounts['days'],
        pickup_location=pickup_location,
        return_location=return_location,
        base_rent=amounts['base_rent'],
        dynamic_rent=amounts['dynamic_rent'],
        coupon_id=coupon.id if coupon else None,
        coupon_name=coupon.coupon.name if coupon else '',
        coupon_discount=amounts['coupon_discount'],
        payable_rent=amounts['payable_rent'],
        deposit=amounts['deposit'],
        total_amount=amounts['total_amount'],
        status='pending',
    )
    # 占用用户优惠券
    if coupon:
        occupy_coupon(coupon, user, order)
    return order, None


def process_order_statuses():
    """
    自动处理订单状态：
    1. 待支付订单超过时限自动取消；
    2. 已支付订单到取车日自动进入「租赁中」；
    3. 租赁中订单超过还车日期自动标记「已逾期」并计算违约金。
    """
    from orders.models import Order
    from payments.services import create_payment
    from pricing.services import get_fine, get_setting

    now = timezone.now()
    # USE_TZ=False 下 timezone.now() 返回 naive 本地时间，直接取日期；
    # 不可用 timezone.localdate()（对 naive datetime 会抛 ValueError）。
    today = now.date()
    # 1. 待支付超时自动取消
    minutes = int(get_setting('auto_cancel_minutes'))
    threshold = now - datetime.timedelta(minutes=minutes)
    for order in Order.objects.filter(status='pending', created_at__lte=threshold):
        order.status = 'cancelled'
        order.cancelled_at = now
        order.cancel_reason = '超时未支付，系统自动取消'
        order.save(update_fields=['status', 'cancelled_at', 'cancel_reason', 'updated_at'])
    # 2. 已支付订单到期自动开始租期
    for order in Order.objects.filter(status='paid', start_date__lte=today):
        order.status = 'renting'
        order.pickup_at = order.pickup_at or now
        order.save(update_fields=['status', 'pickup_at', 'updated_at'])
    # 3. 租赁中订单超期自动标记逾期并计算违约金
    for order in Order.objects.filter(status='renting', end_date__lt=today):
        overdue_days = (today - order.end_date).days
        fine_date = order.end_date + datetime.timedelta(days=1)
        fine = get_fine(order.vehicle, overdue_days, fine_date)
        order.status = 'overdue'
        order.is_overdue = True
        order.fine = fine
        order.save(update_fields=['status', 'is_overdue', 'fine', 'updated_at'])
        # 记录违约金流水
        create_payment(order, 'fine', fine, method='逾期违约金')


def pay_order(order):
    """
    订单支付（模拟支付）：待支付 → 已支付，记录租金与押金流水。
    """
    from payments.services import create_payment
    now = timezone.now()
    order.status = 'paid'
    order.paid_at = now
    order.save(update_fields=['status', 'paid_at', 'updated_at'])
    create_payment(order, 'rent', order.payable_rent, method='在线支付-租金')
    create_payment(order, 'deposit', order.deposit, method='在线支付-押金')


def cancel_order(order, reason='', by_admin=False):
    """
    取消订单：待支付/已支付订单可取消；
    已支付订单退款（租金+押金），优惠券退回用户。
    """
    from payments.services import create_payment, release_coupon
    now = timezone.now()
    # 已支付的订单执行模拟退款
    if order.status == 'paid':
        create_payment(order, 'rent_refund', order.payable_rent, method='取消订单-租金退款')
        create_payment(order, 'deposit_refund', order.deposit, method='取消订单-押金退款')
    order.status = 'cancelled'
    order.cancelled_at = now
    order.cancel_reason = reason or ('管理员取消订单' if by_admin else '用户取消订单')
    order.save(update_fields=['status', 'cancelled_at', 'cancel_reason', 'updated_at'])
    # 退回优惠券
    if order.coupon_id:
        release_coupon(order.coupon_id, order.user)


def confirm_return(order):
    """
    用户确认还车：租赁中/已逾期 → 待还车，等待管理员核验。
    """
    now = timezone.now()
    order.status = 'to_return'
    order.return_at = now
    order.save(update_fields=['status', 'return_at', 'updated_at'])


def complete_order(order):
    """
    管理员核验完成订单：待还车/租赁中/已逾期 → 已完成，自动退还押金。
    """
    from payments.services import create_payment
    now = timezone.now()
    order.status = 'completed'
    order.completed_at = now
    order.deposit_returned = True
    order.save(update_fields=['status', 'completed_at', 'deposit_returned', 'updated_at'])
    create_payment(order, 'deposit_refund', order.deposit, method='还车核验-押金退还')


def apply_extension(order, new_end_date):
    """
    用户申请续租：记录续租目标日期并计算新增租金，进入待审批状态。
    """
    from pricing.services import calculate_price
    extension_start = order.end_date + datetime.timedelta(days=1)
    price_info = calculate_price(order.vehicle, extension_start, new_end_date)
    order.extend_to_date = new_end_date
    order.extension_status = 'pending'
    order.extend_rent = price_info['dynamic_total']
    order.save(update_fields=['extend_to_date', 'extension_status', 'extend_rent', 'updated_at'])


def approve_extension(order):
    """
    管理员批准续租：延长还车日期，新增租金计入订单并生成补款流水。
    """
    from payments.services import create_payment
    order.end_date = order.extend_to_date
    order.days = (order.end_date - order.start_date).days + 1
    order.dynamic_rent += order.extend_rent
    order.payable_rent += order.extend_rent
    order.total_amount = order.payable_rent + order.deposit
    order.extension_status = 'approved'
    order.save(update_fields=[
        'end_date', 'days', 'dynamic_rent', 'payable_rent',
        'total_amount', 'extension_status', 'updated_at',
    ])
    create_payment(order, 'rent', order.extend_rent, method='续租补款')


def reject_extension(order):
    """管理员驳回续租：清空续租申请。"""
    order.extend_to_date = None
    order.extension_status = 'rejected'
    order.extend_rent = 0
    order.save(update_fields=['extend_to_date', 'extension_status', 'extend_rent', 'updated_at'])


def mark_abnormal(order):
    """管理员将逾期/异常订单标记为异常处理。"""
    order.status = 'abnormal'
    order.save(update_fields=['status', 'updated_at'])

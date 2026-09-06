"""
支付与费用数据模型。

- Coupon：优惠券模板（平台发放，用户领取）
- UserCoupon：用户领取的优惠券（记录使用状态）
- Payment：支付/退款流水（租金、押金、违约金、退款）
"""
import datetime

from django.db import models

from orders.models import Order
from users.models import User


class Coupon(models.Model):
    """优惠券模板：满减券或折扣券，由管理员创建。"""
    TYPE_CHOICES = [
        ('fixed', '满减券'),
        ('discount', '折扣券'),
    ]
    name = models.CharField('优惠券名称', max_length=50)
    discount_type = models.CharField('优惠类型', max_length=20, choices=TYPE_CHOICES, default='fixed')
    value = models.DecimalField(
        '面额/折扣', max_digits=10, decimal_places=2,
        help_text='满减券填写抵扣金额(元)；折扣券填写折扣（如 8.5 表示 85 折）',
    )
    min_amount = models.DecimalField(
        '使用门槛(元)', max_digits=10, decimal_places=2, default=0,
        help_text='订单应付租金满该金额可用，0 表示无门槛',
    )
    total_count = models.PositiveIntegerField('发行总量', default=100)
    claimed_count = models.PositiveIntegerField('已领取数量', default=0)
    start_date = models.DateField('生效日期')
    end_date = models.DateField('失效日期')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 't_coupon'
        verbose_name = '优惠券'

    def __str__(self):
        return self.name

    @property
    def type_text(self):
        """优惠类型中文文案。"""
        return dict(self.TYPE_CHOICES).get(self.discount_type, self.discount_type)

    @property
    def value_text(self):
        """面额/折扣展示文案。"""
        if self.discount_type == 'fixed':
            return f'¥{self.value}'
        return f'{self.value}折'

    def is_valid(self, amount):
        """
        优惠券是否有效：启用、在有效期内、未领完、满足使用门槛。
        """
        today = datetime.date.today()
        return (
            self.is_active
            and self.start_date <= today <= self.end_date
            and self.claimed_count < self.total_count
            and amount >= self.min_amount
        )


class UserCoupon(models.Model):
    """用户领取的优惠券。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_coupons', verbose_name='用户')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='user_coupons', verbose_name='优惠券模板')
    order_id = models.IntegerField('使用订单ID', null=True, blank=True)
    is_used = models.BooleanField('是否已使用', default=False)
    claimed_at = models.DateTimeField('领取时间', auto_now_add=True)
    used_at = models.DateTimeField('使用时间', null=True, blank=True)

    class Meta:
        db_table = 't_user_coupon'
        verbose_name = '用户优惠券'
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f'{self.user.username}-{self.coupon.name}'


class Payment(models.Model):
    """支付/退款流水：租金、押金、违约金、押金退还、租金退款。"""
    TYPE_CHOICES = [
        ('rent', '租金'),
        ('deposit', '押金'),
        ('fine', '违约金'),
        ('deposit_refund', '押金退还'),
        ('rent_refund', '租金退款'),
    ]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='payments', verbose_name='订单')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments', verbose_name='用户')
    amount = models.DecimalField('金额(元)', max_digits=10, decimal_places=2)
    payment_type = models.CharField('类型', max_length=20, choices=TYPE_CHOICES)
    method = models.CharField('支付/退款方式', max_length=50, default='模拟支付')
    status = models.CharField('状态', max_length=20, default='success')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 't_payment'
        verbose_name = '支付流水'

    def __str__(self):
        return f'{self.order.order_no}-{self.payment_type}'

    @property
    def type_text(self):
        """类型中文文案。"""
        return dict(self.TYPE_CHOICES).get(self.payment_type, self.payment_type)

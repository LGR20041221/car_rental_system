"""
租赁订单模型。

覆盖从选车下单到还车结算的完整租赁生命周期，
记录费用构成（原价/动态/优惠券/应付/押金/违约金）与关键时间节点。
优惠券通过 coupon_id 冗余关联（避免跨 app 外键），金额快照存于 coupon_name/coupon_discount。
"""
from django.db import models

from users.models import User
from vehicles.models import Vehicle


class Order(models.Model):
    """租赁订单。"""
    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('renting', '租赁中'),
        ('to_return', '待还车'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('overdue', '已逾期'),
        ('abnormal', '异常处理'),
    ]
    EXTENSION_STATUS = [
        ('none', '无'),
        ('pending', '待审批'),
        ('approved', '已批准'),
        ('rejected', '已驳回'),
    ]
    order_no = models.CharField('订单号', max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders', verbose_name='下单用户')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='orders', verbose_name='租赁车辆')
    start_date = models.DateField('取车日期')
    end_date = models.DateField('还车日期')
    days = models.PositiveIntegerField('租期(天)')
    pickup_location = models.CharField('取车地点', max_length=100)
    return_location = models.CharField('还车地点', max_length=100)
    # 费用构成
    base_rent = models.DecimalField('原价租金(元)', max_digits=10, decimal_places=2)
    dynamic_rent = models.DecimalField('动态租金(元)', max_digits=10, decimal_places=2)
    coupon_id = models.IntegerField('优惠券ID', null=True, blank=True)
    coupon_name = models.CharField('优惠券名称', max_length=50, blank=True, default='')
    coupon_discount = models.DecimalField('优惠券抵扣(元)', max_digits=10, decimal_places=2, default=0)
    payable_rent = models.DecimalField('应付租金(元)', max_digits=10, decimal_places=2)
    deposit = models.DecimalField('押金(元)', max_digits=10, decimal_places=2)
    fine = models.DecimalField('违约金(元)', max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField('应付总额(元)', max_digits=10, decimal_places=2)
    # 状态流转
    status = models.CharField('订单状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    is_overdue = models.BooleanField('是否逾期', default=False)
    deposit_returned = models.BooleanField('押金是否已退还', default=False)
    # 续租
    extend_to_date = models.DateField('续租目标还车日期', null=True, blank=True)
    extension_status = models.CharField(
        '续租审批状态', max_length=20, choices=EXTENSION_STATUS, default='none'
    )
    extend_rent = models.DecimalField('续租增加租金(元)', max_digits=10, decimal_places=2, default=0)
    # 其他
    cancel_reason = models.CharField('取消原因', max_length=200, blank=True, default='')
    remark = models.TextField('备注', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    paid_at = models.DateTimeField('支付时间', null=True, blank=True)
    pickup_at = models.DateTimeField('取车时间', null=True, blank=True)
    return_at = models.DateTimeField('确认还车时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    cancelled_at = models.DateTimeField('取消时间', null=True, blank=True)

    class Meta:
        db_table = 't_order'
        verbose_name = '租赁订单'

    def __str__(self):
        return self.order_no

    @property
    def status_text(self):
        """订单状态中文文案。"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def extension_status_text(self):
        """续租审批状态中文文案。"""
        return dict(self.EXTENSION_STATUS).get(self.extension_status, self.extension_status)

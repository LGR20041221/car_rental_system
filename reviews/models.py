"""
评价模型。

用户对已完成的订单进行 1-5 星评分及文字评价，
同一订单可多次评价（ForeignKey），管理员可隐藏不当评价。
"""
from django.db import models

from orders.models import Order
from users.models import User
from vehicles.models import Vehicle


class Review(models.Model):
    """车辆评价。"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='reviews', verbose_name='关联订单')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name='评价用户')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='reviews', verbose_name='被评车辆')
    rating = models.PositiveSmallIntegerField('评分', default=5, help_text='1-5 星')
    content = models.TextField('评价内容')
    is_hidden = models.BooleanField('是否隐藏', default=False)
    created_at = models.DateTimeField('评价时间', auto_now_add=True)

    class Meta:
        db_table = 't_review'
        verbose_name = '车辆评价'

    def __str__(self):
        return f'{self.user.username} 对 {self.vehicle.model_name} 的评价'

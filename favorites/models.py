"""
收藏模型。

用户可收藏感兴趣车辆，收藏数据同时为热门车辆分析和相似推荐提供热度参考。
"""
from django.db import models

from users.models import User
from vehicles.models import Vehicle


class Favorite(models.Model):
    """用户收藏记录。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='用户')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='favorites', verbose_name='车辆')
    created_at = models.DateTimeField('收藏时间', auto_now_add=True)

    class Meta:
        db_table = 't_favorite'
        verbose_name = '收藏记录'
        unique_together = ('user', 'vehicle')

    def __str__(self):
        return f'{self.user.username} 收藏 {self.vehicle.model_name}'

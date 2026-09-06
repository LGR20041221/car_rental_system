"""
消息通知模型。

- Notification：订单状态变更等用户消息（区分已读/未读）
- Announcement：平台系统公告（导航栏公告页统一查看）
"""
from django.db import models

from users.models import User


class Notification(models.Model):
    """用户消息通知。"""
    TYPE_CHOICES = [
        ('order', '订单通知'),
        ('system', '系统通知'),
        ('announcement', '公告通知'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='接收用户')
    title = models.CharField('标题', max_length=100)
    content = models.TextField('内容', blank=True)
    type = models.CharField('类型', max_length=20, choices=TYPE_CHOICES, default='order')
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 't_notification'
        verbose_name = '消息通知'

    def __str__(self):
        return f'{self.user.username}-{self.title}'


class Announcement(models.Model):
    """系统公告：由管理员发布。"""
    title = models.CharField('公告标题', max_length=100)
    content = models.TextField('公告内容')
    publisher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='announcements', verbose_name='发布人',
    )
    is_top = models.BooleanField('是否置顶', default=False)
    is_active = models.BooleanField('是否发布', default=True)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 't_announcement'
        verbose_name = '系统公告'

    def __str__(self):
        return self.title

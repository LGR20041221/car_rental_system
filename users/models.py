"""
用户模型。

继承 Django AbstractUser，扩展手机号、管理员标记、头像等字段。
用户名、手机号、邮箱三个字段均全局唯一。
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """系统用户：普通用户与管理员共用一张表，通过 is_admin 区分角色。"""
    phone = models.CharField('手机号', max_length=20, unique=True)
    email = models.EmailField('邮箱', max_length=100, unique=True)
    is_admin = models.BooleanField('是否管理员', default=False)
    avatar = models.ImageField('头像', upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 't_user'
        verbose_name = '用户'

    def __str__(self):
        """返回用户可读标识。"""
        return f'{self.username}({self.phone})'

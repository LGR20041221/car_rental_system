from django.apps import AppConfig


class UsersConfig(AppConfig):
    """用户管理应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = '用户管理'

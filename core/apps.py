from django.apps import AppConfig


class CoreConfig(AppConfig):
    """公共应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = '公共应用'

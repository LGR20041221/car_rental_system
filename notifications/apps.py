from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """消息通知应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = '消息通知'

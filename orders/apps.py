from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """租赁订单应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    verbose_name = '租赁订单'

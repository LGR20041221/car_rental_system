from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """支付与费用应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = '支付与费用'

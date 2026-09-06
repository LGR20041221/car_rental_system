from django.apps import AppConfig


class PricingConfig(AppConfig):
    """动态定价应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pricing'
    verbose_name = '动态定价'

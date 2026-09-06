from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    """评价应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviews'
    verbose_name = '评价管理'

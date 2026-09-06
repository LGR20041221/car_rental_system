from django.apps import AppConfig


class FavoritesConfig(AppConfig):
    """收藏应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'favorites'
    verbose_name = '收藏管理'

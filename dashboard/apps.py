from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """运营数据可视化应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = '运营数据'

from django.apps import AppConfig


class VehiclesConfig(AppConfig):
    """车辆管理应用配置。"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vehicles'
    verbose_name = '车辆管理'

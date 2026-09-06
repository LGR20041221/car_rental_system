"""ASGI 入口：支持异步协议，生产环境可结合 daphne 部署。"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'car_rental_system.settings')

application = get_asgi_application()

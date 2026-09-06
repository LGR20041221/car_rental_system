"""WSGI 入口：用于生产环境部署（gunicorn / waitress 等）。"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'car_rental_system.settings')

application = get_wsgi_application()

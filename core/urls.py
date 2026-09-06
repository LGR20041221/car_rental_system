"""
core 应用路由：首页。
"""
from django.urls import path

from core import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
]

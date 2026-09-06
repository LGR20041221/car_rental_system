"""
dashboard 应用路由：管理端仪表盘、数据大屏、图表数据接口。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard/', views.admin_data_screen, name='admin_data_screen'),
    path('admin/dashboard/data/', views.admin_data_api, name='admin_data_api'),
]

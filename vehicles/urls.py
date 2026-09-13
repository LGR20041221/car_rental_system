"""
vehicles 应用路由：前台车辆浏览 + 管理端车辆/品牌/分类维护。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from vehicles import views

app_name = 'vehicles'

urlpatterns = [
    # 前台首页
    path('', views.home, name='home'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    # 管理端：车辆
    path('admin/vehicles/', views.admin_vehicle_list, name='admin_vehicle_list'),
    path('admin/vehicles/create/', views.admin_vehicle_create, name='admin_vehicle_create'),
    path('admin/vehicles/<int:vehicle_id>/edit/', views.admin_vehicle_edit, name='admin_vehicle_edit'),
    path('admin/vehicles/<int:vehicle_id>/delete/', views.admin_vehicle_delete, name='admin_vehicle_delete'),
    # 图片管理已并入车辆编辑页，此处仅保留上传、删除、设为主图三个动作
    path('admin/vehicles/<int:vehicle_id>/images/upload/', views.admin_vehicle_image_upload, name='admin_vehicle_image_upload'),
    path('admin/vehicles/images/<int:image_id>/delete/', views.admin_vehicle_image_delete, name='admin_vehicle_image_delete'),
    path('admin/vehicles/images/<int:image_id>/set-cover/', views.admin_vehicle_image_set_cover, name='admin_vehicle_image_set_cover'),
    # 管理端：品牌
    path('admin/vehicles/brands/', views.admin_brand_list, name='admin_brand_list'),
    path('admin/vehicles/brands/create/', views.admin_brand_create, name='admin_brand_create'),
    path('admin/vehicles/brands/<int:brand_id>/edit/', views.admin_brand_edit, name='admin_brand_edit'),
    path('admin/vehicles/brands/<int:brand_id>/delete/', views.admin_brand_delete, name='admin_brand_delete'),
    # 管理端：分类
    path('admin/vehicles/categories/', views.admin_category_list, name='admin_category_list'),
    path('admin/vehicles/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('admin/vehicles/categories/<int:category_id>/edit/', views.admin_category_edit, name='admin_category_edit'),
    path('admin/vehicles/categories/<int:category_id>/delete/', views.admin_category_delete, name='admin_category_delete'),
]

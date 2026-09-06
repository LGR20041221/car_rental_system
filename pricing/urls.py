"""
pricing 应用路由：价格预览 + 管理端定价规则。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from pricing import views

app_name = 'pricing'

urlpatterns = [
    # 价格预览接口（下单确认页调用）
    path('price-preview/', views.price_preview, name='price_preview'),
    # 管理端定价规则
    path('admin/pricing/', views.admin_pricing_list, name='admin_pricing_list'),
    path('admin/pricing/create/', views.admin_pricing_create, name='admin_pricing_create'),
    path('admin/pricing/<int:rule_id>/edit/', views.admin_pricing_edit, name='admin_pricing_edit'),
    path('admin/pricing/<int:rule_id>/toggle/', views.admin_pricing_toggle, name='admin_pricing_toggle'),
    path('admin/pricing/<int:rule_id>/delete/', views.admin_pricing_delete, name='admin_pricing_delete'),
    # 管理端系统设置（归属 dashboard 菜单，此处提供视图）
    path('admin/settings/', views.admin_settings, name='admin_settings'),
]

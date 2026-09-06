"""
orders 应用路由：用户下单操作 + 管理端订单管理。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from orders import views

app_name = 'orders'

urlpatterns = [
    # 用户端
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/pay/', views.order_pay, name='order_pay'),
    path('orders/<int:order_id>/cancel/', views.order_cancel, name='order_cancel'),
    path('orders/<int:order_id>/extend/', views.order_extend, name='order_extend'),
    path('orders/<int:order_id>/confirm-return/', views.order_confirm_return, name='order_confirm_return'),
    path('profile/orders/', views.my_orders, name='my_orders'),
    # 管理端
    path('admin/orders/', views.admin_order_list, name='admin_order_list'),
    path('admin/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/<int:order_id>/cancel/', views.admin_order_cancel, name='admin_order_cancel'),
    path('admin/orders/<int:order_id>/verify/', views.admin_order_verify, name='admin_order_verify'),
    path('admin/orders/<int:order_id>/force-return/', views.admin_order_force_return, name='admin_order_force_return'),
    path('admin/orders/<int:order_id>/abnormal/', views.admin_order_abnormal, name='admin_order_abnormal'),
    path('admin/orders/<int:order_id>/extend-approve/', views.admin_order_extend_approve, name='admin_order_extend_approve'),
    path('admin/orders/<int:order_id>/extend-reject/', views.admin_order_extend_reject, name='admin_order_extend_reject'),
]

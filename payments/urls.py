"""
payments 应用路由：用户优惠券/账单 + 管理端优惠券/财务/退款。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from payments import views

app_name = 'payments'

urlpatterns = [
    # 用户端
    path('profile/coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/<int:coupon_id>/claim/', views.coupon_claim, name='coupon_claim'),
    path('profile/bills/', views.bill_list, name='bill_list'),
    # 管理端：优惠券
    path('admin/coupons/', views.admin_coupon_list, name='admin_coupon_list'),
    path('admin/coupons/create/', views.admin_coupon_create, name='admin_coupon_create'),
    path('admin/coupons/<int:coupon_id>/edit/', views.admin_coupon_edit, name='admin_coupon_edit'),
    path('admin/coupons/<int:coupon_id>/toggle/', views.admin_coupon_toggle, name='admin_coupon_toggle'),
    path('admin/coupons/<int:coupon_id>/delete/', views.admin_coupon_delete, name='admin_coupon_delete'),
    # 管理端：财务
    path('admin/finance/', views.admin_finance, name='admin_finance'),
    path('admin/finance/refunds/', views.admin_refund_list, name='admin_refund_list'),
    path('admin/finance/refunds/<int:order_id>/process/', views.admin_refund_process, name='admin_refund_process'),
]

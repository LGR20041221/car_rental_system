"""
users 应用路由：认证、个人中心、管理端用户维护。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    # 认证相关
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('send-code/', views.send_code, name='send_code'),
    # 个人中心
    path('profile/', views.profile_home, name='profile_home'),
    path('profile/info/', views.profile_info, name='profile_info'),
    path('profile/password/', views.change_password, name='change_password'),
    # 管理端个人中心
    path('admin/profile/info/', views.admin_profile_info, name='admin_profile_info'),
    path('admin/profile/password/', views.admin_change_password, name='admin_change_password'),
    # 管理端用户管理
    path('admin/users/', views.admin_user_list, name='admin_user_list'),
    path('admin/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('admin/users/<int:user_id>/toggle/', views.admin_user_toggle, name='admin_user_toggle'),
]

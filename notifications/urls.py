"""
notifications 应用路由：消息中心、系统公告、管理端公告维护。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from notifications import views

app_name = 'notifications'

urlpatterns = [
    # 用户端：消息中心
    path('profile/notifications/', views.notification_list, name='list'),
    path('notifications/<int:notification_id>/read/', views.mark_read, name='mark_read'),
    path('notifications/read-all/', views.mark_all_read, name='mark_all_read'),
    # 用户端：系统公告
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    # 管理端：公告管理
    path('admin/announcements/', views.admin_announcement_list, name='admin_announcement_list'),
    path('admin/announcements/create/', views.admin_announcement_create, name='admin_announcement_create'),
    path('admin/announcements/<int:announcement_id>/edit/', views.admin_announcement_edit, name='admin_announcement_edit'),
    path('admin/announcements/<int:announcement_id>/delete/', views.admin_announcement_delete, name='admin_announcement_delete'),
    path('admin/announcements/<int:announcement_id>/top/', views.admin_announcement_toggle_top, name='admin_announcement_toggle_top'),
]

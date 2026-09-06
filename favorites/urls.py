"""
favorites 应用路由：用户收藏 + 管理端收藏统计。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from favorites import views

app_name = 'favorites'

urlpatterns = [
    # 用户端
    path('favorites/toggle/', views.favorite_toggle, name='toggle'),
    path('favorites/batch-remove/', views.favorite_batch_remove, name='batch_remove'),
    path('profile/favorites/', views.favorite_list, name='list'),
    # 管理端
    path('admin/favorites/', views.admin_favorite_stats, name='admin_stats'),
]

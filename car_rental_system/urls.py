"""
项目根路由配置。

用户端与管理端路由分别挂载：管理端统一以 /admin/ 开头。
"""
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    # 用户端（首页路由由 vehicles.urls 的 path('', views.home, name='home') 提供）
    path('', include('users.urls')),
    path('', include('vehicles.urls')),
    path('', include('orders.urls')),
    path('', include('payments.urls')),
    path('', include('reviews.urls')),
    path('', include('favorites.urls')),
    path('', include('notifications.urls')),
    # 管理端（管理端路由统一以 /admin/ 开头，见各应用 urls.py）
    path('', include('pricing.urls')),
    path('', include('dashboard.urls')),
]

# 开发阶段提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()

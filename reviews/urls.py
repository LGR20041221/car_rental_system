"""
reviews 应用路由：用户评价 + 管理端评价管理。
管理端路由统一以 /admin/ 开头。
"""
from django.urls import path

from reviews import views

app_name = 'reviews'

urlpatterns = [
    # 用户端
    path('reviews/submit/<int:order_id>/', views.review_submit, name='review_submit'),
    path('profile/reviews/', views.my_reviews, name='my_reviews'),
    # 管理端
    path('admin/reviews/', views.admin_review_list, name='admin_review_list'),
    path('admin/reviews/<int:review_id>/toggle/', views.admin_review_toggle, name='admin_review_toggle'),
]

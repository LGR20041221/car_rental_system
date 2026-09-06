"""
公共视图：首页。

首页包含轮播图、搜索框、热门推荐（销量 TOP10，每行 5 个）。
"""
from django.shortcuts import render

from core.services import get_banner_vehicles, get_hot_vehicles, mark_favorite_status
from vehicles.models import Brand, Category


def home(request):
    """
    首页：展示轮播车辆、搜索入口、热门推荐 TOP10 与最新公告。
    """
    banners = get_banner_vehicles(limit=3)
    hot_vehicles = get_hot_vehicles(limit=10)
    mark_favorite_status(hot_vehicles, request.current_user)
    context = {
        'banners': banners,
        'hot_vehicles': hot_vehicles,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
    }
    return render(request, 'core/home.html', context)

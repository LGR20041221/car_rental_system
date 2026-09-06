"""
运营数据可视化视图：管理端仪表盘、数据大屏与图表数据接口。
"""
import json

from django.http import JsonResponse
from django.shortcuts import render

from core.decorators import admin_required
from dashboard import services as stats_services
from orders import services as order_services


@admin_required
def admin_dashboard(request):
    """
    管理端仪表盘：展示平台核心数据概览与最新订单、快捷入口。
    """
    order_services.process_order_statuses()
    stats = stats_services.get_dashboard_stats()
    recent_orders = stats_services.get_recent_orders(limit=8)
    context = {
        'stats': stats,
        'recent_orders': recent_orders,
        'total_income': stats_services.get_income_total(),
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@admin_required
def admin_data_screen(request):
    """
    数据大屏：综合展示平台核心运营指标（ECharts 可视化）。
    """
    order_services.process_order_statuses()
    stats = stats_services.get_dashboard_stats()
    context = {
        'stats': stats,
        'total_income': stats_services.get_income_total(),
    }
    return render(request, 'dashboard/admin_data_screen.html', context)


@admin_required
def admin_data_api(request):
    """
    数据大屏图表数据接口（AJAX）：返回订单趋势、收入构成、热门车型、
    车辆利用率、用户增长等图表数据。
    """
    data = {
        'order_trend': stats_services.get_order_trend(14),
        'income_trend': stats_services.get_income_trend(14),
        'revenue_composition': stats_services.get_revenue_composition(),
        'hot_vehicles': stats_services.get_hot_vehicles(90),
        'utilization': stats_services.get_vehicle_utilization(),
        'user_growth': stats_services.get_user_growth(30),
        'stats': stats_services.get_dashboard_stats(),
        'total_income': stats_services.get_income_total(),
    }
    return JsonResponse(data)

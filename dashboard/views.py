"""
运营数据可视化视图：管理端仪表盘、数据大屏与图表数据接口。
"""
from django.http import JsonResponse
from django.shortcuts import render

from dashboard import services as stats_services
from orders import services as order_services
from users.decorators import admin_required


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


def _serialize_latest(orders):
    """把最新订单序列化为大屏滚动列表所需结构。"""
    return [
        {
            'order_no': o.order_no,
            'user': o.user.username,
            'vehicle': f'{o.vehicle.brand.name} {o.vehicle.model_name}',
            'amount': float(o.total_amount),
            'status': o.status,
            'status_text': o.status_text,
            'created_at': o.created_at.strftime('%m-%d %H:%M'),
        }
        for o in orders
    ]


@admin_required
def admin_data_screen(request):
    """
    数据大屏：只渲染页面骨架，数据由前端调用 admin_data_api 拉取。
    """
    order_services.process_order_statuses()
    return render(request, 'dashboard/admin_data_screen.html')


@admin_required
def admin_data_api(request):
    """
    数据大屏图表数据接口（AJAX）：返回 KPI、订单/收入趋势、收入构成、
    品牌分布、订单状态分布、热门车型、车辆利用率、用户增长与最新订单。
    """
    data = {
        'kpis': stats_services.get_screen_kpis(),
        'order_trend': stats_services.get_order_trend(14),
        'income_trend': stats_services.get_income_trend(14),
        'revenue_composition': stats_services.get_revenue_composition(),
        'brand_share': stats_services.get_brand_share(90),
        'status_distribution': stats_services.get_order_status_distribution(),
        'hot_vehicles': stats_services.get_hot_vehicles(90),
        'utilization': stats_services.get_vehicle_utilization(),
        'user_growth': stats_services.get_user_growth(30),
        'stats': stats_services.get_dashboard_stats(),
        'total_income': stats_services.get_income_total(),
        'latest_orders': _serialize_latest(stats_services.get_recent_orders(limit=10)),
    }
    return JsonResponse(data)

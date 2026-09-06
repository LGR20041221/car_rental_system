"""
运营数据服务：为仪表盘与数据大屏提供统计指标。

- 仪表盘：今日订单/今日收入/在线用户/车辆总数等概览
- 数据大屏：订单趋势、收入构成、热门车型、车辆利用率、用户增长

统计统一采用时区安全的 datetime 区间查询（见 core.datetime_utils）。
"""
import datetime

from django.db.models import Count, Sum

from core.datetime_utils import day_end, day_start
from orders.models import Order
from payments.models import Payment
from users.models import User
from vehicles.models import Category, Vehicle

# 占用状态（用于车辆利用率）
OCCUPIED_STATUSES = ['paid', 'renting', 'to_return', 'overdue', 'abnormal']


def _income_on(day):
    """某日平台收入 = 租金 + 违约金 - 租金退款（押金不计收入）。"""
    rents = Payment.objects.filter(
        created_at__gte=day_start(day), created_at__lt=day_end(day),
        payment_type='rent',
    ).aggregate(s=Sum('amount'))['s'] or 0
    fines = Payment.objects.filter(
        created_at__gte=day_start(day), created_at__lt=day_end(day),
        payment_type='fine',
    ).aggregate(s=Sum('amount'))['s'] or 0
    refunds = Payment.objects.filter(
        created_at__gte=day_start(day), created_at__lt=day_end(day),
        payment_type='rent_refund',
    ).aggregate(s=Sum('amount'))['s'] or 0
    return float(rents + fines - refunds)


def get_dashboard_stats():
    """仪表盘核心统计指标。"""
    today = datetime.date.today()
    return {
        'today_orders': Order.objects.filter(
            created_at__gte=day_start(today), created_at__lt=day_end(today)
        ).count(),
        'today_income': _income_on(today),
        'total_users': User.objects.count(),
        'total_vehicles': Vehicle.objects.filter(status__in=['available', 'renting']).count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'renting_orders': Order.objects.filter(status='renting').count(),
        'overdue_orders': Order.objects.filter(status='overdue').count(),
    }


def get_income_total():
    """平台累计收入（租金+违约金-租金退款，近90天）。"""
    start = datetime.date.today() - datetime.timedelta(days=90)
    payments = Payment.objects.filter(created_at__gte=day_start(start))
    rents = payments.filter(payment_type='rent').aggregate(s=Sum('amount'))['s'] or 0
    fines = payments.filter(payment_type='fine').aggregate(s=Sum('amount'))['s'] or 0
    refunds = payments.filter(payment_type='rent_refund').aggregate(s=Sum('amount'))['s'] or 0
    return float(rents + fines - refunds)


def get_order_trend(days=14):
    """近 days 天订单量趋势。"""
    today = datetime.date.today()
    result = []
    for offset in range(days - 1, -1, -1):
        day = today - datetime.timedelta(days=offset)
        result.append({
            'date': day.strftime('%m-%d'),
            'count': Order.objects.filter(
                created_at__gte=day_start(day), created_at__lt=day_end(day)
            ).count(),
        })
    return result


def get_income_trend(days=14):
    """近 days 天收入趋势。"""
    today = datetime.date.today()
    result = []
    for offset in range(days - 1, -1, -1):
        day = today - datetime.timedelta(days=offset)
        result.append({'date': day.strftime('%m-%d'), 'income': _income_on(day)})
    return result


def get_revenue_composition():
    """收入构成（近90天各类金额）。"""
    start = datetime.date.today() - datetime.timedelta(days=90)
    payments = Payment.objects.filter(created_at__gte=day_start(start))
    labels = ['租金收入', '押金', '违约金', '押金退还', '租金退款']
    values = []
    for ptype in ['rent', 'deposit', 'fine', 'deposit_refund', 'rent_refund']:
        value = payments.filter(payment_type=ptype).aggregate(s=Sum('amount'))['s'] or 0
        values.append(float(value))
    return {'labels': labels, 'values': values}


def get_hot_vehicles(days=90):
    """热门车型排行：近 days 天订单量 TOP10。"""
    start = datetime.date.today() - datetime.timedelta(days=days)
    rows = (
        Vehicle.objects.filter(orders__created_at__gte=day_start(start))
        .annotate(order_count=Count('orders'))
        .order_by('-order_count')[:10]
    )
    return {
        'names': [f'{v.brand.name} {v.model_name}' for v in rows],
        'counts': [v.order_count for v in rows],
    }


def get_vehicle_utilization():
    """各车型利用率：占用中车辆数 / 在运营车辆数。"""
    result = []
    for category in Category.objects.all():
        vehicles = category.vehicles.filter(status__in=['available', 'renting'])
        total = vehicles.count()
        occupied = vehicles.filter(status='renting').count()
        rate = round(occupied / total * 100, 1) if total else 0
        result.append({'name': category.name, 'rate': rate})
    return result


def get_user_growth(days=30):
    """近 days 天用户增长趋势（累计注册数）。"""
    today = datetime.date.today()
    result = []
    for offset in range(days - 1, -1, -1):
        day = today - datetime.timedelta(days=offset)
        count = User.objects.filter(created_at__lt=day_end(day)).count()
        result.append({'date': day.strftime('%m-%d'), 'count': count})
    return result


def get_recent_orders(limit=8):
    """最新订单列表。"""
    return Order.objects.select_related('user', 'vehicle__brand').order_by('-created_at')[:limit]

"""
车辆服务层：前台车辆筛选与占用日期查询。

车辆列表页与详情页可展示已占用日期，辅助用户提前避开车期冲突。
"""
import datetime

from django.db.models import Q

from vehicles.models import Vehicle


def get_vehicle_list(params):
    """
    根据筛选条件查询可租车辆列表。

    支持关键词、分类、品牌、燃油类型、价格区间筛选与多种排序方式。
    """
    qs = Vehicle.objects.filter(status='available').select_related('brand', 'category')
    keyword = (params.get('keyword') or '').strip()
    if keyword:
        qs = qs.filter(
            Q(model_name__icontains=keyword)
            | Q(plate_number__icontains=keyword)
            | Q(brand__name__icontains=keyword)
        )
    if params.get('category'):
        qs = qs.filter(category_id=params['category'])
    if params.get('brand'):
        qs = qs.filter(brand_id=params['brand'])
    if params.get('fuel_type'):
        qs = qs.filter(fuel_type=params['fuel_type'])
    if params.get('price_min'):
        qs = qs.filter(daily_rent__gte=params['price_min'])
    if params.get('price_max'):
        qs = qs.filter(daily_rent__lte=params['price_max'])
    # 排序：默认最新上架，支持价格升/降序
    sort = params.get('sort', '')
    if sort == 'price_asc':
        qs = qs.order_by('daily_rent')
    elif sort == 'price_desc':
        qs = qs.order_by('-daily_rent')
    else:
        qs = qs.order_by('-created_at')
    return qs


def get_occupied_dates(vehicle, start=None, end=None):
    """
    获取车辆在指定区间内的已占用日期集合。

    区间内存在「已支付/租赁中/待还车/已逾期/异常处理」订单的日期视为占用，
    边界相触允许（还车时间 = 下一单取车时间不冲突）。
    """
    from orders.models import Order
    occupied_statuses = ['paid', 'renting', 'to_return', 'overdue', 'abnormal']
    today = datetime.date.today()
    start = start or today
    end = end or today + datetime.timedelta(days=90)
    orders = Order.objects.filter(
        vehicle=vehicle,
        status__in=occupied_statuses,
        start_date__lte=end,
        end_date__gte=start,
    )
    occupied = set()
    for order in orders:
        day = max(order.start_date, start)
        while day <= min(order.end_date, end):
            occupied.add(day)
            day += datetime.timedelta(days=1)
    return occupied

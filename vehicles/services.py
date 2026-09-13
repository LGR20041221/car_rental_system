"""
车辆服务层：前台车辆筛选、占用日期查询与推荐服务。

- 前台筛选/占用日期：车辆列表页与详情页展示，辅助用户避开车期冲突
- 推荐服务（智能模块）：首页热门推荐按已完成订单数降序，相似车辆按品牌/分类推荐
"""
import datetime

from django.db.models import Count, Q

from favorites.models import Favorite
from vehicles.models import Vehicle


def get_vehicle_list(params):
    """
    根据筛选条件查询可租车辆列表。

    支持关键词、分类、品牌、燃油类型、价格区间筛选与多种排序方式。
    """
    # prefetch images：模板取首张图作缩略图，避免逐车查询
    qs = Vehicle.objects.filter(status='available').select_related(
        'brand', 'category'
    ).prefetch_related('images')
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


# ==================== 推荐服务（智能模块） ====================

def get_hot_vehicles(limit=10):
    """
    获取首页热门推荐车辆：按已完成订单数降序取前 limit 辆（每行 5 个，共 2 行）。
    已完成订单数相同的，按收藏数与主键降序作为兜底排序。
    """
    return (
        Vehicle.objects.filter(status='available')
        .select_related('brand', 'category')
        .prefetch_related('images')
        .annotate(
            sales=Count('orders', filter=Q(orders__status='completed')),
            fav_count=Count('favorites'),
        )
        .order_by('-sales', '-fav_count', '-pk')[:limit]
    )


def get_banner_vehicles(limit=3):
    """获取首页轮播展示车辆（已完成订单数 TOP3，畅销车优先上轮播）。"""
    return get_hot_vehicles(limit=limit)


def mark_favorite_status(vehicles, user):
    """
    为车辆列表标记当前用户的收藏状态（is_favorited），供模板展示。
    """
    if user is None or not getattr(user, 'is_authenticated', False) or not vehicles:
        for v in vehicles:
            v.is_favorited = False
        return vehicles
    ids = set(
        Favorite.objects.filter(
            user=user, vehicle_id__in=[v.id for v in vehicles]
        ).values_list('vehicle_id', flat=True)
    )
    for v in vehicles:
        v.is_favorited = v.id in ids
    return vehicles


def get_similar_vehicles(vehicle, limit=5):
    """
    获取与指定车辆相似的其他车辆：
    1. 同品牌车辆按收藏数降序，排除当前车辆，最多 limit 辆；
    2. 数量不足时，优先补充同分类的其他品牌车辆；
    3. 仍不足时补充其余可租车辆。
    """
    result = list(
        Vehicle.objects.filter(brand=vehicle.brand, status='available')
        .exclude(pk=vehicle.pk)
        .annotate(fav_count=Count('favorites'))
        .order_by('-fav_count', '-pk')[:limit]
    )
    if len(result) < limit:
        exclude_ids = [v.pk for v in result] + [vehicle.pk]
        # 同分类的其他品牌优先
        same_cat = list(
            Vehicle.objects.filter(category=vehicle.category, status='available')
            .exclude(pk__in=exclude_ids)
            .annotate(fav_count=Count('favorites'))
            .order_by('-fav_count', '-pk')[:limit - len(result)]
        )
        result.extend(same_cat)
        exclude_ids = [v.pk for v in result] + [vehicle.pk]
        if len(result) < limit:
            others = list(
                Vehicle.objects.filter(status='available')
                .exclude(pk__in=exclude_ids)
                .annotate(fav_count=Count('favorites'))
                .order_by('-fav_count', '-pk')[:limit - len(result)]
            )
            result.extend(others)
    return result[:limit]

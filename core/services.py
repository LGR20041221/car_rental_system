"""
推荐服务（智能模块核心之一）。

- 首页热门推荐：按销量（订单量，不含已取消）取 TOP 10
- 相似车辆推荐：同品牌优先，按收藏数降序，不足时补足其他品牌（优先同分类）

均为简单的字段过滤与排序，保证查询效率。
"""
from django.db.models import Count, Q

from favorites.models import Favorite
from vehicles.models import Vehicle

# 计入销量的订单状态（排除已取消、待支付）
SALES_STATUS = ['paid', 'renting', 'to_return', 'completed', 'overdue', 'abnormal']


def get_hot_vehicles(limit=10):
    """
    获取首页热门推荐车辆：按订单量降序取前 limit 辆（每行 5 个，共 2 行）。
    """
    return (
        Vehicle.objects.filter(status='available')
        .annotate(
            sales=Count('orders', filter=Q(orders__status__in=SALES_STATUS)),
            fav_count=Count('favorites'),
        )
        .order_by('-sales', '-fav_count', '-pk')[:limit]
    )


def get_banner_vehicles(limit=3):
    """获取首页轮播展示车辆（按销量取前 3 辆，带主图）。"""
    return get_hot_vehicles(limit=limit)


def mark_favorite_status(vehicles, user):
    """
    为车辆列表标记当前用户的收藏状态（is_favorited），供模板展示。
    """
    if user is None or not vehicles:
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

"""
收藏应用视图：收藏/取消收藏、我的收藏、批量取消、管理端收藏统计。
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from favorites.models import Favorite
from users.decorators import admin_required
from vehicles.models import Vehicle


@login_required
def favorite_toggle(request):
    """
    收藏/取消收藏（AJAX）：根据当前状态切换，返回最新收藏状态与数量。
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'}, status=405)
    vehicle_id = request.POST.get('vehicle_id')
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    favorite = Favorite.objects.filter(user=request.user, vehicle=vehicle).first()
    if favorite:
        favorite.delete()
        is_favorited = False
        message = '已取消收藏'
    else:
        Favorite.objects.create(user=request.user, vehicle=vehicle)
        is_favorited = True
        message = '收藏成功'
    return JsonResponse({
        'success': True,
        'message': message,
        'is_favorited': is_favorited,
        'favorite_count': Favorite.objects.filter(vehicle=vehicle).count(),
    })


@login_required
def favorite_list(request):
    """
    我的收藏：支持按品牌、价格区间筛选，支持批量取消收藏。
    """
    user = request.user
    brand = request.GET.get('brand', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    qs = Favorite.objects.filter(user=user).select_related(
        'vehicle__brand', 'vehicle__category'
    ).prefetch_related('vehicle__images').order_by('-created_at')
    if brand:
        qs = qs.filter(vehicle__brand_id=brand)
    if price_min:
        qs = qs.filter(vehicle__daily_rent__gte=price_min)
    if price_max:
        qs = qs.filter(vehicle__daily_rent__lte=price_max)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    from vehicles.models import Brand
    return render(request, 'favorites/favorite_list.html', {
        'page_obj': page_obj,
        'brands': Brand.objects.all(),
        'brand': brand,
        'price_min': price_min,
        'price_max': price_max,
    })


@login_required
def favorite_batch_remove(request):
    """批量取消收藏（POST 传入多个 favorite_id）。"""
    ids = request.POST.getlist('ids')
    if ids:
        Favorite.objects.filter(user=request.user, id__in=ids).delete()
        messages.success(request, f'已取消 {len(ids)} 辆收藏车辆')
    return redirect('favorites:list')


@admin_required
def admin_favorite_stats(request):
    """
    管理端收藏统计：车辆收藏排行 + 用户收藏偏好分析（按品牌）。
    """
    from django.db.models import Count
    vehicle_ranking = Vehicle.objects.annotate(
        fav_count=Count('favorites')
    ).filter(fav_count__gt=0).order_by('-fav_count')[:10]
    brand_ranking = list(
        Favorite.objects.values('vehicle__brand__name').annotate(
            count=Count('id')
        ).order_by('-count')
    )
    return render(request, 'favorites/admin_favorite_stats.html', {
        'vehicle_ranking': vehicle_ranking,
        'brand_ranking': brand_ranking,
    })

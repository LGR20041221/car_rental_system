"""
车辆应用视图：首页、前台车辆列表/详情、管理端车辆与品牌/分类维护。
"""
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from favorites.models import Favorite
from reviews.models import Review
from users.decorators import admin_required
from vehicles.forms import BrandForm, CategoryForm, VehicleForm
from vehicles.models import Brand, Category, Vehicle, VehicleImage
from vehicles.services import (
    get_banner_vehicles,
    get_hot_vehicles,
    get_occupied_dates,
    get_similar_vehicles,
    get_vehicle_list,
    mark_favorite_status,
)

logger = logging.getLogger(__name__)


def home(request):
    """
    首页：展示轮播车辆、搜索入口、热门推荐 TOP10 与最新公告。
    """
    banners = get_banner_vehicles(limit=3)
    hot_vehicles = get_hot_vehicles(limit=10)
    mark_favorite_status(hot_vehicles, request.user)
    context = {
        'banners': banners,
        'hot_vehicles': hot_vehicles,
        'brands': Brand.objects.all(),
        'categories': Category.objects.all(),
    }
    return render(request, 'vehicles/home.html', context)


def vehicle_list(request):
    """
    前台车辆列表：按条件筛选、分页展示可租车辆，并展示筛选表单所需选项。
    """
    filters = {
        'keyword': request.GET.get('keyword', ''),
        'category': request.GET.get('category', ''),
        'brand': request.GET.get('brand', ''),
        'fuel_type': request.GET.get('fuel_type', ''),
        'price_min': request.GET.get('price_min', ''),
        'price_max': request.GET.get('price_max', ''),
        'sort': request.GET.get('sort', ''),
    }
    # 构造筛选参数（空字符串转为 None）
    params = {}
    for key, value in filters.items():
        params[key] = value if value else None
    qs = get_vehicle_list(params)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    # 分页时保留筛选条件
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    mark_favorite_status(list(page_obj), request.user)
    context = {
        'page_obj': page_obj,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'fuel_types': Vehicle.FUEL_CHOICES,
        'filters': filters,
        'query_string': get_copy.urlencode(),
    }
    return render(request, 'vehicles/vehicle_list.html', context)


def vehicle_detail(request, vehicle_id):
    """
    前台车辆详情：展示图片、参数、评价、相似推荐与占用日期。
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('brand', 'category'), pk=vehicle_id
    )
    # 主图取封面图（VehicleImage.is_cover），无封面时退回第一张
    images = vehicle.images.all().order_by('-is_cover', 'id')
    reviews = Review.objects.filter(vehicle=vehicle, is_hidden=False).order_by('-created_at')
    similar_vehicles = get_similar_vehicles(vehicle, limit=5)
    occupied_dates = get_occupied_dates(vehicle)
    # 收藏状态（仅登录用户可收藏）
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(
            user=request.user, vehicle=vehicle
        ).exists()
    context = {
        'vehicle': vehicle,
        'images': images,
        'reviews': reviews,
        'similar_vehicles': similar_vehicles,
        'occupied_dates': occupied_dates,
        'is_favorited': is_favorited,
        'favorite_count': Favorite.objects.filter(vehicle=vehicle).count(),
    }
    return render(request, 'vehicles/vehicle_detail.html', context)


# ==================== 管理端：车辆管理 ====================

@admin_required
def admin_vehicle_list(request):
    """
    管理端车辆列表：支持关键词搜索与状态筛选，含各车辆收藏/订单统计。
    """
    keyword = request.GET.get('keyword', '').strip()
    status = request.GET.get('status', '')
    # prefetch images：列表展示各车首图（主图），避免逐行查询
    qs = Vehicle.objects.select_related('brand', 'category').prefetch_related('images').annotate(
        favorite_count=Count('favorites', distinct=True),
        order_count=Count('orders', distinct=True),
    )
    if keyword:
        qs = qs.filter(
            model_name__icontains=keyword
        ) | qs.filter(plate_number__icontains=keyword) | qs.filter(brand__name__icontains=keyword)
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by('-created_at')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'vehicles/admin_vehicle_list.html', {
        'page_obj': page_obj,
        'keyword': keyword,
        'status': status,
        'status_choices': Vehicle.STATUS_CHOICES,
        'query_string': get_copy.urlencode(),
    })


@admin_required
def admin_vehicle_create(request):
    """
    管理端新增车辆：与「编辑车辆」共用同一界面，区别仅在于表单为空、不自动填充。
    同一表单内也可直接上传车辆图片。
    """
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save()
            _save_uploaded_images(
                vehicle, request.FILES.getlist('images'),
                _parse_cover_index(request.POST.get('cover_index')),
            )
            logger.info('管理员新增车辆：%s', vehicle.model_name)
            messages.success(request, f'车辆 {vehicle.model_name} 添加成功')
            return redirect('vehicles:admin_vehicle_list')
        messages.error(request, '添加失败，请检查填写信息')
    else:
        form = VehicleForm()
    return render(request, 'vehicles/admin_vehicle_form.html', {'form': form})


@admin_required
def admin_vehicle_edit(request, vehicle_id):
    """
    管理端编辑车辆：与「新增车辆」共用同一界面（admin_vehicle_form.html），
    区别仅在于表单会按该车辆已有数据自动填充；图片管理也在此页完成。
    """
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            form.save()
            _save_uploaded_images(vehicle, request.FILES.getlist('images'))
            messages.success(request, f'车辆 {vehicle.model_name} 修改成功')
            return redirect('vehicles:admin_vehicle_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'vehicles/admin_vehicle_form.html', {
        'form': form, 'vehicle': vehicle,
    })


def _parse_cover_index(raw):
    """解析前端提交的主图下标：非法或缺失时返回 None，交由 _save_uploaded_images 兜底。"""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _save_uploaded_images(vehicle, files, cover_index=None):
    """
    保存随表单提交的车辆图片。

    该车还没有主图时，由 cover_index 指定的一张成为主图（新增页前端可
    「设为主图/删除」）；未指定或越界时退回第一张。返回成功保存的张数。
    """
    files = [f for f in files if f]
    if not files:
        return 0
    has_cover = vehicle.images.filter(is_cover=True).exists()
    if not has_cover and (cover_index is None or not 0 <= cover_index < len(files)):
        cover_index = 0
    start = vehicle.images.count()
    for index, f in enumerate(files):
        VehicleImage.objects.create(
            vehicle=vehicle,
            image=f,
            is_cover=(not has_cover and index == cover_index),
            sort_order=start + index,
        )
    return len(files)


@admin_required
def admin_vehicle_delete(request, vehicle_id):
    """管理端删除车辆：存在关联订单时禁止删除（提示先下架）。"""
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    if vehicle.orders.exists():
        messages.error(request, '该车辆存在关联订单，无法删除，请改为「已下架」')
        return redirect('vehicles:admin_vehicle_list')
    vehicle.delete()
    messages.success(request, f'车辆 {vehicle.model_name} 已删除')
    return redirect('vehicles:admin_vehicle_list')


@admin_required
def admin_vehicle_image_upload(request, vehicle_id):
    """
    AJAX 上传车辆图片（编辑页「上传」按钮调用）：保存后返回该车最新图片列表，
    前端据此重绘预览区，新图自然排在原有图片之后（主图始终在最前）。
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '请求方式错误'}, status=405)
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    files = [f for f in request.FILES.getlist('images') if f]
    if not files:
        return JsonResponse({'success': False, 'message': '请先选择要上传的图片'}, status=400)
    saved = _save_uploaded_images(vehicle, files)
    return JsonResponse({
        'success': True,
        'message': f'成功上传 {saved} 张图片',
        'images': _serialize_images(vehicle),
    })


def _serialize_images(vehicle):
    """序列化车辆图片列表，供前端重绘预览区。"""
    return [
        {
            'id': img.id,
            'url': img.image.url,
            'is_cover': img.is_cover,
            'set_cover_url': reverse('vehicles:admin_vehicle_image_set_cover', args=[img.id]),
            'delete_url': reverse('vehicles:admin_vehicle_image_delete', args=[img.id]),
        }
        for img in vehicle.images.all()
    ]


@admin_required
def admin_vehicle_image_delete(request, image_id):
    """
    管理端删除车辆图片：删除后回到车辆编辑页。
    若删除的是主图，自动将剩余图片中 id 最小的一张设为主图。
    """
    image = get_object_or_404(VehicleImage, pk=image_id)
    vehicle = image.vehicle
    was_cover = image.is_cover
    image.delete()
    if was_cover:
        first = vehicle.images.order_by('id').first()
        if first:
            first.is_cover = True
            first.save(update_fields=['is_cover'])
    messages.success(request, '图片已删除')
    return redirect('vehicles:admin_vehicle_edit', vehicle_id=vehicle.id)


@admin_required
def admin_vehicle_image_set_cover(request, image_id):
    """管理端设置车辆主图：同一车辆内主图唯一（先清除其余图片的主图标记）。"""
    image = get_object_or_404(VehicleImage, pk=image_id)
    VehicleImage.objects.filter(vehicle=image.vehicle).exclude(
        pk=image.pk
    ).update(is_cover=False)
    image.is_cover = True
    image.save(update_fields=['is_cover'])
    messages.success(request, '已设为主图')
    return redirect('vehicles:admin_vehicle_edit', vehicle_id=image.vehicle_id)


# ==================== 管理端：品牌管理 ====================

@admin_required
def admin_brand_list(request):
    """管理端品牌列表：展示各品牌车辆数量，支持搜索，每页 15 条。"""
    keyword = request.GET.get('keyword', '').strip()
    qs = Brand.objects.annotate(vehicle_count=Count('vehicles'))
    if keyword:
        qs = qs.filter(name__icontains=keyword)
    qs = qs.order_by('id')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'vehicles/admin_brand_list.html', {
        'page_obj': page_obj, 'keyword': keyword,
        'query_string': get_copy.urlencode(),
    })


@admin_required
def admin_brand_create(request):
    """管理端新增品牌。"""
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '品牌添加成功')
            return redirect('vehicles:admin_brand_list')
        messages.error(request, '添加失败，请检查填写信息')
    else:
        form = BrandForm()
    return render(request, 'vehicles/admin_brand_form.html', {'form': form})


@admin_required
def admin_brand_edit(request, brand_id):
    """管理端编辑品牌。"""
    brand = get_object_or_404(Brand, pk=brand_id)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, '品牌修改成功')
            return redirect('vehicles:admin_brand_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'vehicles/admin_brand_form.html', {
        'form': form, 'brand': brand,
    })


@admin_required
def admin_brand_delete(request, brand_id):
    """管理端删除品牌：存在关联车辆时禁止删除。"""
    brand = get_object_or_404(Brand, pk=brand_id)
    if brand.vehicles.exists():
        messages.error(request, '该品牌下存在车辆，无法删除')
        return redirect('vehicles:admin_brand_list')
    brand.delete()
    messages.success(request, '品牌已删除')
    return redirect('vehicles:admin_brand_list')


# ==================== 管理端：车辆分类 ====================

@admin_required
def admin_category_list(request):
    """管理端车辆分类列表（每页 15 条）。"""
    qs = Category.objects.annotate(vehicle_count=Count('vehicles')).order_by('id')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'vehicles/admin_category_list.html', {
        'page_obj': page_obj,
    })


@admin_required
def admin_category_create(request):
    """管理端新增车辆分类。"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '分类添加成功')
            return redirect('vehicles:admin_category_list')
        messages.error(request, '添加失败，请检查填写信息')
    else:
        form = CategoryForm()
    return render(request, 'vehicles/admin_category_form.html', {'form': form})


@admin_required
def admin_category_edit(request, category_id):
    """管理端编辑车辆分类。"""
    category = get_object_or_404(Category, pk=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '分类修改成功')
            return redirect('vehicles:admin_category_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'vehicles/admin_category_form.html', {
        'form': form, 'category': category,
    })


@admin_required
def admin_category_delete(request, category_id):
    """管理端删除车辆分类：存在关联车辆时禁止删除。"""
    category = get_object_or_404(Category, pk=category_id)
    if category.vehicles.exists():
        messages.error(request, '该分类下存在车辆，无法删除')
        return redirect('vehicles:admin_category_list')
    category.delete()
    messages.success(request, '分类已删除')
    return redirect('vehicles:admin_category_list')

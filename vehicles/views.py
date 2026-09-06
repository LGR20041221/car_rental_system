"""
车辆应用视图：前台车辆列表/详情、管理端车辆与品牌/分类维护。
"""
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required
from core.services import get_similar_vehicles, mark_favorite_status
from favorites.models import Favorite
from reviews.models import Review
from vehicles.forms import BrandForm, CategoryForm, VehicleForm
from vehicles.models import Brand, Category, Vehicle, VehicleImage
from vehicles.services import get_occupied_dates, get_vehicle_list

logger = logging.getLogger(__name__)


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
    mark_favorite_status(list(page_obj), request.current_user)
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
    images = vehicle.images.all()
    reviews = Review.objects.filter(vehicle=vehicle, is_hidden=False).order_by('-created_at')
    similar_vehicles = get_similar_vehicles(vehicle, limit=5)
    occupied_dates = get_occupied_dates(vehicle)
    # 收藏状态（仅登录用户可收藏）
    is_favorited = False
    if request.current_user is not None:
        is_favorited = Favorite.objects.filter(
            user=request.current_user, vehicle=vehicle
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
    qs = Vehicle.objects.select_related('brand', 'category').annotate(
        favorite_count=Count('favorites'),
        order_count=Count('orders'),
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
    """管理端新增车辆：品牌/分类从字典表选择。"""
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save()
            logger.info('管理员新增车辆：%s', vehicle.model_name)
            messages.success(request, f'车辆 {vehicle.model_name} 添加成功')
            return redirect('vehicles:admin_vehicle_list')
        messages.error(request, '添加失败，请检查填写信息')
    else:
        form = VehicleForm()
    return render(request, 'vehicles/admin_vehicle_form.html', {
        'form': form, 'title': '新增车辆',
    })


@admin_required
def admin_vehicle_edit(request, vehicle_id):
    """管理端编辑车辆基本信息与状态。"""
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f'车辆 {vehicle.model_name} 修改成功')
            return redirect('vehicles:admin_vehicle_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'vehicles/admin_vehicle_form.html', {
        'form': form, 'title': '编辑车辆', 'vehicle': vehicle,
    })


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
def admin_vehicle_image_delete(request, image_id):
    """管理端删除车辆图片。"""
    image = get_object_or_404(VehicleImage, pk=image_id)
    vehicle = image.vehicle
    image.delete()
    messages.success(request, '图片已删除')
    return redirect('vehicles:admin_vehicle_images', vehicle_id=vehicle.id)


@admin_required
def admin_vehicle_images(request, vehicle_id):
    """管理端车辆图片管理：查看、上传、删除多角度图片。"""
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    if request.method == 'POST':
        files = request.FILES.getlist('images')
        if not files:
            messages.error(request, '请选择要上传的图片')
        else:
            for index, f in enumerate(files):
                VehicleImage.objects.create(
                    vehicle=vehicle, image=f, sort_order=vehicle.images.count() + index
                )
            messages.success(request, f'成功上传 {len(files)} 张图片')
            return redirect('vehicles:admin_vehicle_images', vehicle_id=vehicle.id)
    return render(request, 'vehicles/admin_vehicle_images.html', {'vehicle': vehicle})


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
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '品牌添加成功')
            return redirect('vehicles:admin_brand_list')
        messages.error(request, '添加失败，请检查填写信息')
    else:
        form = BrandForm()
    return render(request, 'vehicles/admin_brand_form.html', {
        'form': form, 'title': '新增品牌',
    })


@admin_required
def admin_brand_edit(request, brand_id):
    """管理端编辑品牌。"""
    brand = get_object_or_404(Brand, pk=brand_id)
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, '品牌修改成功')
            return redirect('vehicles:admin_brand_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'vehicles/admin_brand_form.html', {
        'form': form, 'title': '编辑品牌', 'brand': brand,
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
    return render(request, 'vehicles/admin_category_form.html', {
        'form': form, 'title': '新增分类',
    })


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
        'form': form, 'title': '编辑分类', 'category': category,
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

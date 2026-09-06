"""
评价应用视图：提交评价、我的评价、管理端评价管理。
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required, login_required
from orders.models import Order
from reviews.forms import ReviewForm
from reviews.models import Review


@login_required
def review_submit(request, order_id):
    """
    提交评价：仅限已完成订单、且本人未评价过的订单可评价。
    """
    order = get_object_or_404(
        Order, pk=order_id, user=request.current_user
    )
    if order.status != 'completed':
        messages.error(request, '仅已完成订单可评价')
        return redirect('orders:order_detail', order_id=order.id)
    if hasattr(order, 'review'):
        messages.error(request, '该订单已评价过')
        return redirect('orders:order_detail', order_id=order.id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.order = order
            review.user = request.current_user
            review.vehicle = order.vehicle
            review.save()
            messages.success(request, '评价发布成功')
            return redirect('reviews:my_reviews')
        messages.error(request, '评价发布失败，请检查填写信息')
    else:
        form = ReviewForm()
    return render(request, 'reviews/review_submit.html', {
        'form': form, 'order': order,
    })


@login_required
def my_reviews(request):
    """我的评价：查看已发表评价列表，每页 15 条。"""
    qs = Review.objects.filter(user=request.current_user).select_related(
        'vehicle__brand', 'order'
    ).order_by('-created_at')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'reviews/my_reviews.html', {'page_obj': page_obj})


@admin_required
def admin_review_list(request):
    """管理端评价管理：查看、隐藏不当评价、各车辆评分统计，每页 15 条。"""
    status = request.GET.get('status', '')
    qs = Review.objects.select_related('user', 'vehicle__brand', 'order').order_by('-created_at')
    if status == 'hidden':
        qs = qs.filter(is_hidden=True)
    elif status == 'visible':
        qs = qs.filter(is_hidden=False)
    # 各车辆平均评分统计
    stats = Review.objects.exclude(is_hidden=True).values(
        'vehicle__id', 'vehicle__model_name', 'vehicle__brand__name'
    ).annotate(avg_rating=Avg('rating'), review_count=Count('id')).order_by('-review_count')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'reviews/admin_review_list.html', {
        'page_obj': page_obj,
        'status': status,
        'stats': stats,
    })


@admin_required
def admin_review_toggle(request, review_id):
    """管理端隐藏/恢复评价。"""
    review = get_object_or_404(Review, pk=review_id)
    review.is_hidden = not review.is_hidden
    review.save(update_fields=['is_hidden'])
    action = '已隐藏' if review.is_hidden else '已恢复展示'
    messages.success(request, f'评价{action}')
    return redirect('reviews:admin_review_list')

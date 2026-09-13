"""
支付应用视图：用户优惠券/账单，管理端优惠券/财务/退款。
"""
import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from payments import services as payment_services
from payments.forms import CouponForm
from payments.models import Coupon, Payment, UserCoupon
from payments.services import claim_coupon, get_revenue_stats
from users.decorators import admin_required


# ==================== 用户端 ====================

@login_required
def coupon_list(request):
    """
    我的优惠券：按状态（未使用/已使用/已失效）服务端筛选，并展示可领取的平台优惠券。
    状态通过 ?status= 查询参数切换，与「我的订单」页筛选方式保持一致。
    """
    user = request.user
    status = request.GET.get('status', '')
    coupons = payment_services.get_user_coupons(user, status)
    # 领券中心：未领取且在有效期内的平台券
    today = datetime.date.today()
    claimed_ids = user.user_coupons.values_list('coupon_id', flat=True)
    claimable = Coupon.objects.filter(
        is_active=True, start_date__lte=today, end_date__gte=today
    ).exclude(id__in=claimed_ids).order_by('-created_at')
    return render(request, 'payments/coupon_list.html', {
        'coupons': coupons,
        'status': status,
        'status_choices': UserCoupon.STATUS_CHOICES,
        'claimable': claimable,
    })


@login_required
def coupon_claim(request, coupon_id):
    """领取平台发放的优惠券。"""
    success, message = claim_coupon(request.user, coupon_id)
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('payments:coupon_list')


@login_required
def bill_list(request):
    """账单查询：查看历史消费明细（支付流水）。"""
    bills = payment_services.get_user_bills(request.user)
    paginator = Paginator(bills, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'payments/bill_list.html', {'page_obj': page_obj})


# ==================== 管理端：优惠券 ====================

@admin_required
def admin_coupon_list(request):
    """管理端优惠券列表：支持搜索，每页 15 条。"""
    keyword = request.GET.get('keyword', '').strip()
    qs = Coupon.objects.all().order_by('-created_at')
    if keyword:
        qs = qs.filter(name__icontains=keyword)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'payments/admin_coupon_list.html', {
        'page_obj': page_obj, 'keyword': keyword,
        'query_string': get_copy.urlencode(),
    })


@admin_required
def admin_coupon_create(request):
    """管理端创建优惠券。"""
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '优惠券创建成功')
            return redirect('payments:admin_coupon_list')
        messages.error(request, '创建失败，请检查填写信息')
    else:
        form = CouponForm()
    return render(request, 'payments/admin_coupon_form.html', {'form': form})


@admin_required
def admin_coupon_edit(request, coupon_id):
    """管理端编辑优惠券。"""
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, '优惠券修改成功')
            return redirect('payments:admin_coupon_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = CouponForm(instance=coupon)
    return render(request, 'payments/admin_coupon_form.html', {
        'form': form, 'coupon': coupon,
    })


@admin_required
def admin_coupon_toggle(request, coupon_id):
    """管理端启用/停用优惠券。"""
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    action = '已启用' if coupon.is_active else '已停用'
    messages.success(request, f'优惠券「{coupon.name}」{action}')
    return redirect('payments:admin_coupon_list')


@admin_required
def admin_coupon_delete(request, coupon_id):
    """管理端删除优惠券：已有用户领取的优惠券禁止删除（建议停用）。"""
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if coupon.user_coupons.exists():
        messages.error(request, '该优惠券已有用户领取，无法删除，请改为停用')
        return redirect('payments:admin_coupon_list')
    coupon.delete()
    messages.success(request, '优惠券已删除')
    return redirect('payments:admin_coupon_list')


# ==================== 管理端：财务 ====================

@admin_required
def admin_finance(request):
    """收入报表：展示平台收入统计和趋势。"""
    stats = get_revenue_stats(days=14)
    context = {
        'daily_json': json.dumps(stats['daily']),
        'composition_json': json.dumps(stats['composition']),
        'total_income': stats['total_income'],
    }
    return render(request, 'payments/admin_finance.html', context)


@admin_required
def admin_refund_list(request):
    """退款处理：展示已取消/异常订单，按需执行模拟退款，每页 15 条。"""
    from orders.models import Order
    qs = Order.objects.filter(status__in=['cancelled', 'abnormal']).select_related(
        'user', 'vehicle__brand'
    ).order_by('-updated_at')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'payments/admin_refund_list.html', {'page_obj': page_obj})


@admin_required
def admin_refund_process(request, order_id):
    """
    退款处理：为取消/异常订单补录退款流水（租金退款 + 押金退款）。
    已生成过退款流水的订单跳过，避免重复退款。
    """
    from orders.models import Order
    order = get_object_or_404(Order, pk=order_id)
    if order.status not in ['cancelled', 'abnormal']:
        messages.error(request, '仅已取消/异常订单可执行退款')
        return redirect('payments:admin_refund_list')
    # 租金退款
    if not Payment.objects.filter(order=order, payment_type='rent_refund').exists():
        payment_services.create_payment(order, 'rent_refund', order.payable_rent, method='管理员退款-租金')
    # 押金退款（未退过才退）
    if not order.deposit_returned and not Payment.objects.filter(
        order=order, payment_type='deposit_refund'
    ).exists():
        payment_services.create_payment(order, 'deposit_refund', order.deposit, method='管理员退款-押金')
        order.deposit_returned = True
        order.save(update_fields=['deposit_returned', 'updated_at'])
    messages.success(request, f'订单 {order.order_no} 退款处理完成')
    return redirect('payments:admin_refund_list')

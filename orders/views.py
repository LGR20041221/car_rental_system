"""
订单应用视图：用户下单/支付/取消/续租/还车，管理端订单管理/审核。
"""
import datetime
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required, login_required
from orders import services as order_services
from orders.forms import ExtendForm, OrderCreateForm
from orders.models import Order
from pricing.services import calculate_price, get_deposit
from vehicles.models import Vehicle

logger = logging.getLogger(__name__)


@login_required
def order_create(request):
    """
    创建订单：选择车辆、租期与优惠券，提交前实时预览价格；
    提交时校验租期冲突，冲突则提示可预约的最近空闲时间段。
    """
    from notifications.services import create_notification
    from payments.services import get_user_valid_coupons, get_user_coupon_by_id

    user = request.current_user
    vehicle = None
    vehicle_id = request.POST.get('vehicle_id') or request.GET.get('vehicle_id')
    if vehicle_id:
        vehicle = Vehicle.objects.select_related('brand', 'category').filter(
            pk=vehicle_id, status__in=['available', 'renting']
        ).first()

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            vehicle = get_object_or_404(Vehicle, pk=data['vehicle_id'])
            if vehicle.status == 'off_shelf':
                messages.error(request, '该车辆已下架，无法下单')
                return redirect('vehicles:vehicle_detail', vehicle_id=vehicle.id)
            # 优惠券校验
            coupon = None
            if data.get('coupon_id'):
                coupon = get_user_coupon_by_id(user, data['coupon_id'])
                if coupon is None:
                    messages.error(request, '优惠券无效或不可用')
                    return redirect('orders:order_create')
            # 创建订单（含冲突校验）
            order, error = order_services.create_order(
                user, vehicle,
                data['start_date'], data['end_date'],
                data['pickup_location'], data['return_location'],
                coupon,
            )
            if error:
                start, end = order_services.find_available_slot(
                    vehicle, data['start_date'], data['end_date']
                )
                tip = f'建议预约 {start} 至 {end}' if start else '该车辆近期已满，请更换车辆'
                messages.error(request, f'{error}；{tip}')
                form = OrderCreateForm(initial={
                    'vehicle_id': vehicle.id,
                    'start_date': start or data['start_date'],
                    'end_date': end or data['end_date'],
                })
            else:
                create_notification(user, '下单成功', f'您的订单 {order.order_no} 已创建，请尽快完成支付。')
                messages.success(request, '下单成功，请尽快完成支付')
                return redirect('orders:order_detail', order_id=order.id)
        else:
            messages.error(request, '下单失败，请检查填写信息')
    else:
        initial = {'vehicle_id': vehicle_id} if vehicle_id else {}
        form = OrderCreateForm(initial=initial)

    coupons = get_user_valid_coupons(user) if user else []
    # 供页面直接渲染的价格预览（车辆已定时）
    price_info = None
    deposit = None
    if vehicle and vehicle_id:
        today = datetime.date.today()
        price_info = calculate_price(vehicle, today, today + datetime.timedelta(days=1))
        deposit = get_deposit(vehicle)
    context = {
        'form': form,
        'vehicle': vehicle,
        'coupons': coupons,
        'price_info': price_info,
        'deposit': deposit,
    }
    return render(request, 'orders/order_create.html', context)


@login_required
def order_detail(request, order_id):
    """
    订单详情：展示订单完整信息（车辆、费用、时间节点），
    按状态提供支付/取消/续租/还车操作。
    """
    order = get_object_or_404(
        Order.objects.select_related('vehicle__brand', 'user'),
        pk=order_id, user=request.current_user,
    )
    # 页面访问时刷新订单状态
    order_services.process_order_statuses()
    order.refresh_from_db()
    can_cancel = order.status in ['pending', 'paid']
    can_pay = order.status == 'pending'
    can_extend = order.status in ['renting', 'overdue'] and order.extension_status in ['none', 'rejected']
    can_confirm_return = order.status in ['renting', 'overdue']
    context = {
        'order': order,
        'can_cancel': can_cancel,
        'can_pay': can_pay,
        'can_extend': can_extend,
        'can_confirm_return': can_confirm_return,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def order_pay(request, order_id):
    """订单支付（模拟支付）：待支付订单支付租金与押金。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id, user=request.current_user)
    if order.status != 'pending':
        messages.error(request, '当前订单状态不可支付')
        return redirect('orders:order_detail', order_id=order.id)
    order_services.pay_order(order)
    create_notification(order.user, '支付成功', f'订单 {order.order_no} 支付成功，已冻结押金 {order.deposit} 元。')
    messages.success(request, '支付成功，车辆已为您保留')
    return redirect('orders:order_detail', order_id=order.id)


@login_required
def order_cancel(request, order_id):
    """取消订单：待支付/已支付订单可免费取消，已支付订单自动退款。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id, user=request.current_user)
    if order.status not in ['pending', 'paid']:
        messages.error(request, '当前订单状态不可取消')
        return redirect('orders:order_detail', order_id=order.id)
    reason = request.POST.get('reason', '').strip()
    order_services.cancel_order(order, reason=reason or '用户取消订单')
    create_notification(order.user, '订单已取消', f'订单 {order.order_no} 已取消。')
    messages.success(request, '订单已取消')
    return redirect('orders:order_detail', order_id=order.id)


@login_required
def order_extend(request, order_id):
    """申请续租：填写续租目标日期，提交后等待管理员审批。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id, user=request.current_user)
    if request.method == 'POST':
        form = ExtendForm(request.POST)
        if form.is_valid():
            new_end = form.cleaned_data['extend_to_date']
            if new_end <= order.end_date:
                messages.error(request, '续租目标日期需晚于当前还车日期')
                return redirect('orders:order_detail', order_id=order.id)
            order_services.apply_extension(order, new_end)
            create_notification(order.user, '续租申请已提交', f'订单 {order.order_no} 续租至 {new_end}，待管理员审批。')
            messages.success(request, '续租申请已提交，等待管理员审批')
        else:
            messages.error(request, '请选择正确的续租日期')
        return redirect('orders:order_detail', order_id=order.id)
    return redirect('orders:order_detail', order_id=order.id)


@login_required
def order_confirm_return(request, order_id):
    """确认还车：用户确认车辆已归还，订单进入「待还车」等待管理员核验。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id, user=request.current_user)
    if order.status not in ['renting', 'overdue']:
        messages.error(request, '当前订单状态不可确认还车')
        return redirect('orders:order_detail', order_id=order.id)
    order_services.confirm_return(order)
    create_notification(order.user, '还车确认成功', f'订单 {order.order_no} 已确认还车，等待管理员核验后退还押金。')
    messages.success(request, '还车确认成功，押金将在管理员核验后退还')
    return redirect('orders:order_detail', order_id=order.id)


@login_required
def my_orders(request):
    """我的订单：按状态筛选查看个人全部订单。"""
    order_services.process_order_statuses()
    status = request.GET.get('status', '')
    qs = Order.objects.filter(user=request.current_user).select_related('vehicle__brand').order_by('-created_at')
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'orders/my_orders.html', {
        'page_obj': page_obj,
        'status': status,
        'status_choices': Order.STATUS_CHOICES,
        'query_string': get_copy.urlencode(),
    })


# ==================== 管理端：订单管理 ====================

@admin_required
def admin_order_list(request):
    """管理端订单列表：按状态、时间、用户筛选。"""
    order_services.process_order_statuses()
    status = request.GET.get('status', '')
    keyword = request.GET.get('keyword', '').strip()
    qs = Order.objects.select_related('user', 'vehicle__brand').order_by('-created_at')
    if status:
        qs = qs.filter(status=status)
    if keyword:
        qs = qs.filter(
            order_no__icontains=keyword
        ) | qs.filter(user__username__icontains=keyword) | qs.filter(user__phone__icontains=keyword)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'orders/admin_order_list.html', {
        'page_obj': page_obj,
        'status': status,
        'keyword': keyword,
        'status_choices': Order.STATUS_CHOICES,
        'query_string': get_copy.urlencode(),
    })


@admin_required
def admin_order_detail(request, order_id):
    """管理端订单详情：查看完整信息并执行审核/还车/异常等操作。"""
    order = get_object_or_404(
        Order.objects.select_related('user', 'vehicle__brand'), pk=order_id
    )
    return render(request, 'orders/admin_order_detail.html', {'order': order})


@admin_required
def admin_order_cancel(request, order_id):
    """管理端取消订单：处理异常情况并退款。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id)
    if order.status not in ['pending', 'paid']:
        messages.error(request, '仅待支付/已支付订单可取消')
        return redirect('orders:admin_order_detail', order_id=order.id)
    reason = request.POST.get('reason', '').strip()
    order_services.cancel_order(order, reason=reason or '管理员取消订单', by_admin=True)
    create_notification(order.user, '订单被管理员取消', f'订单 {order.order_no} 已被管理员取消。')
    messages.success(request, '订单已取消并完成退款')
    return redirect('orders:admin_order_detail', order_id=order.id)


@admin_required
def admin_order_verify(request, order_id):
    """管理端核验还车：订单转「已完成」并自动退还押金。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id)
    if order.status not in ['to_return', 'renting', 'overdue']:
        messages.error(request, '当前订单状态不可核验')
        return redirect('orders:admin_order_detail', order_id=order.id)
    order_services.complete_order(order)
    create_notification(order.user, '订单已完成', f'订单 {order.order_no} 已完成，押金 {order.deposit} 元已退还。')
    messages.success(request, '核验通过，订单已完成，押金已退还')
    return redirect('orders:admin_order_detail', order_id=order.id)


@admin_required
def admin_order_force_return(request, order_id):
    """管理端强制还车：直接完成还车流程。"""
    return admin_order_verify(request, order_id)


@admin_required
def admin_order_abnormal(request, order_id):
    """管理端标记异常处理：将逾期/待还车订单标记为异常处理。"""
    order = get_object_or_404(Order, pk=order_id)
    order_services.mark_abnormal(order)
    messages.success(request, '订单已标记为异常处理')
    return redirect('orders:admin_order_detail', order_id=order.id)


@admin_required
def admin_order_extend_approve(request, order_id):
    """管理端批准续租：延长还车日期并生成续租补款流水。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id)
    if order.extension_status != 'pending':
        messages.error(request, '该订单没有待审批的续租申请')
        return redirect('orders:admin_order_detail', order_id=order.id)
    order_services.approve_extension(order)
    create_notification(order.user, '续租已批准', f'订单 {order.order_no} 续租申请已批准，还车日期延至 {order.end_date}。')
    messages.success(request, '续租申请已批准')
    return redirect('orders:admin_order_detail', order_id=order.id)


@admin_required
def admin_order_extend_reject(request, order_id):
    """管理端驳回续租申请。"""
    from notifications.services import create_notification
    order = get_object_or_404(Order, pk=order_id)
    if order.extension_status != 'pending':
        messages.error(request, '该订单没有待审批的续租申请')
        return redirect('orders:admin_order_detail', order_id=order.id)
    order_services.reject_extension(order)
    create_notification(order.user, '续租被驳回', f'订单 {order.order_no} 续租申请被驳回。')
    messages.success(request, '续租申请已驳回')
    return redirect('orders:admin_order_detail', order_id=order.id)

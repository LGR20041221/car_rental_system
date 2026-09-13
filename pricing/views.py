"""
定价应用视图：价格预览接口 + 管理端定价规则/系统参数配置。
"""
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from pricing.forms import PriceRuleForm
from pricing.models import PriceRule, SystemSetting
from pricing.services import calculate_price, get_deposit, get_setting
from users.decorators import admin_required
from vehicles.models import Vehicle


@login_required
def price_preview(request):
    """
    价格预览接口（AJAX）：根据车辆与租期返回动态定价明细。

    用于下单确认页「原价 → 动态调价 → 优惠券 → 应付租金」的价格构成展示。
    """
    try:
        vehicle = get_object_or_404(Vehicle, pk=request.GET.get('vehicle_id'))
        start_date = datetime.date.fromisoformat(request.GET['start_date'])
        end_date = datetime.date.fromisoformat(request.GET['end_date'])
        today = datetime.date.today()
        if start_date < today:
            return JsonResponse({'success': False, 'message': '取车日期不能早于今天'})
        if end_date < start_date:
            return JsonResponse({'success': False, 'message': '还车日期不能早于取车日期'})
        if (end_date - start_date).days > 30:
            return JsonResponse({'success': False, 'message': '单次租赁最长 30 天'})
    except (KeyError, ValueError):
        return JsonResponse({'success': False, 'message': '参数错误'}, status=400)

    price_info = calculate_price(vehicle, start_date, end_date)
    deposit = get_deposit(vehicle)
    items = [
        {
            'date': item['date'].isoformat(),
            'base': float(item['base']),
            'factor': float(item['factor']),
            'dynamic': float(item['dynamic']),
            'notes': item['notes'],
        }
        for item in price_info['items']
    ]
    return JsonResponse({
        'success': True,
        'days': price_info['days'],
        'base_total': float(price_info['base_total']),
        'dynamic_total': float(price_info['dynamic_total']),
        'deposit': float(deposit),
        'items': items,
    })


@admin_required
def admin_pricing_list(request):
    """
    管理端定价规则列表：支持按规则名称/类型搜索，展示全部规则与系统参数。
    """
    keyword = request.GET.get('keyword', '').strip()
    rules = PriceRule.objects.all().order_by('id')
    if keyword:
        rules = rules.filter(
            name__icontains=keyword
        ) | rules.filter(rule_type__icontains=keyword)
    settings = SystemSetting.objects.all().order_by('id')
    return render(request, 'pricing/admin_pricing_list.html', {
        'rules': rules,
        'settings': settings,
        'keyword': keyword,
    })


@admin_required
def admin_pricing_create(request):
    """
    管理端新增定价规则：仅允许新增尚未配置的规则类型（已全部配置时给出提示）。
    """
    used = set(PriceRule.objects.values_list('rule_type', flat=True))
    available = [(v, l) for v, l in PriceRule.RULE_TYPES if v not in used]
    if not available:
        messages.info(request, '已配置全部规则类型，可编辑或删除现有规则后再新增')
        return redirect('pricing:admin_pricing_list')
    if request.method == 'POST':
        form = PriceRuleForm(request.POST)
        form.fields['rule_type'].choices = available
        if form.is_valid():
            form.save()
            messages.success(request, '定价规则添加成功')
            return redirect('pricing:admin_pricing_list')
        messages.error(request, '添加失败，请检查填写信息')
    else:
        form = PriceRuleForm()
        form.fields['rule_type'].choices = available
    return render(request, 'pricing/admin_pricing_form.html', {
        'form': form, 'rule': None,
    })


@admin_required
def admin_pricing_edit(request, rule_id):
    """管理端编辑定价规则（规则类型不可修改）。"""
    rule = get_object_or_404(PriceRule, pk=rule_id)
    if request.method == 'POST':
        form = PriceRuleForm(request.POST, instance=rule)
        form.fields['rule_type'].disabled = True
        if form.is_valid():
            form.save()
            messages.success(request, '定价规则已更新')
            return redirect('pricing:admin_pricing_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = PriceRuleForm(instance=rule)
        form.fields['rule_type'].disabled = True
    return render(request, 'pricing/admin_pricing_form.html', {
        'form': form, 'rule': rule,
    })


@admin_required
def admin_pricing_toggle(request, rule_id):
    """管理端启用/停用定价规则。"""
    rule = get_object_or_404(PriceRule, pk=rule_id)
    rule.enabled = not rule.enabled
    rule.save(update_fields=['enabled'])
    action = '已启用' if rule.enabled else '已停用'
    messages.success(request, f'规则「{rule.name}」{action}')
    return redirect('pricing:admin_pricing_list')


@admin_required
def admin_pricing_delete(request, rule_id):
    """管理端删除定价规则：删除后该规则按系统默认系数兜底。"""
    rule = get_object_or_404(PriceRule, pk=rule_id)
    name = rule.name
    rule.delete()
    messages.success(request, f'规则「{name}」已删除')
    return redirect('pricing:admin_pricing_list')


@admin_required
def admin_settings(request):
    """
    管理端系统设置：更新押金倍数、违约金倍数、自动取消时限等平台参数。
    """
    # 确保默认参数存在于数据库
    default_params = [
        ('deposit_multiple', '押金倍数：押金 = 基础日租金 × 倍数'),
        ('fine_multiple', '违约金倍数：超时日租金 × 倍数'),
        ('auto_cancel_minutes', '待支付订单自动取消时限（分钟）'),
    ]
    for key, description in default_params:
        if not SystemSetting.objects.filter(key=key).exists():
            SystemSetting.objects.create(
                key=key, value=get_setting(key), description=description
            )

    if request.method == 'POST':
        for key, _ in default_params:
            value = request.POST.get(key, '').strip()
            if value:
                obj, _ = SystemSetting.objects.get_or_create(key=key)
                obj.value = value
                obj.save(update_fields=['value', 'updated_at'])
        messages.success(request, '系统参数已保存')
        return redirect('pricing:admin_settings')
    settings = {s.key: s for s in SystemSetting.objects.all()}
    return render(request, 'pricing/admin_settings.html', {'settings': settings})

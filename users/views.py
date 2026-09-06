"""
用户应用视图：注册、登录、退出、密码找回、个人信息、修改密码、管理端用户维护。

所有视图使用函数视图（FBV），复杂逻辑下沉到 services/forms 层。
"""
import logging

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.decorators import admin_required, login_required
from notifications.services import create_notification
from users.forms import (
    AdminUserForm,
    ChangePasswordForm,
    ForgotPasswordForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    SendCodeForm,
)
from users.models import User
from users.services import send_verification_code

logger = logging.getLogger(__name__)


def send_code(request):
    """
    发送邮箱验证码（AJAX）：校验表单后调用服务层发送，返回 JSON 结果。
    """
    if request.method == 'POST':
        form = SendCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            success, message = send_verification_code(email)
            return JsonResponse({'success': success, 'message': message})
        errors = form.errors.get_json_data()
        return JsonResponse({'success': False, 'message': '邮箱格式不正确'}, status=400)
    return JsonResponse({'success': False, 'message': '请求方式错误'}, status=405)


def register(request):
    """
    用户注册：校验唯一性与验证码，成功后创建用户并跳转登录页。
    """
    if request.current_user is not None:
        return redirect('core:home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                phone=data['phone'],
                password=data['password'],
            )
            logger.info('新用户注册成功：%s', user.username)
            messages.success(request, '注册成功，请登录')
            return redirect('users:login')
        messages.error(request, '注册失败，请检查填写信息')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login(request):
    """
    用户登录：校验账号密码，成功后写入 session 并跳转。

    装饰器拦截时已把原访问路由写入登录页地址的 next 参数（?next=原路由），
    登录成功后直接回跳该原目标页；无 next 时管理员跳仪表盘、普通用户跳首页。
    """
    if request.current_user is not None:
        return redirect('core:home')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        # next 从路由查询参数中获取（表单提交回当前 ?next=... 地址）
        next_url = request.GET.get('next') or request.POST.get('next', '')
        if form.is_valid():
            user = form.user
            request.session['user_id'] = user.id
            messages.success(request, '登录成功')
            # 仅允许站内相对路径，防止开放重定向；优先回跳原目标页
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            if user.is_admin:
                return redirect('dashboard:admin_dashboard')
            return redirect('core:home')
        messages.error(request, form.errors['__all__'][0] if '__all__' in form.errors else '登录失败')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form})


def logout(request):
    """
    退出登录：清空 session 并跳转首页。
    """
    request.session.flush()
    messages.success(request, '已安全退出登录')
    return redirect('core:home')


def forgot_password(request):
    """
    密码找回：通过邮箱验证码重置密码。
    """
    if request.current_user is not None:
        return redirect('core:home')
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.filter(email=data['email']).first()
            user.password = make_password(data['new_password'])
            user.save(update_fields=['password', 'updated_at'])
            messages.success(request, '密码重置成功，请用新密码登录')
            return redirect('users:login')
        messages.error(request, '重置失败，请检查填写信息')
    else:
        form = ForgotPasswordForm()
    return render(request, 'users/forgot_password.html', {'form': form})


@login_required
def profile_home(request):
    """个人中心首页：默认展示「个人信息」子页。"""
    return redirect('users:profile_info')


@login_required
def profile_info(request):
    """
    个人信息维护：修改用户名、手机号、邮箱，均校验唯一性。
    管理员访问时渲染管理端布局（admin_base），普通用户渲染个人中心布局。
    """
    user = request.current_user
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人信息修改成功')
            return redirect('users:profile_info')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = ProfileForm(instance=user)
    template = 'users/admin_profile_info.html' if user.is_admin else 'users/profile_info.html'
    return render(request, template, {'form': form, 'title': '个人信息'})


@login_required
def change_password(request):
    """
    修改密码：校验原密码后更新为新密码。
    管理员访问时渲染管理端布局（admin_base）。
    """
    user = request.current_user
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST, user=user)
        if form.is_valid():
            user.password = make_password(form.cleaned_data['new_password'])
            user.save(update_fields=['password', 'updated_at'])
            messages.success(request, '密码修改成功，请重新登录')
            # 修改密码后重新登录
            request.session.flush()
            return redirect('users:login')
        messages.error(request, '修改失败，请检查填写信息')
    else:
        form = ChangePasswordForm(user=user)
    template = 'users/admin_change_password.html' if user.is_admin else 'users/change_password.html'
    return render(request, template, {'form': form, 'title': '修改密码'})


@admin_required
def admin_profile_info(request):
    """管理端个人信息页（复用个人信息逻辑，走 admin_base 布局）。"""
    return profile_info(request)


@admin_required
def admin_change_password(request):
    """管理端修改密码页（复用修改密码逻辑，走 admin_base 布局）。"""
    return change_password(request)


@admin_required
def admin_user_list(request):
    """
    管理端用户列表：支持按用户名/手机号/邮箱模糊搜索，分页展示。
    """
    keyword = request.GET.get('keyword', '').strip()
    qs = User.objects.all().order_by('-created_at')
    if keyword:
        qs = qs.filter(
            username__icontains=keyword
        ) | qs.filter(phone__icontains=keyword) | qs.filter(email__icontains=keyword)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'users/admin_user_list.html', {
        'page_obj': page_obj,
        'keyword': keyword,
        'query_string': get_copy.urlencode(),
    })


@admin_required
def admin_user_detail(request, user_id):
    """
    管理端用户详情：展示用户信息、订单与收藏概览。
    """
    user = get_object_or_404(User, pk=user_id)
    order_count = user.orders.count()
    favorite_count = user.favorites.count()
    return render(request, 'users/admin_user_detail.html', {
        'target_user': user,
        'order_count': order_count,
        'favorite_count': favorite_count,
    })


@admin_required
def admin_user_edit(request, user_id):
    """
    管理端编辑用户：修改资料、启用/禁用、赋予/回收管理员角色。
    """
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.password = make_password(password)
            user.save()
            messages.success(request, f'用户 {user.username} 信息已更新')
            return redirect('users:admin_user_detail', user_id=user.id)
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = AdminUserForm(instance=user)
    return render(request, 'users/admin_user_edit.html', {'form': form, 'target_user': user})


@admin_required
def admin_user_toggle(request, user_id):
    """
    管理端禁用/启用用户：POST 请求，仅可操作普通用户（不能禁用管理员）。
    """
    user = get_object_or_404(User, pk=user_id)
    if user.is_admin:
        messages.error(request, '管理员账号不允许禁用')
        return redirect('users:admin_user_list')
    user.is_active = not user.is_active
    user.save(update_fields=['is_active', 'updated_at'])
    action = '已启用' if user.is_active else '已禁用'
    messages.success(request, f'用户 {user.username} 已{action}')
    return redirect('users:admin_user_list')

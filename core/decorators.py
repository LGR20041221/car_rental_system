"""
自定义权限装饰器。

- login_required：保护需要登录才能访问的页面（校验 session 中是否存在用户）
- admin_required：保护需要管理员权限的页面（在登录基础上校验 is_admin 字段）

未登录访问受保护页面时，直接取当前路由拼接为登录页的 next 参数，
登录后即可回跳用户原本要访问的页面。
"""
from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


def _redirect_to_login(request):
    """跳转登录页，并把当前访问路由作为 next 参数带回，便于登录后回跳。"""
    login_url = reverse('users:login')
    next_path = quote(request.get_full_path())
    return redirect(f'{login_url}?next={next_path}')


def login_required(view_func):
    """
    登录保护装饰器：未登录用户跳转登录页（携带当前路由 next），并给出全局提示。
    通过中间件挂载的 request.current_user 判断登录状态。
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if getattr(request, 'current_user', None) is None:
            messages.error(request, '请先登录后再操作')
            return _redirect_to_login(request)
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    管理员保护装饰器：在登录校验基础上，检查用户 is_admin 字段。
    未登录跳转登录页（携带当前路由 next）；非管理员访问管理端提示权限不足并跳首页。
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'current_user', None)
        if user is None:
            messages.error(request, '请先登录后再操作')
            return _redirect_to_login(request)
        if not user.is_admin:
            messages.error(request, '权限不足：仅管理员可访问该页面')
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper

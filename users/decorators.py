"""
自定义权限装饰器。

- admin_required：在 Django 登录校验基础上，额外校验 is_admin 字段。

登录保护统一使用 django.contrib.auth.decorators.login_required，
未登录访问受保护页面时由 Django 自动跳转登录页并携带 next 参数。
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def admin_required(view_func):
    """
    管理员保护装饰器：未登录跳登录页；已登录但非管理员提示权限不足并跳首页。
    """
    @login_required(login_url='/login/')
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, '权限不足：仅管理员可访问该页面')
            return redirect('vehicles:home')
        return view_func(request, *args, **kwargs)
    return wrapper

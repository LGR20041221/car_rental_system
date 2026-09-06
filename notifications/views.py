"""
消息通知应用视图：消息中心、系统公告、管理端公告维护。
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required, login_required
from notifications.forms import AnnouncementForm
from notifications.models import Announcement, Notification


# ==================== 用户端：消息中心 ====================

@login_required
def notification_list(request):
    """消息中心：查看历史消息，区分已读/未读。"""
    notifications = Notification.objects.filter(
        user=request.current_user
    ).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()
    paginator = Paginator(notifications, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
        'unread_count': unread_count,
    })


@login_required
def mark_read(request, notification_id):
    """标记单条消息为已读。"""
    notification = get_object_or_404(
        Notification, pk=notification_id, user=request.current_user
    )
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    """全部标记为已读。"""
    Notification.objects.filter(user=request.current_user, is_read=False).update(is_read=True)
    messages.success(request, '已全部标记为已读')
    return redirect('notifications:list')


# ==================== 用户端：系统公告 ====================

def announcement_list(request):
    """系统公告列表：支持按标题模糊搜索。"""
    keyword = request.GET.get('keyword', '').strip()
    qs = Announcement.objects.filter(is_active=True).order_by('-is_top', '-created_at')
    if keyword:
        qs = qs.filter(title__icontains=keyword)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'notifications/announcement_list.html', {
        'page_obj': page_obj,
        'keyword': keyword,
        'query_string': get_copy.urlencode(),
    })


def announcement_detail(request, announcement_id):
    """公告详情页。"""
    announcement = get_object_or_404(
        Announcement, pk=announcement_id, is_active=True
    )
    return render(request, 'notifications/announcement_detail.html', {
        'announcement': announcement,
    })


# ==================== 管理端：公告管理 ====================

@admin_required
def admin_announcement_list(request):
    """管理端公告列表：支持搜索，每页 15 条。"""
    keyword = request.GET.get('keyword', '').strip()
    qs = Announcement.objects.select_related('publisher').order_by('-created_at')
    if keyword:
        qs = qs.filter(title__icontains=keyword)
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    return render(request, 'notifications/admin_announcement_list.html', {
        'page_obj': page_obj, 'keyword': keyword,
        'query_string': get_copy.urlencode(),
    })


@admin_required
def admin_announcement_create(request):
    """管理端发布公告。"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.publisher = request.current_user
            announcement.save()
            messages.success(request, '公告发布成功')
            return redirect('notifications:admin_announcement_list')
        messages.error(request, '发布失败，请检查填写信息')
    else:
        form = AnnouncementForm()
    return render(request, 'notifications/admin_announcement_form.html', {
        'form': form, 'title': '发布公告',
    })


@admin_required
def admin_announcement_edit(request, announcement_id):
    """管理端编辑公告。"""
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, '公告修改成功')
            return redirect('notifications:admin_announcement_list')
        messages.error(request, '保存失败，请检查填写信息')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'notifications/admin_announcement_form.html', {
        'form': form, 'title': '编辑公告', 'announcement': announcement,
    })


@admin_required
def admin_announcement_delete(request, announcement_id):
    """管理端删除公告。"""
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    announcement.delete()
    messages.success(request, '公告已删除')
    return redirect('notifications:admin_announcement_list')


@admin_required
def admin_announcement_toggle_top(request, announcement_id):
    """管理端置顶/取消置顶公告。"""
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    announcement.is_top = not announcement.is_top
    announcement.save(update_fields=['is_top'])
    action = '已置顶' if announcement.is_top else '已取消置顶'
    messages.success(request, f'公告「{announcement.title}」{action}')
    return redirect('notifications:admin_announcement_list')

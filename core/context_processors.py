"""
全局模板上下文处理器。

向所有模板注入：当前用户、未读消息数量、网站基础信息，减少各视图重复传参。
"""
from notifications.models import Notification


def global_context(request):
    """为所有模板提供当前用户与公共导航数据。"""
    current_user = getattr(request, 'current_user', None)
    unread_count = 0
    if current_user is not None:
        unread_count = Notification.objects.filter(
            user=current_user, is_read=False
        ).count()
    return {
        'current_user': current_user,
        'unread_count': unread_count,
        'site_name': '汽车租赁智能管理系统',
    }

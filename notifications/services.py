"""
消息通知服务：创建订单通知等系统消息。
"""
from notifications.models import Notification


def create_notification(user, title, content, type='order'):
    """向用户创建一条消息通知，供各业务视图调用。"""
    if user is None:
        return None
    return Notification.objects.create(user=user, title=title, content=content, type=type)

"""
自定义中间件：从 session 中恢复当前登录用户。

登录时写入 request.session['user_id']，中间件读取并挂载为 request.current_user；
会话失效或用户被禁用时自动清除会话。
"""
from users.models import User


class CurrentUserMiddleware:
    """当前用户中间件。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 默认无登录用户
        request.current_user = None
        user_id = request.session.get('user_id')
        if user_id:
            user = User.objects.filter(id=user_id, is_active=True).first()
            if user:
                request.current_user = user
            else:
                # 用户不存在或被禁用：清除会话
                request.session.flush()
        return self.get_response(request)

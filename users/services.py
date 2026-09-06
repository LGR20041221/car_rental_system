"""
用户服务层：邮箱验证码发送与校验。

验证码为 6 位随机数字，通过 Django 缓存存储：
- 验证码 Key：verification:{email}（TTL 5 分钟）
- 发送时间 Key：sent_at:{email}（TTL 60 秒，限制重发频率）
开发阶段通过 console 邮件后端输出到终端，生产环境切换 SMTP。
"""
import random

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail


def send_verification_code(email):
    """
    向指定邮箱发送 6 位随机验证码。

    返回 (success, message)：success 为是否发送成功，message 为提示文案。
    """
    # 60 秒内不可重发
    if cache.get(f'sent_at:{email}'):
        return False, '发送过于频繁，请 60 秒后再试'
    # 生成 6 位纯数字验证码
    code = str(random.randint(100000, 999999))
    # 写入缓存：验证码 300 秒过期，发送时间戳 60 秒过期
    cache.set(f'verification:{email}', code, settings.VERIFY_CODE_TTL)
    cache.set(f'sent_at:{email}', True, settings.VERIFY_CODE_SEND_INTERVAL)
    # 开发阶段 console 打印到终端，生产环境对接 SMTP 邮件服务
    subject = f'【{settings.EMAIL_FROM_NAME}】邮箱验证码'
    message = f'您的验证码是：{code}，{settings.VERIFY_CODE_TTL // 60} 分钟内有效，请勿泄露给他人。'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    return True, '验证码已发送，请注意查收'


def verify_code(email, code):
    """
    校验验证码：与缓存中的值比对，成功后立即删除该 Key 防止重复使用。
    """
    if not code:
        return False
    cached = cache.get(f'verification:{email}')
    if cached and cached == code.strip():
        cache.delete(f'verification:{email}')
        return True
    return False

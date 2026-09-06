"""
全流程冒烟测试脚本。

覆盖：注册验证码、登录、车辆浏览/筛选/收藏、下单/价格预览/支付/取消/
续租/还车、评价、个人中心、管理端全部页面与操作。

运行：python test_smoke.py
"""
import os
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'car_rental_system.settings')
import django

django.setup()

from django.test import Client
from django.core.cache import cache
from django.db.models import Count

from users.models import User
from vehicles.models import Vehicle
from orders.models import Order
from reviews.models import Review
from favorites.models import Favorite

PASS = 0
FAIL = 0


def check(name, cond, extra=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  ✅ {name}')
    else:
        FAIL += 1
        print(f'  ❌ {name} {extra}')


def main():
    print('========== 1. 公共页面 ==========')
    c = Client()
    check('首页', c.get('/').status_code == 200)
    check('车辆列表', c.get('/vehicles/').status_code == 200)
    check('车辆筛选', c.get('/vehicles/?category=1&sort=price_asc').status_code == 200)
    vid = Vehicle.objects.first().id
    check('车辆详情', c.get(f'/vehicles/{vid}/').status_code == 200)
    check('登录页', c.get('/login/').status_code == 200)
    check('注册页', c.get('/register/').status_code == 200)
    check('找回密码', c.get('/forgot-password/').status_code == 200)
    check('公告列表', c.get('/announcements/').status_code == 200)

    print('========== 2. 用户注册 + 验证码 ==========')
    import random
    import time
    suffix = str(int(time.time()))[-6:]
    new_username = f'newuser{suffix}'
    new_email = f'newuser{suffix}@test.com'
    new_phone = '139' + str(random.randint(10 ** 7, 10 ** 8 - 1))
    cache.clear()
    resp = c.post('/send-code/', {'email': new_email})
    check('发送验证码接口', resp.status_code == 200 and resp.json().get('success'))
    code = cache.get(f'verification:{new_email}')
    check('验证码写入缓存', code is not None and len(code) == 6)
    # 60秒内重发应被拒绝
    resp = c.post('/send-code/', {'email': new_email})
    check('60秒内禁止重发', resp.json().get('success') is False)
    resp = c.post('/register/', {
        'username': new_username, 'phone': new_phone, 'email': new_email,
        'code': code, 'password': 'test123456', 'confirm_password': 'test123456',
    })
    check('注册成功', resp.status_code == 302)
    check('注册后用户存在', User.objects.filter(username=new_username).exists())
    # 重复注册校验：使用已存在的用户名
    cache.clear()
    c.post('/send-code/', {'email': 'dup@test.com'})
    code2 = cache.get('verification:dup@test.com')
    resp = c.post('/register/', {
        'username': 'user01', 'phone': '139' + str(random.randint(10 ** 7, 10 ** 8 - 1)),
        'email': 'dup@test.com',
        'code': code2, 'password': '12345678', 'confirm_password': '12345678',
    })
    check('重复用户名被拒绝', resp.status_code == 200 and '该用户名已被注册' in resp.content.decode('utf-8'))

    print('========== 3. 用户登录与浏览 ==========')
    resp = c.post('/login/', {'username': 'user01', 'password': 'test123456'})
    check('用户登录', resp.status_code == 302)
    # 价格预览
    start = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    resp = c.get('/price-preview/', {'vehicle_id': vid, 'start_date': start, 'end_date': end})
    check('价格预览', resp.status_code == 200 and resp.json().get('success'))
    # 收藏
    resp = c.post('/favorites/toggle/', {'vehicle_id': vid})
    check('收藏车辆', resp.status_code == 200 and resp.json().get('is_favorited'))
    check('收藏记录', Favorite.objects.filter(user__username='user01', vehicle_id=vid).exists())
    resp = c.post('/favorites/toggle/', {'vehicle_id': vid})
    check('取消收藏', resp.json().get('is_favorited') is False)
    check('个人中心', c.get('/profile/info/').status_code == 200)
    check('我的订单', c.get('/profile/orders/').status_code == 200)
    check('我的收藏', c.get('/profile/favorites/').status_code == 200)
    check('我的优惠券', c.get('/profile/coupons/').status_code == 200)
    check('我的评价', c.get('/profile/reviews/').status_code == 200)
    check('消费账单', c.get('/profile/bills/').status_code == 200)
    check('消息中心', c.get('/profile/notifications/').status_code == 200)

    print('========== 4. 下单 -> 支付 -> 取消 ==========')
    from orders import services as order_services
    # 寻找无冲突的车辆与时段
    vehicle = None
    start = end = None
    for v in Vehicle.objects.filter(status='available'):
        s = datetime.date.today() + datetime.timedelta(days=2)
        e = datetime.date.today() + datetime.timedelta(days=4)
        if not order_services.check_conflict(v, s, e):
            vehicle, start, end = v, s, e
            break
    check('找到可下单车辆', vehicle is not None)
    resp = c.post('/orders/create/', {
        'vehicle_id': vehicle.id, 'start_date': start.isoformat(), 'end_date': end.isoformat(),
        'pickup_location': '市中心旗舰店', 'return_location': '机场店',
    })
    check('创建订单', resp.status_code == 302)
    order = Order.objects.filter(user__username='user01', status='pending').order_by('-created_at').first()
    check('订单生成', order is not None)
    check('订单详情', c.get(f'/orders/{order.id}/').status_code == 200)
    resp = c.post(f'/orders/{order.id}/pay/')
    order.refresh_from_db()
    check('订单支付', resp.status_code == 302 and order.status == 'paid')
    check('支付流水', order.payments.filter(payment_type='rent').exists())
    resp = c.post(f'/orders/{order.id}/cancel/', {'reason': '测试取消'})
    order.refresh_from_db()
    check('取消订单', resp.status_code == 302 and order.status == 'cancelled')

    print('========== 5. 下单 -> 支付 -> 租期 -> 还车 -> 评价 ==========')
    vehicle2 = None
    for v in Vehicle.objects.filter(status='available').exclude(pk=vehicle.pk):
        s = datetime.date.today() + datetime.timedelta(days=2)
        e = datetime.date.today() + datetime.timedelta(days=6)
        if not order_services.check_conflict(v, s, e):
            vehicle2, start, end = v, s, e
            break
    check('找到可下单车辆2', vehicle2 is not None)
    resp = c.post('/orders/create/', {
        'vehicle_id': vehicle2.id, 'start_date': start.isoformat(), 'end_date': end.isoformat(),
        'pickup_location': '高铁站店', 'return_location': '高铁站店',
    })
    order2 = Order.objects.filter(user__username='user01', status='pending').order_by('-created_at').first()
    check('订单2生成', order2 is not None)
    c.post(f'/orders/{order2.id}/pay/')
    order2.refresh_from_db()
    check('订单2已支付', order2.status == 'paid')
    # 模拟时间推进：将租期调整为已开始，触发自动进入「租赁中」
    order2.start_date = datetime.date.today() - datetime.timedelta(days=1)
    order2.end_date = datetime.date.today() + datetime.timedelta(days=3)
    order2.save()
    order_services.process_order_statuses()
    order2.refresh_from_db()
    check('自动开始租期', order2.status == 'renting')
    resp = c.post(f'/orders/{order2.id}/confirm-return/')
    order2.refresh_from_db()
    check('确认还车', resp.status_code == 302 and order2.status == 'to_return')
    # 续租申请
    new_end = (datetime.date.today() + datetime.timedelta(days=6)).isoformat()
    resp = c.post(f'/orders/{order2.id}/extend/', {'extend_to_date': new_end})
    order2.refresh_from_db()
    check('续租申请', resp.status_code == 302 and order2.extension_status == 'pending')
    check('续租金额>0', order2.extend_rent > 0)

    print('========== 6. 管理员操作 ==========')
    adm = Client()
    resp = adm.post('/login/', {'username': 'admin', 'password': 'admin123'})
    check('管理员登录', resp.status_code == 302)
    admin_pages = [
        '/admin/', '/admin/dashboard/', '/admin/dashboard/data/',
        '/admin/users/', '/admin/vehicles/', '/admin/vehicles/brands/',
        '/admin/vehicles/categories/', '/admin/orders/', '/admin/coupons/',
        '/admin/pricing/', '/admin/settings/', '/admin/reviews/',
        '/admin/announcements/', '/admin/favorites/', '/admin/finance/',
        '/admin/finance/refunds/', '/admin/profile/info/', '/admin/profile/password/',
    ]
    for path in admin_pages:
        check(f'管理页面 {path}', adm.get(path).status_code == 200)
    # 续租审批
    resp = adm.post(f'/admin/orders/{order2.id}/extend-approve/')
    order2.refresh_from_db()
    check('批准续租', resp.status_code == 302 and order2.extension_status == 'approved')
    # 核验还车（完成订单）
    resp = adm.post(f'/admin/orders/{order2.id}/verify/')
    order2.refresh_from_db()
    check('核验还车完成', resp.status_code == 302 and order2.status == 'completed')
    check('押金已退还', order2.deposit_returned and order2.payments.filter(payment_type='deposit_refund').exists())
    # 用户评价
    resp = c.post(f'/reviews/submit/{order2.id}/', {'rating': '5', 'content': '冒烟测试评价'})
    check('提交评价', resp.status_code == 302 and Review.objects.filter(order=order2).exists())

    print('========== 7. 权限控制 ==========')
    check('普通用户访问管理端被拒', c.get('/admin/').status_code == 302)
    resp = c.get('/vehicles/10000/')
    check('访问不存在车辆返回404', resp.status_code == 404)

    print(f'\n========== 结果：通过 {PASS} 项，失败 {FAIL} 项 ==========')
    return 1 if FAIL else 0


if __name__ == '__main__':
    raise SystemExit(main())

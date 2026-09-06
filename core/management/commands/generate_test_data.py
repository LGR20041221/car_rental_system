"""
一键生成测试数据管理命令。

用法：python manage.py generate_test_data [--flush]
--flush：先清空业务表再生成（保留系统参数与定价规则）。

生成内容（对应需求 9.1 测试数据表）：
- 管理员 1 名（admin/admin123）、普通用户 49 名（密码 test123456）
- 品牌 8 个、分类 3 个、车辆 30 辆、车辆图片 90 张
- 订单 100 单（覆盖各状态）、评价 40 条
- 优惠券 10 张、通知 60 条、公告 10 条、收藏 80 条
"""
import io
import os
import random
import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from favorites.models import Favorite
from notifications.models import Announcement, Notification
from orders.models import Order
from payments.models import Coupon, Payment, UserCoupon
from pricing.models import PriceRule, SystemSetting
from pricing.services import calculate_price, get_deposit, get_fine
from reviews.models import Review
from users.models import User
from vehicles.models import Brand, Category, Vehicle, VehicleImage

# ---------- 常量 ----------
BRANDS = [
    ('大众', '德系经典品牌，品质可靠'), ('丰田', '日系耐用品牌，节能省油'),
    ('本田', '日系运动品牌，操控出色'), ('奔驰', '德系豪华品牌，尊贵舒适'),
    ('宝马', '德系豪华品牌，驾驶乐趣'), ('奥迪', '德系科技品牌，智能四驱'),
    ('比亚迪', '国产品牌领跑者，新能源'), ('特斯拉', '纯电科技品牌，智能驾驶'),
]
CATEGORIES = ['轿车', 'SUV', 'MPV']
MODEL_POOL = {
    '大众': ['朗逸', '速腾', '迈腾', '途观L'],
    '丰田': ['卡罗拉', '凯美瑞', 'RAV4荣放'],
    '本田': ['思域', '雅阁', 'CR-V'],
    '奔驰': ['C级', 'E级', 'GLC'],
    '宝马': ['3系', '5系', 'X3'],
    '奥迪': ['A4L', 'A6L', 'Q5L'],
    '比亚迪': ['汉', '宋PLUS', '秦PLUS'],
    '特斯拉': ['Model 3', 'Model Y'],
}
COLORS = ['白色', '黑色', '银色', '蓝色', '红色', '灰色']
REVIEW_TEXTS = [
    '车辆很新，车况良好，取还车都很方便！', '动力强劲，空间宽敞，很满意的一次体验。',
    '工作人员服务态度好，流程清晰。', '价格合理，车况不错，推荐！',
    '油耗比预期低，驾驶体验很棒。', '整体不错，就是取车地点稍微有点远。',
    '车很干净，客服响应及时，下次还会选择。', '底盘扎实，高速很稳，性价比高。',
    '外观帅气，拍照很出片，适合短途旅行。', '续航精准，充电方便，电动车体验很好。',
]
NOTICE_TEXTS = [
    '您的订单已创建，请尽快完成支付。', '支付成功，车辆已为您保留。',
    '取车提醒：您的租期即将开始，请按时取车。', '还车提醒：您的租期即将结束，请按时还车。',
    '您的续租申请已提交，等待管理员审批。', '订单已完成，感谢您的使用，期待再次光临。',
]
ANNOUNCEMENTS = [
    ('平台上线公告', '汽车租赁智能管理系统正式上线，注册即享新人优惠券！'),
    ('国庆假期租车指南', '国庆出行高峰即将到来，建议提前 7 天预订，早鸟优惠最高立减 10%。'),
    ('系统维护通知', '本周六凌晨 2:00-4:00 进行系统维护，期间部分功能暂不可用。'),
    ('五一出行优惠', '五一期间全平台动态定价调整，长租 7 天以上享 85 折优惠。'),
    ('会员等级权益升级', '平台会员体系升级，收藏与评价可获得更多优惠券奖励。'),
    ('新能源汽车体验季', '比亚迪、特斯拉等新能源车型全面上线，绿色出行更环保。'),
    ('安全驾驶提示', '请遵守交通规则，系好安全带，安全文明出行。'),
    ('春节租车预订开启', '春节出行车辆预订通道已开启，热门车型手慢无。'),
    ('服务网点扩展', '新增 3 个取还车网点，覆盖主城区主要商圈。'),
    ('感谢信', '感谢各位用户的支持与反馈，我们将持续优化租车体验。'),
]


def _placeholder_image(width, height, color):
    """生成纯色占位图片（模拟车辆/品牌图片）。"""
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    # 绘制一个简易车身色块，增加可辨识度
    draw.rounded_rectangle([width * 0.1, height * 0.35, width * 0.9, height * 0.8],
                           radius=18, fill=(min(255, color[0] + 30), min(255, color[1] + 30), min(255, color[2] + 30)))
    draw.ellipse([width * 0.18, height * 0.72, width * 0.34, height * 0.9], fill=(30, 58, 138))
    draw.ellipse([width * 0.66, height * 0.72, width * 0.82, height * 0.9], fill=(30, 58, 138))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return ContentFile(buf.getvalue(), name=f'car_{random.randint(10000, 99999)}.png')


class Command(BaseCommand):
    """生成测试数据命令。"""
    help = '一键生成系统测试数据（用户、品牌、车辆、订单、评价、优惠券等）'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='生成前清空已有业务数据')

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('开始生成测试数据...')
        if options['flush']:
            self._flush_data()
            self.stdout.write('已清空旧数据')

        users = self._create_users()
        categories, brands, vehicles = self._create_vehicles()
        coupons = self._create_coupons()
        orders = self._create_orders(users, vehicles, coupons)
        self._create_reviews(users, orders)
        self._create_favorites(users, vehicles)
        self._create_notifications(users, orders)
        self._create_announcements(users)
        self._create_pricing_config()

        self.stdout.write(self.style.SUCCESS(
            f'测试数据生成完成！\n'
            f'  管理员账号：admin / admin123\n'
            f'  普通用户：user01 ~ user49（密码 test123456）\n'
            f'  品牌 {len(brands)} 个、分类 {len(categories)} 个、车辆 {len(vehicles)} 辆\n'
            f'  订单 {len(orders)} 单、优惠券 {len(coupons)} 张'
        ))

    def _flush_data(self):
        """清空业务数据与媒体文件（保留价格规则与系统参数）。"""
        # 注意删除顺序：Payment/Review 外键引用 Order，UserCoupon 引用 Coupon
        for model in [Favorite, Notification, Announcement, Payment, Review,
                      UserCoupon, Coupon, Order, VehicleImage, Vehicle,
                      Brand, Category]:
            model.objects.all().delete()
        User.objects.all().delete()
        # 清理上传的媒体文件
        for sub in ['vehicles', 'brands', 'avatars']:
            directory = os.path.join(settings.MEDIA_ROOT, sub)
            if os.path.isdir(directory):
                for fname in os.listdir(directory):
                    try:
                        os.remove(os.path.join(directory, fname))
                    except OSError:
                        pass

    def _create_users(self):
        """创建 1 名管理员 + 49 名普通用户。"""
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@carrental.com',
                'phone': '13800000000',
                'is_admin': True,
                'is_staff': True,
            },
        )
        admin.set_password('admin123')
        admin.save()
        users = [admin]
        for i in range(1, 50):
            username = f'user{i:02d}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'user{i:02d}@test.com',
                    'phone': f'138{i:05d}{i % 10}{i % 10}',
                },
            )
            if created:
                user.set_password('test123456')
                user.save()
            users.append(user)
        # 分散注册时间（近 30 天），让用户增长趋势图更有意义
        now = timezone.now()
        for user in users[1:]:
            user.created_at = now - datetime.timedelta(days=random.randint(1, 30))
            user.save(update_fields=['created_at'])
        return users

    def _create_vehicles(self):
        """创建分类、品牌与车辆，并为每辆车生成 3 张占位图片。"""
        categories = [Category.objects.create(name=name) for name in CATEGORIES]
        brands = [
            Brand.objects.create(name=name, description=desc)
            for name, desc in BRANDS
        ]
        vehicles = []
        cat_map = {'轿车': 0, 'SUV': 1, 'MPV': 2}
        for i in range(30):
            brand = brands[i % len(brands)]
            cat_name = '轿车' if i < 13 else ('SUV' if i < 25 else 'MPV')
            category = categories[cat_map[cat_name]]
            model_name = random.choice(MODEL_POOL[brand.name])
            price = random.choice([168, 188, 208, 238, 268, 298, 328, 358, 398, 458, 528])
            if cat_name == 'SUV':
                price += 80
            elif cat_name == 'MPV':
                price += 120
            color = random.choice(COLORS)
            vehicle = Vehicle.objects.create(
                brand=brand,
                category=category,
                model_name=model_name,
                plate_number=f'京A·{random.randint(10000, 99999)}',
                color=color,
                seats=7 if cat_name == 'MPV' else 5,
                displacement=random.choice(['1.4T', '1.5T', '2.0T', '1.8L', '纯电']),
                fuel_type=random.choice(['gasoline', 'hybrid', 'electric']),
                daily_rent=price,
                status=random.choices(['available', 'available', 'available', 'renting'], weights=[3, 3, 3, 1])[0],
                description=f'{brand.name} {model_name}，{color}外观，适合商务出行与家庭用车。',
            )
            # 封面图 + 2 张角度图
            base_color = (random.randint(40, 90), random.randint(60, 120), random.randint(140, 210))
            cover = _placeholder_image(800, 500, base_color)
            # FieldFile.save() 会自动拼接 upload_to，这里只传文件名
            vehicle.cover_image.save(f'car_{vehicle.id}_cover.png', cover, save=True)
            for idx in range(3):
                img_file = _placeholder_image(800, 500, base_color)
                VehicleImage.objects.create(
                    vehicle=vehicle,
                    image=img_file,
                    sort_order=idx,
                )
            vehicles.append(vehicle)
        return categories, brands, vehicles

    def _create_coupons(self):
        """创建 10 张优惠券模板并随机分配给部分用户。"""
        coupon_data = [
            ('新人立减券', 'fixed', 50, 300, 200),
            ('周末畅游券', 'fixed', 30, 200, 200),
            ('长租 95 折', 'discount', 9.5, 0, 100),
            ('88 折通用券', 'discount', 8.8, 500, 100),
            ('满 1000 减 150', 'fixed', 150, 1000, 80),
            ('满 500 减 80', 'fixed', 80, 500, 120),
            ('七折体验券', 'discount', 7.0, 800, 60),
            ('满 300 减 40', 'fixed', 40, 300, 150),
            ('92 折优惠券', 'discount', 9.2, 0, 150),
            ('VIP 满减券', 'fixed', 200, 1500, 50),
        ]
        coupons = []
        today = datetime.date.today()
        for name, dtype, value, min_amount, total in coupon_data:
            coupon = Coupon.objects.create(
                name=name,
                discount_type=dtype,
                value=value,
                min_amount=min_amount,
                total_count=total,
                start_date=today - datetime.timedelta(days=30),
                end_date=today + datetime.timedelta(days=60),
                is_active=True,
            )
            coupons.append(coupon)
        return coupons

    def _create_orders(self, users, vehicles, coupons):
        """创建 100 单覆盖各状态的订单，并生成支付流水。"""
        normal_users = [u for u in users if not u.is_admin]
        orders = []
        today = datetime.date.today()
        now = timezone.now()

        def build_order(status):
            """按状态构造 (start, end, status, is_overdue, fine)。"""
            if status == 'completed':
                start = today - datetime.timedelta(days=random.randint(10, 60))
                end = start + datetime.timedelta(days=random.randint(1, 8))
                return start, end, status, False, 0
            if status == 'cancelled':
                start = today - datetime.timedelta(days=random.randint(0, 10))
                end = start + datetime.timedelta(days=random.randint(1, 5))
                return start, end, status, False, 0
            if status == 'pending':
                start = today + datetime.timedelta(days=random.randint(1, 15))
                end = start + datetime.timedelta(days=random.randint(1, 5))
                return start, end, status, False, 0
            if status == 'paid':
                start = today + datetime.timedelta(days=random.randint(1, 20))
                end = start + datetime.timedelta(days=random.randint(1, 7))
                return start, end, status, False, 0
            if status == 'renting':
                start = today - datetime.timedelta(days=random.randint(1, 5))
                end = today + datetime.timedelta(days=random.randint(1, 5))
                return start, end, status, False, 0
            if status == 'to_return':
                start = today - datetime.timedelta(days=random.randint(4, 10))
                return start, today, status, False, 0
            if status == 'overdue':
                end = today - datetime.timedelta(days=random.randint(1, 5))
                start = end - datetime.timedelta(days=random.randint(3, 12))
                days = (today - end).days
                return start, end, status, True, 0
            # abnormal
            start = today - datetime.timedelta(days=random.randint(3, 15))
            end = start + datetime.timedelta(days=random.randint(1, 6))
            return start, end, status, False, 0

        dist = (['completed'] * 50 + ['cancelled'] * 12 + ['pending'] * 6 +
                ['paid'] * 12 + ['renting'] * 8 + ['to_return'] * 4 +
                ['overdue'] * 5 + ['abnormal'] * 3)
        random.shuffle(dist)

        for idx, status in enumerate(dist[:100]):
            user = random.choice(normal_users)
            vehicle = random.choice(vehicles)
            start, end, _, is_overdue, _ = build_order(status)
            price_info = calculate_price(vehicle, start, end)
            deposit = get_deposit(vehicle)
            fine = 0
            if status == 'overdue':
                fine = get_fine(vehicle, (today - end).days, end + datetime.timedelta(days=1))
            order = Order.objects.create(
                order_no=f'CR{now.strftime("%Y%m%d")}{idx + 1:05d}',
                user=user, vehicle=vehicle,
                start_date=start, end_date=end,
                days=price_info['days'],
                pickup_location=random.choice(['机场店', '高铁站店', '市中心旗舰店', '万达广场店']),
                return_location=random.choice(['机场店', '高铁站店', '市中心旗舰店', '万达广场店']),
                base_rent=price_info['base_total'],
                dynamic_rent=price_info['dynamic_total'],
                payable_rent=price_info['dynamic_total'],
                deposit=deposit,
                fine=fine,
                total_amount=price_info['dynamic_total'] + deposit + fine,
                status=status,
                is_overdue=is_overdue,
                cancel_reason='用户行程变更取消' if status == 'cancelled' else '',
            )
            # 关键时间节点
            if status == 'completed':
                order.paid_at = order.created_at
                order.pickup_at = order.created_at + datetime.timedelta(hours=2)
                order.return_at = timezone.make_aware(
                    datetime.datetime.combine(end, datetime.time(18, 0))
                )
                order.completed_at = order.return_at + datetime.timedelta(hours=2)
                order.deposit_returned = True
            elif status == 'paid':
                order.paid_at = order.created_at
            elif status in ['renting', 'to_return', 'overdue']:
                order.paid_at = order.created_at
                order.pickup_at = timezone.make_aware(
                    datetime.datetime.combine(start, datetime.time(10, 0))
                )
                if status == 'to_return':
                    order.return_at = timezone.make_aware(
                        datetime.datetime.combine(today, datetime.time(18, 0))
                    )
            elif status == 'overdue':
                order.paid_at = order.created_at
                order.pickup_at = timezone.make_aware(
                    datetime.datetime.combine(start, datetime.time(10, 0))
                )
            order.save()
            # 支付流水
            if status in ['paid', 'renting', 'to_return', 'completed', 'overdue', 'abnormal']:
                Payment.objects.create(order=order, user=user, amount=order.payable_rent,
                                       payment_type='rent', method='在线支付-租金')
                Payment.objects.create(order=order, user=user, amount=order.deposit,
                                       payment_type='deposit', method='在线支付-押金')
                if order.deposit_returned:
                    Payment.objects.create(order=order, user=user, amount=order.deposit,
                                           payment_type='deposit_refund', method='还车核验-押金退还')
            if status == 'overdue' and fine > 0:
                Payment.objects.create(order=order, user=user, amount=fine,
                                       payment_type='fine', method='逾期违约金')
            orders.append(order)

        # 部分订单使用优惠券并生成抵扣
        used_orders = [o for o in orders if o.status in ['paid', 'renting', 'to_return', 'completed']]
        for order in random.sample(used_orders, min(15, len(used_orders))):
            user = order.user
            coupon = random.choice(Coupon.objects.all())
            if not UserCoupon.objects.filter(user=user, coupon=coupon).exists():
                uc = UserCoupon.objects.create(user=user, coupon=coupon, is_used=True,
                                               order_id=order.id)
                order.coupon_id = uc.id
                order.coupon_name = coupon.name
                if coupon.discount_type == 'fixed':
                    discount = min(coupon.value, order.dynamic_rent)
                else:
                    discount = round(order.dynamic_rent * (1 - coupon.value / 10), 2)
                order.coupon_discount = discount
                order.payable_rent = max(order.dynamic_rent - discount, 0)
                order.total_amount = order.payable_rent + order.deposit + order.fine
                order.save()

        # 按状态分散创建时间，让订单趋势/收入趋势图更有意义
        for order in orders:
            if order.status in ('pending', 'paid'):
                created = now - datetime.timedelta(days=random.randint(0, 2), hours=random.randint(1, 12))
            elif order.status in ('renting', 'to_return'):
                created = now - datetime.timedelta(days=random.randint(1, 8))
            elif order.status in ('overdue', 'abnormal'):
                created = now - datetime.timedelta(days=random.randint(3, 15))
            elif order.status == 'cancelled':
                created = now - datetime.timedelta(days=random.randint(1, 10))
            else:  # completed
                created = now - datetime.timedelta(days=random.randint(2, 25))
            order.created_at = created
            order.save(update_fields=['created_at'])
            order.payments.update(created_at=created)
        return orders

    def _create_reviews(self, users, orders):
        """为部分已完成订单生成评价。"""
        completed = [o for o in orders if o.status == 'completed']
        for order in random.sample(completed, min(40, len(completed))):
            if hasattr(order, 'review'):
                continue
            Review.objects.create(
                order=order, user=order.user, vehicle=order.vehicle,
                rating=random.randint(3, 5),
                content=random.choice(REVIEW_TEXTS),
            )

    def _create_favorites(self, users, vehicles):
        """生成用户收藏记录。"""
        normal_users = [u for u in users if not u.is_admin]
        created = set()
        while len(created) < 80:
            user = random.choice(normal_users)
            vehicle = random.choice(vehicles)
            key = (user.id, vehicle.id)
            if key in created:
                continue
            created.add(key)
            Favorite.objects.create(user=user, vehicle=vehicle)

    def _create_notifications(self, users, orders):
        """生成订单通知消息。"""
        normal_users = [u for u in users if not u.is_admin]
        for _ in range(60):
            user = random.choice(normal_users)
            order = random.choice(orders)
            Notification.objects.create(
                user=user,
                title=random.choice(['订单通知', '取车提醒', '还车提醒', '支付成功', '续租申请']),
                content=random.choice(NOTICE_TEXTS) + f'（订单号：{order.order_no}）',
                type='order',
                is_read=random.random() < 0.6,
            )

    def _create_announcements(self, users):
        """生成系统公告。"""
        admin = User.objects.filter(is_admin=True).first()
        for i, (title, content) in enumerate(ANNOUNCEMENTS):
            Announcement.objects.create(
                title=title, content=content,
                publisher=admin,
                is_top=(i < 2),
                is_active=True,
            )

    def _create_pricing_config(self):
        """初始化定价规则与系统参数。"""
        rules = [
            ('holiday', '节假日上浮', '0.30', '法定节假日期间租金上浮 30%'),
            ('weekend', '周末上浮', '0.20', '周末租金上浮 20%'),
            ('peak', '旺季调价', '0.20', '预订率超过 80% 时上调 20%'),
            ('off_season', '淡季促销', '-0.15', '预订率低于 30% 时下调 15%'),
            ('early_bird', '早鸟优惠', '-0.10', '提前 7 天以上预订优惠 10%'),
            ('long_rent', '长租优惠', '-0.15', '连续租赁 7 天及以上优惠 15%'),
        ]
        for rule_type, name, factor, desc in rules:
            PriceRule.objects.update_or_create(
                rule_type=rule_type,
                defaults={'name': name, 'factor': factor, 'enabled': True, 'description': desc},
            )
        settings = [
            ('deposit_multiple', '1', '押金倍数：押金 = 基础日租金 × 倍数'),
            ('fine_multiple', '1.5', '违约金倍数：超时日租金 × 倍数'),
            ('auto_cancel_minutes', '30', '待支付订单自动取消时限（分钟）'),
        ]
        for key, value, desc in settings:
            SystemSetting.objects.update_or_create(
                key=key, defaults={'value': value, 'description': desc},
            )

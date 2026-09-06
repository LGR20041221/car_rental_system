"""
动态定价服务（智能特色核心）。

按价格计算链逐日计算动态日租金：
基础日租金 → 动态定价（节假日/周末/旺季/淡季/早鸟/长租）→ 逐日累加。
还提供押金、违约金的计算，供下单与订单服务调用。
"""
import datetime
from decimal import ROUND_HALF_UP, Decimal

from core.holidays import is_holiday
from pricing.models import PriceRule, SystemSetting

# 各规则的默认调整系数（数据库未配置时兜底）
DEFAULT_RULES = {
    'holiday': Decimal('0.30'),    # 节假日上浮 +30%
    'weekend': Decimal('0.20'),    # 周末上浮 +20%
    'peak': Decimal('0.20'),       # 旺季调价 +20%（预订率 > 80%）
    'off_season': Decimal('-0.15'),  # 淡季促销 -15%（预订率 < 30%）
    'early_bird': Decimal('-0.10'),  # 早鸟优惠 -10%（提前 ≥ 7 天）
    'long_rent': Decimal('-0.15'),   # 长租优惠 -15%（连续 ≥ 7 天）
}

# 系统参数默认值
DEFAULT_SETTINGS = {
    'deposit_multiple': '1',     # 押金倍数：押金 = 基础日租金 × 倍数
    'fine_multiple': '1.5',      # 违约金倍数：超时日租金 × 倍数
    'auto_cancel_minutes': '30',  # 待支付订单自动取消时限（分钟）
}


def get_active_rules():
    """获取启用中的定价规则，映射 rule_type -> factor（未配置时用默认值兜底）。"""
    rules = dict(DEFAULT_RULES)
    for rule in PriceRule.objects.filter(enabled=True):
        rules[rule.rule_type] = rule.factor
    return rules


def get_setting(key):
    """读取系统参数，未配置时返回默认值。"""
    value = SystemSetting.get(key)
    if value is None:
        return DEFAULT_SETTINGS.get(key)
    return value


def get_booking_rate(vehicle):
    """
    计算车辆未来 30 天预订率（已占用天数 / 30），用于旺季/淡季判断。
    """
    from orders.models import Order
    today = datetime.date.today()
    end = today + datetime.timedelta(days=30)
    occupied_days = 0
    statuses = ['paid', 'renting', 'to_return', 'overdue', 'abnormal']
    orders = Order.objects.filter(
        vehicle=vehicle, status__in=statuses,
        start_date__lte=end, end_date__gte=today,
    )
    for order in orders:
        start = max(order.start_date, today)
        stop = min(order.end_date, end)
        occupied_days += (stop - start).days + 1
    rate = occupied_days / 30.0
    return min(rate, 1.0)


def get_day_detail(vehicle, day, start_date, end_date, rules, booking_rate):
    """
    计算单日的动态定价系数与命中规则说明。
    """
    factor = Decimal('0')
    notes = []
    # 节假日 / 周末上浮
    if is_holiday(day):
        factor += rules['holiday']
        notes.append('节假日上浮')
    elif day.weekday() >= 5:
        factor += rules['weekend']
        notes.append('周末上浮')
    # 旺季 / 淡季调价
    if booking_rate > Decimal('0.8'):
        factor += rules['peak']
        notes.append('旺季调价')
    elif booking_rate < Decimal('0.3'):
        factor += rules['off_season']
        notes.append('淡季促销')
    # 早鸟 / 长租优惠（整段租期统一适用）
    if (start_date - datetime.date.today()).days >= 7:
        factor += rules['early_bird']
        notes.append('早鸟优惠')
    if (end_date - start_date).days + 1 >= 7:
        factor += rules['long_rent']
        notes.append('长租优惠')
    return factor, notes


def calculate_price(vehicle, start_date, end_date):
    """
    按价格计算链计算租金：逐日动态租金累加。

    返回包含每日明细、原价总额、动态总额的字典。
    """
    rules = get_active_rules()
    booking_rate = get_booking_rate(vehicle)
    base_daily = Decimal(str(vehicle.daily_rent))
    items = []
    base_total = Decimal('0')
    dynamic_total = Decimal('0')
    day = start_date
    while day <= end_date:
        factor, notes = get_day_detail(vehicle, day, start_date, end_date, rules, booking_rate)
        dynamic_daily = (base_daily * (Decimal('1') + factor)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        items.append({
            'date': day,
            'base': base_daily,
            'factor': factor,
            'dynamic': dynamic_daily,
            'notes': notes,
        })
        base_total += base_daily
        dynamic_total += dynamic_daily
        day += datetime.timedelta(days=1)
    return {
        'days': len(items),
        'base_total': base_total,
        'dynamic_total': dynamic_total,
        'items': items,
    }


def get_deposit(vehicle, price_info=None):
    """
    计算押金：押金 = 基础日租金 × 押金倍数（默认 1 天租金）。
    """
    multiple = Decimal(str(get_setting('deposit_multiple')))
    deposit = Decimal(str(vehicle.daily_rent)) * multiple
    return deposit.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_fine(vehicle, overdue_days, return_date):
    """
    计算违约金：超时天数 × 当日动态日租金 × 违约金倍数（默认 1.5）。
    """
    rules = get_active_rules()
    booking_rate = get_booking_rate(vehicle)
    factor, _ = get_day_detail(vehicle, return_date, return_date, return_date, rules, booking_rate)
    daily = (Decimal(str(vehicle.daily_rent)) * (Decimal('1') + factor)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    multiple = Decimal(str(get_setting('fine_multiple')))
    fine = daily * Decimal(overdue_days) * multiple
    return fine.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

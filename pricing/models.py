"""
动态定价数据模型。

- PriceRule：定价规则配置（节假日上浮、旺季/淡季、早鸟、长租等）
- SystemSetting：平台基础参数（押金倍数、违约金倍数等）
"""
from django.db import models


class PriceRule(models.Model):
    """定价规则：管理员可配置调整系数与启用状态。"""
    RULE_TYPES = [
        ('holiday', '节假日上浮'),
        ('weekend', '周末上浮'),
        ('peak', '旺季调价'),
        ('off_season', '淡季促销'),
        ('early_bird', '早鸟优惠'),
        ('long_rent', '长租优惠'),
    ]
    rule_type = models.CharField('规则类型', max_length=30, choices=RULE_TYPES, unique=True)
    name = models.CharField('规则名称', max_length=50)
    factor = models.DecimalField(
        '调整系数', max_digits=5, decimal_places=2,
        help_text='上浮为正数（如 0.30 表示 +30%），优惠为负数（如 -0.15 表示 -15%）',
    )
    enabled = models.BooleanField('是否启用', default=True)
    description = models.CharField('规则说明', max_length=200, blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 't_price_rule'
        verbose_name = '定价规则'

    def __str__(self):
        return self.name


class SystemSetting(models.Model):
    """系统基础参数：押金倍数、违约金倍数、待支付订单自动取消时限等。"""
    key = models.CharField('参数键', max_length=50, unique=True)
    value = models.CharField('参数值', max_length=100)
    description = models.CharField('参数说明', max_length=200, blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 't_system_setting'
        verbose_name = '系统设置'

    def __str__(self):
        return f'{self.key}={self.value}'

    @classmethod
    def get(cls, key, default=None):
        """读取参数值，不存在时返回默认值。"""
        obj = cls.objects.filter(key=key).first()
        return obj.value if obj else default

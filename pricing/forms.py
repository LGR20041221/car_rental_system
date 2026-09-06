"""
定价应用表单：定价规则配置、系统参数配置。
"""
from decimal import Decimal

from django import forms

from pricing.models import PriceRule, SystemSetting


class PriceRuleForm(forms.ModelForm):
    """定价规则表单：系数可正可负，限制范围 -0.5 ~ 0.5。"""
    class Meta:
        model = PriceRule
        fields = ['rule_type', 'name', 'factor', 'enabled', 'description']
        labels = {
            'rule_type': '规则类型', 'name': '规则名称',
            'factor': '调整系数', 'enabled': '是否启用', 'description': '规则说明',
        }

    def clean_factor(self):
        """调整系数限制在 -0.5 ~ 0.5 之间。"""
        factor = self.cleaned_data['factor']
        if factor < -Decimal('0.5') or factor > Decimal('0.5'):
            raise forms.ValidationError('调整系数需在 -0.5 ~ 0.5 之间')
        return factor


class SystemSettingForm(forms.ModelForm):
    """系统参数表单。"""
    class Meta:
        model = SystemSetting
        fields = ['key', 'value', 'description']
        labels = {'key': '参数键', 'value': '参数值', 'description': '参数说明'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 参数键为系统约定，不允许编辑
        self.fields['key'].disabled = True

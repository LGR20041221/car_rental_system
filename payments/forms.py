"""
支付应用表单：优惠券创建/编辑。
"""
from django import forms

from payments.models import Coupon


class CouponForm(forms.ModelForm):
    """优惠券表单：满减券或折扣券。"""
    class Meta:
        model = Coupon
        fields = [
            'name', 'discount_type', 'value', 'min_amount',
            'total_count', 'start_date', 'end_date', 'is_active',
        ]
        labels = {
            'name': '优惠券名称', 'discount_type': '优惠类型', 'value': '面额/折扣',
            'min_amount': '使用门槛(元)', 'total_count': '发行总量',
            'start_date': '生效日期', 'end_date': '失效日期', 'is_active': '是否启用',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_value(self):
        """满减券面额必须为正数；折扣券折扣需在 0.1 ~ 10 之间。"""
        value = self.cleaned_data['value']
        discount_type = self.cleaned_data.get('discount_type')
        if value <= 0:
            raise forms.ValidationError('面额/折扣必须大于 0')
        if discount_type == 'discount' and (value <= 0.1 or value >= 10):
            raise forms.ValidationError('折扣需在 0.1 ~ 10 之间（如 8.5 表示 85 折）')
        return value

    def clean(self):
        """失效日期不能早于生效日期。"""
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', '失效日期不能早于生效日期')
        return cleaned

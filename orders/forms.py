"""
订单应用表单：创建订单、续租申请。
"""
import datetime

from django import forms


class OrderCreateForm(forms.Form):
    """创建订单表单：车辆、租期、取还车地点与可选优惠券。"""
    vehicle_id = forms.IntegerField(label='车辆', widget=forms.HiddenInput)
    start_date = forms.DateField(label='取车日期', widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='还车日期', widget=forms.DateInput(attrs={'type': 'date'}))
    pickup_location = forms.CharField(
        label='取车地点', max_length=100,
        error_messages={'required': '请填写取车地点'},
    )
    return_location = forms.CharField(
        label='还车地点', max_length=100,
        error_messages={'required': '请填写还车地点'},
    )
    coupon_id = forms.IntegerField(label='优惠券', required=False)

    def clean_start_date(self):
        """取车日期不能早于今天。"""
        start = self.cleaned_data['start_date']
        if start < datetime.date.today():
            raise forms.ValidationError('取车日期不能早于今天')
        return start

    def clean(self):
        """还车日期不能早于取车日期，租期不超过 30 天。"""
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end:
            if end < start:
                self.add_error('end_date', '还车日期不能早于取车日期')
            elif (end - start).days + 1 > 30:
                self.add_error('end_date', '单次租赁最长 30 天')
        return cleaned


class ExtendForm(forms.Form):
    """续租申请表单：填写续租目标还车日期。"""
    extend_to_date = forms.DateField(
        label='续租至', widget=forms.DateInput(attrs={'type': 'date'}),
        error_messages={'required': '请选择续租目标还车日期'},
    )

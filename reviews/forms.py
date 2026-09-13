"""
评价应用表单：提交评价。
"""
from django import forms

from reviews.models import Review

RATING_CHOICES = [(i, f'{i} 星') for i in range(1, 6)]


class ReviewForm(forms.ModelForm):
    """评价表单：1-5 星评分与文字评价。"""
    rating = forms.ChoiceField(
        label='评分', choices=RATING_CHOICES, widget=forms.RadioSelect,
        error_messages={'required': '请选择评分'},
    )

    content = forms.CharField(
        label='评价内容',
        error_messages={'required': '评价内容不能为空'},
        widget=forms.Textarea(attrs={
            'rows': 4, 'placeholder': '分享您的租车体验…', 'required': 'required',
        }),
    )

    class Meta:
        model = Review
        fields = ['rating', 'content']
        labels = {'content': '评价内容'}

    def clean_rating(self):
        """评分转换为整数。"""
        return int(self.cleaned_data['rating'])

    def clean_content(self):
        """评价内容去除首尾空白后不能为空（防止只输入空格绕过必填）。"""
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError('评价内容不能为空')
        return content

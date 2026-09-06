"""
消息通知应用表单：系统公告发布/编辑。
"""
from django import forms

from notifications.models import Announcement


class AnnouncementForm(forms.ModelForm):
    """系统公告表单。"""
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'is_top', 'is_active']
        labels = {
            'title': '公告标题', 'content': '公告内容',
            'is_top': '是否置顶', 'is_active': '是否发布',
        }
        widgets = {'content': forms.Textarea(attrs={'rows': 6})}

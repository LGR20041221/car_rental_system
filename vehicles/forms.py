"""
车辆应用表单：车辆新增/编辑、品牌维护、分类维护、前台筛选。
"""
from django import forms

from vehicles.models import Brand, Category, Vehicle


class VehicleForm(forms.ModelForm):
    """车辆信息录入/编辑表单：品牌从品牌表选择。"""
    class Meta:
        model = Vehicle
        fields = [
            'brand', 'category', 'model_name', 'plate_number', 'color',
            'seats', 'displacement', 'fuel_type', 'daily_rent',
            'status', 'cover_image', 'description',
        ]
        labels = {
            'brand': '品牌', 'category': '分类', 'model_name': '型号',
            'plate_number': '车牌号', 'color': '颜色', 'seats': '座位数',
            'displacement': '排量', 'fuel_type': '燃油类型',
            'daily_rent': '日租金(元)', 'status': '状态',
            'cover_image': '封面图', 'description': '车辆描述',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        """设置日租金校验的最小值。"""
        super().__init__(*args, **kwargs)
        self.fields['daily_rent'].min_value = 0
        self.fields['seats'].min_value = 1


class BrandForm(forms.ModelForm):
    """品牌新增/编辑表单。"""
    class Meta:
        model = Brand
        fields = ['name', 'logo', 'description']
        labels = {'name': '品牌名称', 'logo': '品牌LOGO', 'description': '品牌简介'}
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class CategoryForm(forms.ModelForm):
    """车辆分类新增/编辑表单。"""
    class Meta:
        model = Category
        fields = ['name', 'description']
        labels = {'name': '分类名称', 'description': '分类描述'}


class VehicleSearchForm(forms.Form):
    """前台车辆筛选表单：分类、品牌、价格区间、关键词、燃油类型、排序。"""
    keyword = forms.CharField(required=False, max_length=50)
    category = forms.IntegerField(required=False)
    brand = forms.IntegerField(required=False)
    fuel_type = forms.CharField(required=False, max_length=20)
    price_min = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    price_max = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    sort = forms.CharField(required=False, max_length=20)

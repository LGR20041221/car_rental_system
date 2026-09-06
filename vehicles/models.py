"""
车辆数据模型。

- Brand：品牌字典（车辆录入时从品牌表选择）
- Category：车辆分类（轿车/SUV/MPV）
- Vehicle：车辆主体信息
- VehicleImage：车辆多角度图片
"""
from django.db import models


class Brand(models.Model):
    """汽车品牌：名称唯一，维护品牌 LOGO 与简介。"""
    name = models.CharField('品牌名称', max_length=50, unique=True)
    logo = models.ImageField('品牌LOGO', upload_to='brands/', null=True, blank=True)
    description = models.TextField('品牌简介', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 't_brand'
        verbose_name = '品牌'

    def __str__(self):
        return self.name


class Category(models.Model):
    """车辆分类：轿车 / SUV / MPV。"""
    name = models.CharField('分类名称', max_length=50, unique=True)
    description = models.CharField('分类描述', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 't_category'
        verbose_name = '车辆分类'

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    """租赁车辆：包含基本信息、日租金、状态与所属品牌/分类。"""
    STATUS_CHOICES = [
        ('available', '可租'),
        ('renting', '租赁中'),
        ('off_shelf', '已下架'),
    ]
    FUEL_CHOICES = [
        ('gasoline', '汽油'),
        ('diesel', '柴油'),
        ('electric', '纯电动'),
        ('hybrid', '混动'),
    ]
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='vehicles', verbose_name='品牌'
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='vehicles', verbose_name='分类'
    )
    model_name = models.CharField('型号', max_length=100)
    plate_number = models.CharField('车牌号', max_length=20, unique=True)
    color = models.CharField('颜色', max_length=20, default='白色')
    seats = models.PositiveSmallIntegerField('座位数', default=5)
    displacement = models.CharField('排量', max_length=20, blank=True, default='')
    fuel_type = models.CharField('燃油类型', max_length=20, choices=FUEL_CHOICES, default='gasoline')
    daily_rent = models.DecimalField('日租金(元)', max_digits=10, decimal_places=2)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='available')
    cover_image = models.ImageField('封面图', upload_to='vehicles/', null=True, blank=True)
    description = models.TextField('车辆描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 't_vehicle'
        verbose_name = '车辆'

    def __str__(self):
        return f'{self.brand.name} {self.model_name}'

    @property
    def status_text(self):
        """状态中文文案。"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def fuel_text(self):
        """燃油类型中文文案。"""
        return dict(self.FUEL_CHOICES).get(self.fuel_type, self.fuel_type)


class VehicleImage(models.Model):
    """车辆多角度图片：通过 sort_order 控制展示顺序。"""
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name='images', verbose_name='车辆'
    )
    image = models.ImageField('图片', upload_to='vehicles/')
    sort_order = models.PositiveIntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 't_vehicle_image'
        verbose_name = '车辆图片'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.vehicle.model_name} 图片'

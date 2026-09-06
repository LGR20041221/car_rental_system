"""
用户应用表单：统一管理字段校验与业务规则。

包含注册、登录、密码找回、个人信息修改、修改密码、管理员维护用户等表单。
"""
from django import forms
from django.contrib.auth.hashers import check_password
from django.core.validators import RegexValidator

from users.models import User
from users.services import verify_code

# 手机号格式校验
_phone_validator = RegexValidator(
    regex=r'^1[3-9]\d{9}$',
    message='请输入正确的 11 位手机号',
)


class RegisterForm(forms.Form):
    """用户注册表单：用户名+手机号+邮箱+验证码+密码。"""
    username = forms.CharField(
        label='用户名', max_length=30,
        error_messages={'required': '请输入用户名'},
    )
    phone = forms.CharField(
        label='手机号', validators=[_phone_validator],
        error_messages={'required': '请输入手机号'},
    )
    email = forms.EmailField(
        label='邮箱',
        error_messages={'required': '请输入邮箱', 'invalid': '邮箱格式不正确'},
    )
    code = forms.CharField(
        label='验证码', max_length=6,
        error_messages={'required': '请输入验证码'},
    )
    password = forms.CharField(
        label='密码', min_length=6, max_length=32,
        widget=forms.PasswordInput,
        error_messages={'required': '请输入密码', 'min_length': '密码至少 6 位'},
    )
    confirm_password = forms.CharField(
        label='确认密码', widget=forms.PasswordInput,
        error_messages={'required': '请再次输入密码'},
    )

    def clean_username(self):
        """用户名唯一性校验。"""
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('该用户名已被注册')
        return username

    def clean_phone(self):
        """手机号唯一性校验。"""
        phone = self.cleaned_data.get('phone', '').strip()
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError('该手机号已被注册')
        return phone

    def clean_email(self):
        """邮箱唯一性校验。"""
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已被注册')
        return email

    def clean(self):
        """
        跨字段校验：验证码核验 + 两次密码一致性。
        验证码需在邮箱与验证码字段均清洗后校验。
        """
        cleaned = super().clean()
        pwd = cleaned.get('password')
        confirm = cleaned.get('confirm_password')
        if pwd and confirm and pwd != confirm:
            self.add_error('confirm_password', '两次输入的密码不一致')
        email = cleaned.get('email')
        code = cleaned.get('code')
        if email and code and not verify_code(email, code):
            self.add_error('code', '验证码错误或已过期')
        return cleaned


class LoginForm(forms.Form):
    """登录表单：账号 + 密码。"""
    username = forms.CharField(label='账号', error_messages={'required': '请输入账号'})
    password = forms.CharField(
        label='密码', widget=forms.PasswordInput,
        error_messages={'required': '请输入密码'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def clean(self):
        """校验账号密码并缓存查到的用户对象。"""
        cleaned = super().clean()
        username = cleaned.get('username', '').strip()
        password = cleaned.get('password', '')
        user = User.objects.filter(username=username).first()
        if user is None:
            raise forms.ValidationError('账号不存在')
        if not user.is_active:
            raise forms.ValidationError('该账号已被禁用，请联系管理员')
        if not check_password(password, user.password):
            raise forms.ValidationError('密码错误')
        self.user = user
        return cleaned


class ForgotPasswordForm(forms.Form):
    """密码找回表单：邮箱 + 验证码 + 新密码。"""
    email = forms.EmailField(label='邮箱', error_messages={'required': '请输入邮箱'})
    code = forms.CharField(label='验证码', max_length=6, error_messages={'required': '请输入验证码'})
    new_password = forms.CharField(
        label='新密码', min_length=6, max_length=32, widget=forms.PasswordInput,
        error_messages={'required': '请输入新密码', 'min_length': '密码至少 6 位'},
    )
    confirm_password = forms.CharField(
        label='确认新密码', widget=forms.PasswordInput,
        error_messages={'required': '请再次输入新密码'},
    )

    def clean_email(self):
        """找回密码的邮箱必须已注册。"""
        email = self.cleaned_data.get('email', '').strip()
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱未注册')
        return email

    def clean_code(self):
        """校验邮箱验证码。"""
        email = self.cleaned_data.get('email', '')
        code = self.cleaned_data.get('code', '')
        if not verify_code(email, code):
            raise forms.ValidationError('验证码错误或已过期')
        return code

    def clean(self):
        """两次新密码一致性校验。"""
        cleaned = super().clean()
        pwd = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if pwd and confirm and pwd != confirm:
            self.add_error('confirm_password', '两次输入的新密码不一致')
        return cleaned


class ProfileForm(forms.ModelForm):
    """个人信息表单：修改用户名、手机号、邮箱（需校验唯一性，排除自己）。"""
    class Meta:
        model = User
        fields = ['username', 'phone', 'email']
        labels = {'username': '用户名', 'phone': '手机号', 'email': '邮箱'}
        error_messages = {'username': {'required': '请输入用户名'}}

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def clean_username(self):
        """用户名唯一性校验（排除当前用户）。"""
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('该用户名已被其他用户使用')
        return username

    def clean_phone(self):
        """手机号唯一性校验（排除当前用户）。"""
        phone = self.cleaned_data.get('phone', '').strip()
        if User.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('该手机号已被其他用户使用')
        return phone

    def clean_email(self):
        """邮箱唯一性校验（排除当前用户）。"""
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('该邮箱已被其他用户使用')
        return email


class ChangePasswordForm(forms.Form):
    """修改密码表单。"""
    old_password = forms.CharField(
        label='原密码', widget=forms.PasswordInput,
        error_messages={'required': '请输入原密码'},
    )
    new_password = forms.CharField(
        label='新密码', min_length=6, max_length=32, widget=forms.PasswordInput,
        error_messages={'required': '请输入新密码', 'min_length': '密码至少 6 位'},
    )
    confirm_password = forms.CharField(
        label='确认新密码', widget=forms.PasswordInput,
        error_messages={'required': '请再次输入新密码'},
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        """校验原密码是否正确。"""
        old = self.cleaned_data.get('old_password', '')
        if not check_password(old, self.user.password):
            raise forms.ValidationError('原密码不正确')
        return old

    def clean(self):
        """两次新密码一致性校验。"""
        cleaned = super().clean()
        pwd = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if pwd and confirm and pwd != confirm:
            self.add_error('confirm_password', '两次输入的新密码不一致')
        return cleaned


class SendCodeForm(forms.Form):
    """发送验证码表单：仅校验邮箱格式。"""
    email = forms.EmailField(error_messages={'required': '请输入邮箱', 'invalid': '邮箱格式不正确'})
    purpose = forms.CharField(widget=forms.HiddenInput, required=False)


class AdminUserForm(forms.ModelForm):
    """管理员维护用户表单：用户名、手机号、邮箱、启用状态、管理员角色。"""
    password = forms.CharField(
        label='密码', min_length=6, max_length=32, required=False,
        widget=forms.PasswordInput,
        help_text='留空表示不修改密码',
    )

    class Meta:
        model = User
        fields = ['username', 'phone', 'email', 'is_active', 'is_admin']
        labels = {
            'username': '用户名',
            'phone': '手机号',
            'email': '邮箱',
            'is_active': '是否启用',
            'is_admin': '是否管理员',
        }

    def clean_username(self):
        """用户名唯一性校验（排除自己）。"""
        username = self.cleaned_data.get('username', '').strip()
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('该用户名已被使用')
        return username

    def clean_phone(self):
        """手机号唯一性校验（排除自己）。"""
        phone = self.cleaned_data.get('phone', '').strip()
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('该手机号已被使用')
        return phone

    def clean_email(self):
        """邮箱唯一性校验（排除自己）。"""
        email = self.cleaned_data.get('email', '').strip()
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('该邮箱已被使用')
        return email

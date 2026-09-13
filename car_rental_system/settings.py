"""
Django 项目全局配置。

包含数据库、认证、缓存、邮件、静态资源等基础配置。
数据库统一使用 MySQL（库名：car_rental_system）。
"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# ========== 安全配置（开发阶段） ==========
SECRET_KEY = 'django-insecure-car-rental-smart-system-2026'
DEBUG = True
ALLOWED_HOSTS = ['*']

# ========== 应用注册 ==========
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 业务应用
    'users',         # 用户管理
    'vehicles',      # 车辆管理
    'pricing',       # 动态定价
    'orders',        # 租赁订单
    'payments',      # 支付与费用
    'reviews',       # 评价
    'favorites',     # 收藏
    'notifications', # 消息通知
    'dashboard',     # 运营数据可视化
]

# ========== 中间件 ==========
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Django 标准认证中间件：从 session 恢复 request.user
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'car_rental_system.urls'

# ========== 模板配置 ==========
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                # Django 标准认证上下文：向模板注入 user 变量
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'car_rental_system.wsgi.application'

# ========== 数据库（MySQL 8.0） ==========
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'car_rental_system',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

# 密码存储：使用 Django 默认 PBKDF2PasswordHasher（set_password 即走 PBKDF2）

# 自定义用户模型
AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
]

# ========== 国际化 ==========
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
# 数据库存本地时间（Asia/Shanghai），使 created_at__date 等日期查询直接准确
USE_TZ = False

# ========== 静态资源 ==========
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ========== 媒体文件（车辆图片、头像等上传） ==========
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========== 缓存（开发环境本地内存缓存，生产可切换 Redis） ==========
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
# 生产环境可切换 Redis：
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#     }
# }

# ========== 邮件（开发阶段终端输出验证码，生产切换 SMTP） ==========
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = 'car_rental@example.com'
# 邮件发件人显示名称
EMAIL_FROM_NAME = '汽车租赁智能管理系统'

# ========== 登录保护 ==========
LOGIN_URL = '/login/'

# ========== 业务参数 ==========
# 验证码有效期（秒）
VERIFY_CODE_TTL = 300
# 验证码发送间隔（秒）
VERIFY_CODE_SEND_INTERVAL = 60

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

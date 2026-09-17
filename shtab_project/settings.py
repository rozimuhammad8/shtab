"""
Django settings for shtab_project.

Andijon tumani "Aholi bandligi va kambag'allikka barham berish" shtabi
ma'lumotlar bazasi uchun sodda, ishga tushirishga tayyor konfiguratsiya.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# XAVFSIZLIK: production'ga chiqarishdan oldin bu qiymatni o'zgartiring
# va uni environment variable orqali bering (masalan: os.environ["DJANGO_SECRET_KEY"]).
SECRET_KEY = 'django-insecure-CHANGE-ME-before-deploying-to-production'

# Ishlab chiqish (development) uchun True. Production'da FALSE qiling!
DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'registry',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'shtab_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'shtab_project.wsgi.application'
ASGI_APPLICATION = 'shtab_project.asgi.application'

# Ma'lumotlar bazasi: sinov/kichik joylashtirishlar uchun SQLite.
# Katta hajmda (~16 ming yozuv) ishlatish uchun PostgreSQL tavsiya etiladi -
# quyida misol izohli holda keltirilgan.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PostgreSQL bilan ishlash uchun (tavsiya etiladi), yuqoridagi bloqni
# o'chirib, quyidagini yoqing va psycopg2-binary'ni requirements.txt'ga qo'shing:
#
# import os
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', 'shtab_db'),
#         'USER': os.environ.get('DB_USER', 'shtab_user'),
#         'PASSWORD': os.environ.get('DB_PASSWORD', ''),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'registry' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Ro'yxat sahifalarida bir sahifada nechta yozuv ko'rsatilishi
PAGE_SIZE = 25


from pathlib import Path
import os
from dotenv import load_dotenv
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv()

# DB Password
MY_DB_PASSWORD = os.environ['MY_DB_PASSWORD']
# MY_DB_PASSWORD = os.environ.get('MY_DB_PASSWORD')

# AWS credentials
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
AWS_S3_REGION_NAME = os.environ['AWS_S3_REGION_NAME']

# Google auth credentials
SOCIAL_GOOGLE_CLIENT_ID = os.environ['SOCIAL_GOOGLE_CLIENT_ID']
SOCIAL_GOOGLE_CLIENT_SECRET = os.environ['SOCIAL_GOOGLE_CLIENT_SECRET']

# Stripe credentials
STRIPE_PUBLIC_KEY = os.environ['STRIPE_PUBLIC_KEY']
STRIPE_SECRET_KEY = os.environ['STRIPE_SECRET_KEY']
STRIPE_WEBHOOK_SECRET = os.environ['STRIPE_WEBHOOK_SECRET']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'nanntheint.dev@gmail.com'
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
DEFAULT_FROM_EMAIL = 'nanntheint.dev@gmail.com'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-3_vyq10@%=g2*pi0^5s_tdu6tfs5a!dlensj*xewnrmh@h_v2f'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# settings.py
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_ADDRESSING_STYLE = 'virtual'
AWS_QUERYSTRING_EXPIRE = 300  # 5 minutes

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

ALLOWED_HOSTS = ['ecommerce-production-97c1.up.railway.app', 'https://ecommerce-production-97c1.up.railway.app', '127.0.0.1', 'localhost', ' dc66-80-99-40-134.ngrok-free.app']
CSRF_TRUSTED_ORIGINS = ['https://ecommerce-production-97c1.up.railway.app', ' https://dc66-80-99-40-134.ngrok-free.app']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'store',
    'cart',
    'payment',
    'whitenoise.runserver_nostatic',
    'paypal.standard.ipn',
    'storages',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',  
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1  # Ensure SITE_ID matches your sites configuration

LOGIN_REDIRECT_URL = '/'  # Redirect after login
LOGOUT_REDIRECT_URL = '/'  # Redirect after logout

# AllAuth configuration
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True

# Social account settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'APP': {
            'client_id': SOCIAL_GOOGLE_CLIENT_ID,
            'secret': SOCIAL_GOOGLE_CLIENT_SECRET,
            'key': 'AIzaSyA-UOoz_PwRhYgo7fQgGH8wQ6se3cI5hlM'
        }
    }
}

ROOT_URLCONF = 'ecommerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processor.category_list',
                'cart.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'railway',
        'USER': 'postgres',
        'PASSWORD': MY_DB_PASSWORD,
        'HOST': 'autorack.proxy.rlwy.net',
        'PORT': '19675',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# White noise static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files storage
# S3 Static and Media Settings
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_CUSTOM_DOMAIN = 'euphoria-media.s3.amazonaws.com'

if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

else:
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
    STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "BUCKET_NAME": 'euphoria-media',
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "videos": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "BUCKET_NAME": AWS_STORAGE_BUCKET_NAME,
    },
}
    

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# add paypal settings
PAYPAL_TEST = True

PAYPAL_RECEIVER_EMAIL = 'euphoria@business.com' # business sandbox account

# settings.py

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
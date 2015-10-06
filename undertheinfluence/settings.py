"""
Django settings for undertheinfluence project.

Generated by 'django-admin startproject' using Django 1.8.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from os.path import dirname, exists, join, realpath
import yaml

BASE_DIR = realpath(dirname(dirname(__file__)))
PROJECT_DIR = join(BASE_DIR, 'undertheinfluence')

configuration_file = join(
    BASE_DIR, 'conf', 'general.yml'
)

with open(configuration_file) as f:
    conf = yaml.load(f)

ALLOWED_HOSTS = conf.get('ALLOWED_HOSTS')

BASE_URL = conf.get('BASE_URL')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/


# Application definition

INSTALLED_APPS = [
    'cms',
    'search',
    'datafetch',
    'appc_redirect',
    'api',

    'bootstrap_admin',
    'rest_framework',
    'djangobower',

    'wagtail.wagtailforms',
    'wagtail.wagtailredirects',
    'wagtail.wagtailembeds',
    'wagtail.wagtailsites',
    'wagtail.wagtailusers',
    'wagtail.wagtailsnippets',
    'wagtail.wagtaildocs',
    'wagtail.wagtailimages',
    'wagtail.wagtailsearch',
    'wagtail.wagtailadmin',
    'wagtail.wagtailcore',

    'modelcluster',
    'compressor',
    'taggit',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'wagtail.wagtailcore.middleware.SiteMiddleware',
    'wagtail.wagtailredirects.middleware.RedirectMiddleware',
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = conf['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(conf.get('STAGING')))

ROOT_URLCONF = 'undertheinfluence.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(PROJECT_DIR, 'templates'),
        ],
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

BOOTSTRAP_ADMIN_SIDEBAR_MENU = True

WSGI_APPLICATION = 'undertheinfluence.wsgi.application'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# The email address that will be displayed on the site as the contact
# email for all support requests, and so on:
SUPPORT_EMAIL = conf.get('SUPPORT_EMAIL')

# The From = address for error emails
SERVER_EMAIL = conf.get('SERVER_EMAIL')

# The From = address for all emails except error emails
DEFAULT_FROM_EMAIL = conf.get('DEFAULT_FROM_EMAIL')

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

if conf.get('DATABASE_SYSTEM') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql_psycopg2',
            'NAME':     conf.get('UTI_DB_NAME'),
            'USER':     conf.get('UTI_DB_USER'),
            'PASSWORD': conf.get('UTI_DB_PASS'),
            'HOST':     conf.get('UTI_DB_HOST'),
            'PORT':     conf.get('UTI_DB_PORT'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Europe/London'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
    'djangobower.finders.BowerFinder',
)

STATICFILES_DIRS = (
    join(PROJECT_DIR, 'static'),
)

STATIC_ROOT = join(BASE_DIR, 'static')
STATIC_URL = '/static/'

MEDIA_ROOT = join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Django-bower settings
BOWER_COMPONENTS_ROOT = BASE_DIR

BOWER_INSTALLED_APPS = (
    'jquery#2.1.1',
    'bootstrap',
    'bootstrap-material-design',
    'bootstrap-table',
    'moment',
)

# Wagtail settings

WAGTAIL_SITE_NAME = "UnderTheInfluence"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "SAMEORIGIN"  # for the wagtail toolbar
CSRF_COOKIE_HTTPONLY = True

# Django REST Framework settings
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
}

# TheyWorkForYou API key
TWFY_API_KEY = conf.get('TWFY_API_KEY')

# Email addresses that error emails are sent to when DEBUG = False
ADMINS = conf['ADMINS']

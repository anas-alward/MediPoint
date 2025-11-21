# settings/production.py

from .base import * 
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Allowed hosts for production
ALLOWED_HOSTS = [env('ALLOWED_HOSTS')]

# Database (use PostgreSQL or another production-ready database)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
    }
}


CORS_ALLOWED_ORIGINS = [
    env('CORS_ALLOWED_ORIGINS'),
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


# Static files (use Whitenoise or a CDN for production)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = "/static/"


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
USE_X_FORWARDED_HOST = True


EMAIL_BACKEND = "anymail.backends.mailjet.EmailBackend"  # or sendgrid.EmailBackend, or...
DEFAULT_FROM_EMAIL = "medipoint@decodaai.com"  # if you don't already have this in settings
ANYMAIL = {
    "MAILJET_API_KEY": env("EMAIL_API_KEY"),
    "MAILJET_SECRET_KEY": env("EMAIL_SECRET_KEY"),  
}


# Celery settings
CELERY_BROKER_URL = env('CELERY_BROKER_URL')  
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')   
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Backup settings
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': env('DBBACKUP_STORAGE_LOCATION')}

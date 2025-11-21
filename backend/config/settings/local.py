# settings/local.py
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allowed hosts for local development
# settings.py

ALLOWED_HOSTS = ['164.92.161.163', 'localhost', '127.0.0.1']

# Database (use SQLite or another local database)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
    }
}

CORS_ALLOWED_ORIGINS = [
    "http://164.92.161.163:4174",
    "http://164.92.161.163:4173",  # Example: Allow requests from a React app running on port 3000
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Static files (optional for local development)
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "email" 
EMAIL_PORT = 1025
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

DEFAULT_FROM_EMAIL = "medipoint@decodaai.com"  # if you don't already have this in settings

# SERVER_EMAIL = ""  # ditto (default from-email for Django errors)


# Celery settings for local development
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'

DBBACKUP_STORAGE_OPTIONS = {'location': '/home/MediPoint/medipoint_db/'}

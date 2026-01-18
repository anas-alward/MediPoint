from django.apps import AppConfig


class DoctorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.doctors"

    def ready(self):
        # Import signals to ensure they are registered
        from . import signals  # noqa: F401

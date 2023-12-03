from django.apps import AppConfig


class DjangoExtrasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_extras"

    def ready(self):
        # Ensure signals get registered
        from .. import signals  # noqa

from django.apps import AppConfig


class TrainsConfig(AppConfig):
    name = 'trains'

    def ready(self):
        # Import the module so its @receiver hooks register when the app starts.
        from . import signals  # noqa: F401

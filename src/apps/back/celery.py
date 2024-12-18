import os

from celery import Celery

from . import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.back.settings")


app = Celery(
    "back",
    broker_connection_retry_on_startup=True,
)

app.conf.enable_utc = False
app.conf.update(timezone="Europe/Moscow")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.update(
    result_extended=True,
)

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
app.conf.task_routes = settings.task_routes
app.conf.beat_schedule = settings.task_groups[os.getenv("TASK", "main")]

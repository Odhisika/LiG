# Scheduler has no models of its own. Celery Beat's schedule is defined
# in config/settings/base.py (CELERY_BEAT_SCHEDULE) and synced into
# django_celery_beat's own tables (manageable via /admin/) by
# DatabaseScheduler on startup.

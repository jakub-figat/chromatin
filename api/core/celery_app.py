"""Celery application configuration"""

from celery import Celery

from core.config import settings

celery_app = Celery(
    "chromatin",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["jobs.tasks"],  # Auto-discover tasks from jobs.tasks module
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time for CPU-bound work
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
    task_acks_late=True,  # Acknowledge task after completion (for reliability)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies
    result_expires=86400,  # Results expire after 24 hours
)

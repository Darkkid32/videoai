from celery import Celery
from core.config import settings

celery_app = Celery(
    "videoai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # GPU stability — reload after each task to prevent VRAM leaks
    worker_max_tasks_per_child=1,

    # One GPU job at a time per worker process
    # Scale by launching multiple workers on multi-GPU machines
    worker_concurrency=1,

    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Timeouts
    task_soft_time_limit=settings.JOB_TIMEOUT,
    task_time_limit=settings.JOB_TIMEOUT + 120,

    # Priority queue support (0=highest, 9=lowest)
    task_queue_max_priority=10,
    task_default_priority=5,
)

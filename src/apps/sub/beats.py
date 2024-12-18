import logging

from celery import shared_task

logger = logging.getLogger("sub")


@shared_task
def test_celery_work() -> None:
    # Пример использования провайдера
    logger.info(f"Hello, world! Settings timezone: asdasd")

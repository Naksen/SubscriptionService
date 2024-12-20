from celery import shared_task
from django.db import transaction

from . import logic, models, exceptions


@shared_task
def make_autopayment(subscription_id: int) -> None:
    """
    Таска для автоматического продления платежа
    """
    import logging

    logger = logging.getLogger("sub")
    logger.info("Выполняем автоплатеж")
    try:
        auto_payment = models.AutoSubscriptionTasks.objects.get(
            subscription__id=subscription_id,
        )
    except models.Subscription.DoesNotExist:
        msg = "Подписка не найдена"
        raise exceptions.SubAppError(msg)

    make_autopayment_periodic_task = auto_payment.task

    logic.PeriodicTasksLogic.remove_periodic_task_with_clocked(
        make_autopayment_periodic_task
    )

    # Выполняем автоплатеж
    if logic.SubscriptionLogic.renew_subscription(subscription_id) is not None:
        # Создаем снова таску на продление подписки
        logger.info("Платеж прошел успешно")
        subscription = models.Subscription.objects.get(pk=subscription_id)
        auto_payment_task = logic.PeriodicTasksLogic.create_auto_payment_task(
            subscription.pk, subscription.plan.days
        )

        auto_payment.subscription = subscription
        auto_payment.task = auto_payment_task
        auto_payment.save()
    else:
        auto_payment.delete()


@shared_task
def stop_subscription(subscription_id: int) -> None:
    """
    Таска для остановки подписки по истечению её времени
    """
    import logging

    logger = logging.getLogger("sub")
    logger.info("Выполняем остановку подписки")
    try:
        auto_payment = models.AutoSubscriptionTasks.objects.get(
            subscription__id=subscription_id,
        )
    except models.AutoSubscriptionTasks.DoesNotExist:
        msg = "Задача на остановку подписки не найдена"
        raise exceptions.SubAppError(msg)

    try:
        subscription = models.Subscription.objects.get(
            pk=subscription_id,
        )
    except models.AutoSubscriptionTasks.DoesNotExist:
        msg = "Подписка не найдена"
        raise exceptions.SubAppError(msg)

    make_autopayment_periodic_task = auto_payment.task

    logic.PeriodicTasksLogic.remove_periodic_task_with_clocked(
        make_autopayment_periodic_task
    )

    auto_payment.delete()

    with transaction.atomic():
        subscription.status = "cancelled"
        subscription.save()

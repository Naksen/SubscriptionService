import os
import uuid
import json
from dotenv import load_dotenv
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from yookassa import Configuration, Payment, Refund
from django_celery_beat.models import PeriodicTask, ClockedSchedule

from .models import Plan, Subscription, Payment as PaymentModel, AutoSubscriptionTasks
from . import sub_types

load_dotenv()


class YooKassaClient:
    def __init__(cls, account_id: str, secret_key: str):
        Configuration.account_id = account_id
        Configuration.secret_key = secret_key

    def create_payment(
        cls,
        amount: float,
        currency: str,
        return_url: str,
        user_id: str,
        save_payment_method: bool = False,
        description: str = None,
    ) -> dict:
        """
        Создает платеж, возвращает URL для оплаты и данные о платеже.

        :param amount: сумма платежа, float
        :param currency: код валюты, например 'RUB'
        :param return_url: URL, на который пользователь вернется после оплаты
        :param user_id: идентификатор пользователя (UUID), сохраняется в metadata
        :param save_payment_method: сохранить ли способ оплаты для автоплатежей
        :param description: описание платежа, можно указать информацию о подписке, или user_id
        :return: словарь с confirmation_url и данными о платеже
        """
        if description is None:
            description = f"Payment for user {user_id}"

        # Создаем платеж
        payment = Payment.create(
            {
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "confirmation": {"type": "redirect", "return_url": return_url},
                "capture": True,
                "description": description,
                "save_payment_method": save_payment_method,
                "metadata": {"user_id": user_id},
            },
            uuid.uuid4(),
        )

        # Возвращаем confirmation_url и информацию о платеже
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": payment.amount,
            "created_at": payment.created_at,
            "confirmation_url": (
                payment.confirmation.confirmation_url if payment.confirmation else None
            ),
            "description": payment.description,
            "metadata": payment.metadata,
        }

    def cancel_payment(cls, payment_id: str) -> dict:
        """
        Отменяет платеж в статусе waiting_for_capture.

        :param payment_id: идентификатор платежа
        :return: данные об отмененном платеже
        """
        response = Payment.cancel(payment_id, uuid.uuid4())
        return {
            "payment_id": response.id,
            "status": response.status,
            "cancellation_details": response.cancellation_details,
        }

    def get_user_payments_history(
        cls, user_id: str, limit: int = 100, **list_params
    ) -> list:
        """
        Возвращает список платежей пользователя, фильтруя их по metadata.user_id.
        Параметр list_params можно использовать для передачи дополнительных параметров в Payment.list(),
        например: from_time, to_time, и т.д.

        Обратите внимание, что в реальности может потребоваться пагинация, т.к. Payment.list() возвращает
        ограниченное число платежей. Тут для простоты берём первые `limit` платежей.

        :param user_id: идентификатор пользователя (UUID)
        :param limit: Максимальное количество возвращаемых платежей
        :param list_params: дополнительные параметры для Payment.list()
        :return: список словарей с информацией о платежах пользователя
        """
        # Получаем список платежей (по умолчанию SDK может вернуть до 100 платежей)
        payments = Payment.list(limit=limit, **list_params)

        user_payments = []
        for p in payments.items:
            if p.metadata and p.metadata.get("user_id") == user_id:
                user_payments.append(
                    {
                        "payment_id": p.id,
                        "status": p.status,
                        "paid": p.paid,
                        "amount": p.amount,
                        "created_at": p.created_at,
                        "description": p.description,
                        "metadata": p.metadata,
                        "payment_method_id": (
                            p.payment_method.id if p.payment_method else None
                        ),
                    }
                )
        return user_payments

    def get_payment(cls, payment_id: str) -> dict:
        """
        Получает информацию о платеже по его идентификатору.

        :param payment_id: идентификатор платежа
        :return: данные о платеже
        """
        payment = Payment.find_one(payment_id)
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": payment.amount,
            "created_at": payment.created_at,
            "description": payment.description,
            "metadata": payment.metadata,
            "payment_method_id": (
                payment.payment_method.id if payment.payment_method else None
            ),
        }

    def charge_autopayment(
        cls,
        user_id: str,
        amount: float,
        currency: str,
        payment_method_id: str,
        description: str,
    ) -> dict:
        """
        Совершает автоплатеж с сохраненным способом оплаты.

        :param amount: сумма списания
        :param currency: валюта
        :param payment_method_id: идентификатор сохраненного способа оплаты (получен из успешного платежа)
        :param description: описание платежа
        :return: данные о созданном платеже
        """
        payment = Payment.create(
            {
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "capture": True,
                "payment_method_id": payment_method_id,
                "description": description,
                "metadata": {"user_id": user_id},
            },
            uuid.uuid4(),
        )

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": payment.amount,
            "created_at": payment.created_at,
            "description": payment.description,
            "metadata": payment.metadata,
        }

    def refund_payment(
        cls, payment_id: str, amount: float, currency: str = "RUB"
    ) -> sub_types.RefundResponse:
        """
        Возврат платежа.

        :param payment_id: идентификатор исходного платежа
        :param amount: сумма возврата
        :param currency: валюта
        :return: данные о возврате
        """
        refund = Refund.create(
            {
                "payment_id": payment_id,
                "amount": {"value": f"{amount:.2f}", "currency": currency},
            },
            uuid.uuid4(),
        )

        return sub_types.RefundResponse(
            refund_id=refund.id,
            status=refund.status,
            payment_id=refund.payment_id,
            amount=(
                sub_types.RefundAmount(
                    value=refund.amount.value, currency=refund.amount.currency
                )
                if refund.amount
                else None
            ),
            created_at=refund.created_at,
            description=refund.description,
        )


class SubscriptionLogic:
    account_id = os.getenv("YOOKASSA_ACCOUNT_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    yoo_client = YooKassaClient(account_id, secret_key)

    @classmethod
    def create_subscription(
        cls, plan_id: int, user_uuid: str, auto_renew: bool, return_url: str
    ) -> str:
        """
        Создать новую подписку и инициировать платеж.

        :param plan_id: ID тарифного плана
        :param user_uuid: UUID пользователя
        :param auto_renew: нужно ли автопродление
        :param return_url: URL, на который пользователь вернется после оплаты
        :return: URL для оплаты через YooKassa
        """
        plan = Plan.objects.get(id=plan_id)
        now = timezone.now()
        end_date = now + timedelta(days=plan.days)

        # Создаем платеж через YooKassa
        payment_data = cls.yoo_client.create_payment(
            amount=float(plan.price),
            currency="RUB",
            return_url=return_url,
            user_id=user_uuid,
            save_payment_method=auto_renew,  # Если автопродление, то сохраняем способ оплаты
            description=f"Subscription for user {user_uuid}",
        )

        # Создаем подписку
        subscription = Subscription.objects.create(
            user_uuid=user_uuid,
            plan=plan,
            status="pending",
            start_date=now,
            end_date=end_date,
            auto_renew=auto_renew,
        )

        # Сохраняем данные платежа в БД
        PaymentModel.objects.create(
            subscription=subscription,
            amount=plan.price,
            user_uuid=user_uuid,
            yk_payment_id=payment_data["payment_id"],
            yk_payment_method_id=payment_data.get("payment_method_id"),
        )

        return payment_data["confirmation_url"]

    @classmethod
    def get_user_subscriptions(cls, user_uuid: str) -> Subscription | None:
        """
        Получить историю подписок по UUID пользователя.

        :param user_uuid: UUID пользователя
        :return: QuerySet или список подписок
        """
        return (
            Subscription.objects.filter(user_uuid=user_uuid)
            .order_by("-created_at")
            .first()
        )

    @classmethod
    def renew_subscription(cls, subscription_id: int) -> PaymentModel | None:
        """
        Продлить подписку через автоплатеж. Предполагается, что у подписки был сохранен способ оплаты.

        :param subscription_id: ID подписки
        :return: данные о созданном автоплатеже
        """
        import logging

        logger = logging.getLogger("sub")

        subscription = Subscription.objects.get(id=subscription_id)
        if subscription.status != "active" or subscription.auto_renew is False:
            raise ValueError("Subscription cannot be renewed automatically")

        # Находим последний платеж с сохраненным способом оплаты (yk_payment_method_id)
        last_payment = (
            PaymentModel.objects.filter(subscription=subscription)
            .exclude(yk_payment_method_id__isnull=True)
            .order_by("-id")
            .first()
        )
        if not last_payment or not last_payment.yk_payment_method_id:
            raise ValueError("No saved payment method found for this subscription")

        logger.info("Подали запрос на автоплатеж")
        # Совершаем автоплатеж
        payment_data = cls.yoo_client.charge_autopayment(
            user_id=str(subscription.user_uuid),
            amount=float(subscription.plan.price),
            currency="RUB",
            payment_method_id=last_payment.yk_payment_method_id,
            description=f"Renew subscription {subscription.pk} for user {subscription.user_uuid}",
        )
        with transaction.atomic():
            # Обновляем дату окончания подписки и ставим статус active
            if payment_data["status"] == "succeeded":
                logger.info(f"Статус платежа: {payment_data.get('status')}")
                subscription.end_date = subscription.end_date + timedelta(
                    days=subscription.plan.days
                )
                logger.info("Переводим подписку в ACTIVE")
                subscription.status = "active"
                subscription.save()

                # Сохраняем новый платеж
                return PaymentModel.objects.create(
                    subscription=subscription,
                    amount=subscription.plan.price,
                    user_uuid=subscription.user_uuid,
                    yk_payment_id=payment_data["payment_id"],
                    yk_payment_method_id=last_payment.yk_payment_method_id,
                )
            else:
                subscription.status = "cancelled"
                subscription.save()

    @classmethod
    def renew_subscription_through_payment(
        cls, plan_id: int, subscription: Subscription, return_url: str, auto_renew: bool
    ) -> str:
        """
        Продлить подписку за счёт обычной оплаты (не автоплатежа).
        Продлить можно только cancelled подписку.
        Возвращает ссылку на оплату. После оплаты можно обновить подписку.

        :param plan_id: ID плана
        :param subscription_id: ID подписки
        :param return_url: URL для возвращения после оплаты
        :param auto_renew: Автоплатеж
        :return: URL для оплаты
        """
        plan = Plan.objects.get(id=plan_id)

        plan = subscription.plan

        # Создаем платеж через YooKassa. Здесь мы не сохраняем payment_method для автоплатежа.
        payment_data = cls.yoo_client.create_payment(
            amount=float(plan.price),
            currency="RUB",
            return_url=return_url,
            user_id=str(subscription.user_uuid),
            save_payment_method=auto_renew,  # здесь можно оставить False, если не хотим сохранять способ оплаты
            description=f"Manual renewal for subscription {subscription.pk} user {subscription.user_uuid}",
        )

        # Сохраняем данные платежа в БД
        PaymentModel.objects.create(
            subscription=subscription,
            amount=plan.price,
            user_uuid=subscription.user_uuid,
            yk_payment_id=payment_data["payment_id"],
            yk_payment_method_id=payment_data.get("payment_method_id"),
        )

        subscription.end_date = subscription.end_date + timedelta(days=plan.days)
        subscription.status = "pending"
        subscription.plan = plan
        subscription.auto_renew = auto_renew
        subscription.save()

        return payment_data["confirmation_url"]

    @classmethod
    def cancel_subscription(cls, subscription: Subscription) -> bool:
        """
        Отмена подписки.

        :param subscription: объект БД Subscription
        :return: True, если возврат произошел, иначе False
        """
        import logging

        logger = logging.getLogger("sub")
        logger.info(f"Отменяем подписку пользователю {subscription.user_uuid}")

        last_payment = (
            PaymentModel.objects.filter(subscription=subscription)
            .exclude(yk_payment_method_id__isnull=True)
            .order_by("-id")
            .first()
        )

        if last_payment:
            refund = cls.yoo_client.refund_payment(
                payment_id=last_payment.yk_payment_id,
                amount=float(subscription.plan.price),
            )

            logger.info(f"Статус возврата: {refund['status']}")

            if refund["status"] != "succeeded":
                logger.info("Возврат не удался")
                return False

        subscription.status = "cancelled"
        subscription.save()

        if subscription.auto_renew:
            # Удаляем таску на автоматическую оплату
            auto_payment = AutoSubscriptionTasks.objects.filter(
                subscription=subscription
            ).first()

            if auto_payment:
                PeriodicTasksLogic.remove_periodic_task_with_clocked(auto_payment.task)

                auto_payment.delete()

        return True


class PeriodicTasksLogic:
    @classmethod
    def create_stop_subscription_task(
        cls, subscription_id: int, days: int
    ) -> PeriodicTask:
        task_name = f"stop_subscription_{subscription_id}"
        task_path = "apps.sub.tasks.stop_subscription"
        stop_subscription_time = timezone.now() + timedelta(days=days)
        task_kwargs = {"subscription_id": subscription_id}

        clocked_schedule = ClockedSchedule.objects.create(
            clocked_time=stop_subscription_time
        )

        return PeriodicTask.objects.create(
            clocked=clocked_schedule,
            name=task_name,
            task=task_path,
            kwargs=json.dumps(task_kwargs),
            one_off=True,
        )

    @classmethod
    def create_auto_payment_task(cls, subscription_id: int, days: int) -> PeriodicTask:
        task_name = f"auto_payment_{subscription_id}"
        task_path = "apps.sub.tasks.make_autopayment"
        make_autopayment_time = timezone.now() + timedelta(days=days)
        task_kwargs = {"subscription_id": subscription_id}

        clocked_schedule = ClockedSchedule.objects.create(
            clocked_time=make_autopayment_time
        )

        return PeriodicTask.objects.create(
            clocked=clocked_schedule,
            name=task_name,
            task=task_path,
            kwargs=json.dumps(task_kwargs),
            one_off=True,
        )

    @classmethod
    def remove_periodic_task_with_clocked(cls, periodic_task: PeriodicTask) -> None:
        # Удаляем периодическую таску из БД
        clocked = periodic_task.clocked

        periodic_task.delete()

        assert isinstance(clocked, ClockedSchedule)
        clocked.delete()

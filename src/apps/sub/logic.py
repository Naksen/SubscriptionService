import os
from dotenv import load_dotenv

import uuid
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from yookassa import Configuration, Payment, Refund
from .models import Plan, Subscription, Payment as PaymentModel

load_dotenv()

class YooKassaClient:
    def __init__(cls, account_id: str, secret_key: str):
        Configuration.account_id = account_id
        Configuration.secret_key = secret_key

    def create_payment(cls, amount: float, currency: str, return_url: str, user_id: str,
                       save_payment_method: bool = False, description: str = None) -> dict:
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
        payment = Payment.create({
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
            "save_payment_method": save_payment_method,
            "metadata": {
                "user_id": user_id
            }
        }, uuid.uuid4())

        # Возвращаем confirmation_url и информацию о платеже
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": payment.amount,
            "created_at": payment.created_at,
            "confirmation_url": payment.confirmation.confirmation_url if payment.confirmation else None,
            "description": payment.description,
            "metadata": payment.metadata
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
            "cancellation_details": response.cancellation_details
        }

    def get_user_payments_history(cls, user_id: str, limit: int = 100, **list_params) -> list:
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
        # Если у вас есть очень много платежей, понадобится механизм пагинации.
        payments = Payment.list(limit=limit, **list_params)

        user_payments = []
        for p in payments.items:
            if p.metadata and p.metadata.get("user_id") == user_id:
                user_payments.append({
                    "payment_id": p.id,
                    "status": p.status,
                    "paid": p.paid,
                    "amount": p.amount,
                    "created_at": p.created_at,
                    "description": p.description,
                    "metadata": p.metadata,
                    "payment_method_id": p.payment_method.id if p.payment_method else None,
                })
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
            "payment_method_id": payment.payment_method.id if payment.payment_method else None,
        }

    def charge_autopayment(cls, user_id: str, amount: float, currency: str, payment_method_id: str, description: str) -> dict:
        """
        Совершает автоплатеж с сохраненным способом оплаты.

        :param amount: сумма списания
        :param currency: валюта
        :param payment_method_id: идентификатор сохраненного способа оплаты (получен из успешного платежа)
        :param description: описание платежа
        :return: данные о созданном платеже
        """
        payment = Payment.create({
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency
            },
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description,
            "metadata": {
                "user_id": user_id
            }
        }, uuid.uuid4())

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": payment.amount,
            "created_at": payment.created_at,
            "description": payment.description,
            "metadata": payment.metadata,
        }

    def refund_payment(cls, payment_id: str, amount: float, currency: str = "RUB") -> dict:
        """
        Возврат платежа.

        :param payment_id: идентификатор исходного платежа
        :param amount: сумма возврата
        :param currency: валюта
        :return: данные о возврате
        """
        refund = Refund.create({
            "payment_id": payment_id,
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency
            }
        }, uuid.uuid4())

        return {
            "refund_id": refund.id,
            "status": refund.status,
            "payment_id": refund.payment_id,
            "amount": refund.amount,
            "created_at": refund.created_at,
            "description": refund.description,
            "metadata": refund.metadata
        }


class SubscriptionLogic:
    account_id = os.getenv("YOOKASSA_ACCOUNT_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    yoo_client = YooKassaClient(account_id, secret_key)

    @classmethod
    def create_subscription(cls, plan_id: int, user_uuid: str, auto_renew: bool, return_url: str) -> str:
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
        end_date = now + timedelta(days=plan.duration)

        # Создаем подписку 
        # TODO: Поменять статус на pending, нужно получить уведомление с юкассы после подтверждения платежа
        subscription = Subscription.objects.create(
            user_uuid=user_uuid,
            plan=plan,
            status='active',  # возможно стоит сделать 'pending', если вы хотите активировать после успешной оплаты
            start_date=now,
            end_date=end_date,
            auto_renew=auto_renew,
        )

        # Создаем платеж через YooKassa
        payment_data = cls.yoo_client.create_payment(
            amount=float(plan.price),
            currency='RUB',
            return_url=return_url,
            user_id=user_uuid,
            save_payment_method=auto_renew,  # Если автопродление, то сохраняем способ оплаты
            description=f"Subscription {subscription.id} for user {user_uuid}"
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
    def get_user_subscriptions(cls, user_uuid: str) -> Subscription:
        """
        Получить историю подписок по UUID пользователя.

        :param user_uuid: UUID пользователя
        :return: QuerySet или список подписок
        """
        return Subscription.objects.filter(user_uuid=user_uuid).order_by('-created_at')

    @classmethod
    def renew_subscription(cls, subscription_id: int):
        """
        Продлить подписку через автоплатеж. Предполагается, что у подписки был сохранен способ оплаты.

        :param subscription_id: ID подписки
        :return: данные о созданном автоплатеже
        """
        subscription = Subscription.objects.get(id=subscription_id)
        if subscription.status != 'active' or not subscription.auto_renew:
            raise ValueError("Subscription cannot be renewed automatically")

        # Находим последний платеж с сохраненным способом оплаты (yk_payment_method_id)
        last_payment = Payment.objects.filter(subscription=subscription).exclude(yk_payment_method_id__isnull=True).order_by('-id').first()
        if not last_payment or not last_payment.yk_payment_method_id:
            raise ValueError("No saved payment method found for this subscription")

        # Совершаем автоплатеж
        payment_data = cls.yoo_client.charge_autopayment(
            user_id=str(subscription.user_uuid),
            amount=float(subscription.plan.price),
            currency='RUB',
            payment_method_id=last_payment.yk_payment_method_id,
            description=f"Renew subscription {subscription.id} for user {subscription.user_uuid}"
        )

        # Обновляем дату окончания подписки
        with transaction.atomic():
            subscription.end_date = subscription.end_date + timedelta(days=subscription.plan.duration)
            subscription.save()

            # Сохраняем новый платеж
            PaymentModel.objects.create(
                subscription=subscription,
                amount=subscription.plan.price,
                user_uuid=subscription.user_uuid,
                yk_payment_id=payment_data["payment_id"],
                yk_payment_method_id=payment_data.get("payment_method_id"),
            )

        return payment_data

    @classmethod
    def renew_subscription_through_payment(cls, subscription_id: int, return_url: str, auto_renew: bool) -> str:
        """
        Продлить подписку за счёт обычной оплаты (не автоплатежа).
        Возвращает ссылку на оплату. После оплаты можно обновить подписку.

        :param subscription_id: ID подписки
        :param return_url: URL для возвращения после оплаты
        :return: URL для оплаты
        """
        subscription = Subscription.objects.get(id=subscription_id)
        if subscription.status != 'active':
            raise ValueError("Only active subscription can be renewed through payment.")

        plan = subscription.plan

        # Создаем платеж через YooKassa. Здесь мы не сохраняем payment_method для автоплатежа.
        payment_data = cls.yoo_client.create_payment(
            amount=float(plan.price),
            currency='RUB',
            return_url=return_url,
            user_id=str(subscription.user_uuid),
            save_payment_method=auto_renew,  # здесь можно оставить False, если не хотим сохранять способ оплаты
            description=f"Manual renewal for subscription {subscription.id} user {subscription.user_uuid}"
        )

        # Сохраняем данные платежа в БД
        PaymentModel.objects.create(
            subscription=subscription,
            amount=plan.price,
            user_uuid=subscription.user_uuid,
            yk_payment_id=payment_data["payment_id"],
            yk_payment_method_id=payment_data.get("payment_method_id"),
        )
        
        subscription.end_date = subscription.end_date + timedelta(days=plan.duration)
        subscription.save()

        return payment_data["confirmation_url"]

    @classmethod
    def cancel_subscription(cls, subscription_id: int, user_uuid: str):
        """
        Отмена подписки.
        
        :param subscription_id: ID подписки
        :param user_uuid: UUID пользователя
        :return: обновленная подписка
        """
        subscription = Subscription.objects.get(id=subscription_id, user_uuid=user_uuid)
        subscription.status = 'cancelled'
        subscription.save()
        return subscription

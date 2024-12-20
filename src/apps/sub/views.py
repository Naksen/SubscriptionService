import json

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from yookassa.domain.notification import WebhookNotification


from .models import Plan, Subscription
from . import serializers, sub_types, logic, models


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = serializers.PlanSerializer


class SubcriptionViewSet(viewsets.GenericViewSet):

    @extend_schema(
        request=serializers.CreateSubscriptionRequestSerializer,
        responses={200: serializers.CreateSubscriptionResponseSerializer},
    )
    @action(methods=["POST"], detail=False)
    def create_subscription(self, request: Request) -> Response:
        """
        Ручка для создания подписки
        """
        request_serializer = serializers.CreateSubscriptionRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)
        create_sub_body: sub_types.CreateSubscription = (
            request_serializer.validated_data
        )  # type: ignore

        if Subscription.objects.filter(user_uuid=create_sub_body["user_uuid"]).exists():
            return Response(
                {"detail": "user with the same uuid already has the subscription"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if Plan.objects.filter(pk=create_sub_body["plan_id"]).exists() is False:
            return Response(
                {"detail": "plan not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        create_sub_response = logic.SubscriptionLogic.create_subscription(
            plan_id=create_sub_body["plan_id"],
            user_uuid=create_sub_body["user_uuid"],
            auto_renew=create_sub_body["auto_renew"],
            return_url=create_sub_body["return_url"],
        )

        response_serializer = serializers.CreateSubscriptionResponseSerializer(
            {"payment_url": create_sub_response}
        )
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False)
    def get_subscription_by_user_uuid(self, request: Request) -> Response:
        """
        Ручка для получения подписки по user_uuid
        """
        user_uuid = request.query_params.get("user_uuid", None)

        if not user_uuid:
            return Response(
                {"detail": "user_uuid is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        subscription = models.Subscription.objects.filter(user_uuid=user_uuid).first()
        if subscription is None:
            return Response(
                {"detail": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = serializers.SubscriptionRequestSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=serializers.RenewSubscriptionRequestSerializer,
        responses={200: serializers.RenewSubscriptionResponseSerializer},
    )
    @action(methods=["POST"], detail=False)
    def renew_subscription_through_payment(self, request: Request) -> Response:
        """
        Ручка для ручного продления подписки

        Можно продлить только cancelled подписку
        """
        request_serializer = serializers.RenewSubscriptionRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        renew_subscription: sub_types.RenewSubscription = (
            request_serializer.validated_data
        )  # type: ignore

        subscription = Subscription.objects.filter(user_uuid=renew_subscription["user_uuid"]).first()
        if subscription is None:
            return Response(
                {"detail": "Subscription not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        if subscription.status != "cancelled":
            return Response(
                {"detail": "Subscription is not cancelled"}, status=status.HTTP_400_BAD_REQUEST
            )

        create_sub_response = (
            logic.SubscriptionLogic.renew_subscription_through_payment(
                plan_id=renew_subscription["plan_id"],
                subscription=subscription,
                auto_renew=renew_subscription["auto_renew"],
                return_url=renew_subscription["return_url"],
            )
        )

        response_serializer = serializers.RenewSubscriptionResponseSerializer(
            {"payment_url": create_sub_response}
        )
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False)
    def cancel_subscription(self, request: Request) -> Response:
        """
        Ручка для отмены подписки

        Можно отменить только активную подписку
        """
        user_uuid = request.query_params.get("user_uuid", None)
        if user_uuid is None:
            return Response(
                {"detail": "user_uuid is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = models.Subscription.objects.filter(user_uuid=user_uuid).first()

        if subscription is None:
            return Response(
                {"detail": "subscription not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.status != "active":
            return Response(
                {"detail": "subscription is not active"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_canceled = logic.SubscriptionLogic.cancel_subscription(subscription)

        if is_canceled is False:
            return Response(
                {"detail": "couldn't issue refund"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_200_OK)

    @action(methods=["DELETE"], detail=False)
    def remove_subscription(self, request: Request) -> Response:
        """
        Ручка удаления подписки по user_uuid

        Можно удалить только cancelled подписку
        """
        user_uuid = request.query_params.get("user_uuid", None)
        if user_uuid is None:
            return Response(
                {"detail": "user_uuid is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = Subscription.objects.filter(user_uuid=user_uuid).first()
        if subscription is None:
            return Response(
                {"detail": "subscription not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.status != "cancelled":
            return Response(
                {"detail": "subscription is not cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.auto_renew:
            # Удаляем таску на автоматическую оплату
            auto_payment = models.AutoSubscriptionTasks.objects.filter(subscription=subscription).first()

            if auto_payment:
                logic.PeriodicTasksLogic.remove_periodic_task_with_clocked(auto_payment.task)

                auto_payment.delete()

        subscription.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(methods=["GET"], detail=False)
    def get_user_payment_history(self, request: Request) -> Response:
        """
        Получение истории оплаты по user_uuid
        """

        user_uuid = request.query_params.get("user_uuid", None)

        payments = models.Payment.objects.filter(user_uuid=user_uuid)

        response_serializer = serializers.PaymentHistoryResponseSerializer(
            payments,
            many=True,
        )

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=serializers.PaymentNotificationRequestSerializer,
    )
    @action(methods=["POST"], detail=False)
    def payment_notification(self, request: Request) -> Response:
        """
        Ручка для уведомления об оплате
        """
        try:
            event_json = json.loads(request.body)
        except json.JSONDecodeError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Создаём объект уведомления
        try:
            notification_object = WebhookNotification(event_json)
        except Exception:
            # Если не удалось создать уведомление, вернем ошибку
            return Response(status=status.HTTP_400_BAD_REQUEST)

        payment = notification_object.object

        if not payment:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        payment_db = models.Payment.objects.filter(yk_payment_id=payment.id).first()

        if payment_db is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        subscription: models.Subscription = payment_db.subscription

        # Если платеж прошел
        if payment.paid is True:

            # Ставим статус active
            subscription.status = "active"

            # Если установленно автоматическое продление подписки
            if subscription.auto_renew and payment.payment_method:

                payment_db.yk_payment_method_id = payment.payment_method.id
                payment_db.save(update_fields=["yk_payment_method_id"])

                # Таска на автоматическое продление подписки
                auto_payment_task = logic.PeriodicTasksLogic.create_auto_payment_task(
                    subscription.pk, subscription.plan.days
                )

                models.AutoSubscriptionTasks.objects.create(
                    subscription=subscription, task=auto_payment_task
                )

            else:
                # Создаем таску на остановку подписки по её окончанию 
                stop_sub_task = logic.PeriodicTasksLogic.create_stop_subscription_task(subscription.pk, subscription.plan.days)
                models.AutoSubscriptionTasks.objects.create(
                    subscription=subscription, task=stop_sub_task
                )
        else:
            # Если оплата не прошла
            subscription.status = "cancelled"
        subscription.save(
            update_fields=[
                "status",
            ]
        )

        return Response(status=status.HTTP_200_OK)

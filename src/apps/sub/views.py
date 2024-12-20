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
            if payment.payment_method:
                subscription.auto_renew = True

                payment_db.yk_payment_method_id = payment.payment_method.id

                payment_db.save(update_fields=["yk_payment_method_id"])

                # TODO: Таска на автоматическое продление подписки

            subscription.save(update_fields=["status", "auto_renew"])

        else:
            # Если оплата не прошла
            subscription.status = "cancelled"
            subscription.save(
                update_fields=[
                    "status",
                ]
            )

        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        request=serializers.CreateSubscriptionRequestSerializer,
        responses={200: serializers.CreateSubscriptionResponseSerializer},
    )
    @action(methods=["POST"], detail=False)
    def renew_subscription_through_payment(self, request: Request) -> Response:
        """
        Ручка для ручного продления подписки
        """
        request_serializer = serializers.RenewSubscriptionRequestSerializer(
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        subscription_id = request.query_params.get("id", None)

        if not subscription_id:
            return Response(
                {"detail": "subscription_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Subscription.objects.filter(pk=subscription_id).exists() is False:
            return Response(
                {"detail": "Subscription not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        renew_subscription: sub_types.RenewSubscription = (
            request_serializer.validated_data
        )

        create_sub_response = (
            logic.SubscriptionLogic.renew_subscription_through_payment(
                subscription_id=subscription_id,
                auto_renew=renew_subscription["auto_renew"],
                return_url=renew_subscription["return_url"],
            )
        )

        response_serializer = serializers.RenewSubscriptionResponseSerializer(
            {"payment_url": create_sub_response}
        )
        return Response(data=response_serializer.data, status=status.HTTP_200_OK)

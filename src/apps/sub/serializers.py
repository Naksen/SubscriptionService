from rest_framework import serializers
from .models import Plan, Subscription, Payment


class CheckNameRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    surname = serializers.CharField()


class CheckNameResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    surname = serializers.CharField()


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "price", "days"]


class CreateSubscriptionRequestSerializer(serializers.Serializer):
    plan_id: int = serializers.IntegerField()
    user_uuid: str = serializers.CharField()
    auto_renew: bool = serializers.BooleanField()
    return_url: str = serializers.CharField()


class CreateSubscriptionResponseSerializer(serializers.Serializer):
    payment_url: str = serializers.CharField()


class PaymentNotificationObjectAmountSerializer(serializers.Serializer):
    value = serializers.CharField()
    currency = serializers.CharField()


class PaymentNotificationObjectPaymentMethodCardSerializer(serializers.Serializer):
    first6 = serializers.CharField()
    last4 = serializers.CharField()
    expiry_month = serializers.CharField()
    expiry_year = serializers.CharField()
    card_type = serializers.CharField()
    issuer_country = serializers.CharField()
    issuer_name = serializers.CharField()


class PaymentNotificationObjectPaymentMethodSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.CharField()
    saved = serializers.BooleanField()
    card = PaymentNotificationObjectPaymentMethodCardSerializer()
    title = serializers.CharField()


class PaymentNotificationObjectAuthorizationDetailsSerializer(serializers.Serializer):
    rrn = serializers.CharField()
    auth_code = serializers.CharField()
    three_d_secure = serializers.DictField()  # Можно подробнее при необходимости


class PaymentNotificationObjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    status = serializers.CharField()
    paid = serializers.BooleanField()
    amount = PaymentNotificationObjectAmountSerializer()
    authorization_details = PaymentNotificationObjectAuthorizationDetailsSerializer()
    created_at = serializers.CharField()
    description = serializers.CharField()
    expires_at = serializers.CharField()
    metadata = serializers.DictField()
    payment_method = PaymentNotificationObjectPaymentMethodSerializer()
    refundable = serializers.BooleanField()
    test = serializers.BooleanField()


class PaymentNotificationRequestSerializer(serializers.Serializer):
    type = serializers.CharField()
    event = serializers.CharField()
    object = PaymentNotificationObjectSerializer()


class SubscriptionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


class RenewSubscriptionRequestSerializer(serializers.Serializer):
    plan_id: int = serializers.IntegerField()
    user_uuid: str = serializers.CharField()
    auto_renew: bool = serializers.BooleanField()
    return_url: str = serializers.CharField()


class RenewSubscriptionResponseSerializer(CreateSubscriptionResponseSerializer):
    pass


class PaymentHistoryResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"

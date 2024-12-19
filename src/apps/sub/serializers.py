from rest_framework import serializers
from .models import Plan

class CheckNameRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    surname = serializers.CharField()

class CheckNameResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    surname = serializers.CharField()


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "price", "duration"]


class CreateSubscriptionRequestSerializer(serializers.Serializer):
    plan_id: int = serializers.IntegerField()
    user_uuid: str = serializers.CharField()
    auto_renew: bool = serializers.BooleanField()
    return_url: str = serializers.CharField()


class CreateSubscriptionResponseSerializer(serializers.Serializer):
    payment_url: str = serializers.CharField()

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
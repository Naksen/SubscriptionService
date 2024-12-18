from rest_framework import serializers

class CheckNameRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    surname = serializers.CharField()

class CheckNameResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    surname = serializers.CharField()
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Plan
from . import serializers, sub_types

class TestViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin, # Миксин для реализации метода LIST. Для методов RETRIEVE, CREATE, DELETE тоже есть миксин. Можно и без них
):
    @action(methods=["GET"], detail=False)
    def ping(self, _: Request,) -> Response:
        return Response(status=status.HTTP_200_OK)
    
    @action(methods=["POST"], detail=False)
    def fake_check_name(self, request: Request) -> Response:
        request_serializer = serializers.CheckNameRequestSerializer( # С помощью сериализаторов валидируем (десириализуем) прищедшее тело запроса (используется вместо pydantic классов в Django)
            data=request.data,
        )
        request_serializer.is_valid(raise_exception=True)

        typed_body: sub_types.FakeNameUsername = request_serializer.validated_data # Пример того, как можно типизировать body

        response_serializer = serializers.CheckNameResponseSerializer(typed_body) # Также с помощью сериализаторов сериализуем объекты

        return Response(data=response_serializer.data, status=status.HTTP_200_OK)


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = serializers.PlanSerializer

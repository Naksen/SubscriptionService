from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.sub import views as sub_views

router = DefaultRouter()


router.register(
    r"plans",
    sub_views.PlanViewSet,
    basename="plans",
)

router.register(
    r"sub",
    sub_views.SubcriptionViewSet,
    basename="sub",
)

urlpatterns = [
    path("", include(router.urls)), # Регистрация роутов
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),  # Сваггер
]
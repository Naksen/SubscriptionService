from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Plan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название плана")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Стоимость"
    )
    month = models.IntegerField(
        verbose_name="Количество месяцев",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    class Meta:
        db_table = "plans"
        verbose_name = "Тарифный план"
        verbose_name_plural = "Тарифные планы"

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("pending", "Pending"),
    ]

    user_uuid = models.UUIDField(verbose_name="UUID пользователя")
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, verbose_name="Тарифный план"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, verbose_name="Статус подписки"
    )
    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")
    auto_renew = models.BooleanField(default=False, verbose_name="Автопродление")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "subscription"
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"Subscription {self.id} for user {self.user_uuid}"


class Payment(models.Model):
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, verbose_name="Подписка"
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Сумма платежа"
    )
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата платежа")
    yk_payment_id = models.CharField(max_length=255, verbose_name="ID платежа в ЮKassa")
    yk_payment_method_id = models.CharField(
        max_length=255, verbose_name="ID способа оплаты в ЮKassa", blank=True, null=True
    )
    user_uuid = models.UUIDField(verbose_name="UUID пользователя")

    class Meta:
        db_table = "payment"
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"

    def __str__(self) -> str:
        return f"Payment {self.id} for subscription {self.subscription_id}"

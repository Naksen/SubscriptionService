# Generated by Django 5.1.4 on 2024-12-20 16:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100, verbose_name="Название плана"),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Стоимость"
                    ),
                ),
                ("days", models.IntegerField(verbose_name="Количество дней")),
            ],
            options={
                "verbose_name": "Тарифный план",
                "verbose_name_plural": "Тарифные планы",
                "db_table": "plans",
            },
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user_uuid",
                    models.UUIDField(unique=True, verbose_name="UUID пользователя"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                            ("pending", "Pending"),
                        ],
                        max_length=20,
                        verbose_name="Статус подписки",
                    ),
                ),
                ("start_date", models.DateTimeField(verbose_name="Дата начала")),
                ("end_date", models.DateTimeField(verbose_name="Дата окончания")),
                (
                    "auto_renew",
                    models.BooleanField(default=False, verbose_name="Автопродление"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата создания"
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sub.plan",
                        verbose_name="Тарифный план",
                    ),
                ),
            ],
            options={
                "verbose_name": "Подписка",
                "verbose_name_plural": "Подписки",
                "db_table": "subscription",
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="Сумма платежа"
                    ),
                ),
                (
                    "payment_date",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Дата платежа"
                    ),
                ),
                (
                    "yk_payment_id",
                    models.CharField(
                        max_length=255, verbose_name="ID платежа в ЮKassa"
                    ),
                ),
                (
                    "yk_payment_method_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="ID способа оплаты в ЮKassa",
                    ),
                ),
                ("user_uuid", models.UUIDField(verbose_name="UUID пользователя")),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sub.subscription",
                        verbose_name="Подписка",
                    ),
                ),
            ],
            options={
                "verbose_name": "Платеж",
                "verbose_name_plural": "Платежи",
                "db_table": "payment",
            },
        ),
        migrations.CreateModel(
            name="AutoSubscriptionTasks",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        default=None,
                        help_text="Задача на операцию, связанную с подпиской",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="django_celery_beat.periodictask",
                        verbose_name="Задача на операцию, связанную с подпиской",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sub.subscription",
                        unique=True,
                        verbose_name="Подписка",
                    ),
                ),
            ],
        ),
    ]

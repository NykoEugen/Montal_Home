from django.db import migrations, models
import django.db.models.deletion


def create_initial_statuses(apps, schema_editor):
    OrderStatus = apps.get_model("checkout", "OrderStatus")
    Order = apps.get_model("checkout", "Order")

    statuses = [
        {
            "slug": "new",
            "name": "Новий",
            "salesdrive_status_id": 1,
            "sort_order": 10,
            "is_default": True,
        },
        {
            "slug": "processing",
            "name": "В обробці",
            "salesdrive_status_id": None,
            "sort_order": 20,
        },
        {
            "slug": "confirmed",
            "name": "Підтверджено",
            "salesdrive_status_id": 2,
            "sort_order": 30,
        },
        {
            "slug": "ready_to_ship",
            "name": "На відправку",
            "salesdrive_status_id": 3,
            "sort_order": 40,
        },
        {
            "slug": "shipped",
            "name": "Відправлено",
            "salesdrive_status_id": 4,
            "sort_order": 50,
        },
        {
            "slug": "sale",
            "name": "Продаж",
            "salesdrive_status_id": 5,
            "sort_order": 60,
        },
        {
            "slug": "canceled",
            "name": "Відмова",
            "salesdrive_status_id": 6,
            "sort_order": 70,
        },
        {
            "slug": "returned",
            "name": "Повернення",
            "salesdrive_status_id": 7,
            "sort_order": 80,
        },
        {
            "slug": "deleted",
            "name": "Видалений",
            "salesdrive_status_id": 8,
            "sort_order": 90,
        },
    ]

    slug_to_obj = {}
    for status in statuses:
        obj, _ = OrderStatus.objects.get_or_create(
            slug=status["slug"],
            defaults={
                "name": status["name"],
                "salesdrive_status_id": status["salesdrive_status_id"],
                "sort_order": status["sort_order"],
                "is_default": status.get("is_default", False),
                "is_active": True,
            },
        )
        slug_to_obj[obj.slug] = obj

    legacy_map = {
        "new": "new",
        "processing": "processing",
        "shipped": "shipped",
        "completed": "sale",
        "canceled": "canceled",
    }
    default_status = slug_to_obj.get("new")

    for order in Order.objects.all():
        legacy_value = getattr(order, "status", None)
        target_slug = legacy_map.get(legacy_value, "new")
        order.status_new = slug_to_obj.get(target_slug, default_status)
        order.save(update_fields=["status_new"])


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0010_order_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Назва статусу")),
                (
                    "slug",
                    models.SlugField(
                        blank=True,
                        help_text="Використовується у внутрішніх інтеграціях",
                        max_length=50,
                        unique=True,
                        verbose_name="Системна назва",
                    ),
                ),
                (
                    "salesdrive_status_id",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Опціонально. Використовується для синхронізації вебхуком",
                        null=True,
                        unique=True,
                        verbose_name="ID статусу в SalesDrive",
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="Присвоюється новим замовленням, якщо не вибрано інше значення.",
                        verbose_name="Статус за замовчуванням",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Активний")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок сортування")),
            ],
            options={
                "verbose_name": "Статус замовлення",
                "verbose_name_plural": "Статуси замовлень",
                "ordering": ("sort_order", "name"),
            },
        ),
        migrations.AddField(
            model_name="order",
            name="status_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="checkout.orderstatus",
                verbose_name="Статус замовлення",
            ),
        ),
        migrations.RunPython(create_initial_statuses, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="order",
            name="status",
        ),
        migrations.RenameField(
            model_name="order",
            old_name="status_new",
            new_name="status",
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to="checkout.orderstatus",
                verbose_name="Статус замовлення",
            ),
        ),
    ]

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SeasonalCampaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=255)),
                ("enabled", models.BooleanField(default=False)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                ("priority", models.IntegerField(default=0)),
                ("pack_path", models.CharField(max_length=255)),
                ("path_glob", models.CharField(blank=True, max_length=255, null=True)),
                ("country", models.CharField(blank=True, max_length=2, null=True)),
                ("device", models.CharField(blank=True, max_length=10, null=True)),
                (
                    "percentage_rollout",
                    models.IntegerField(
                        default=100,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("-priority", "-starts_at", "slug"),
            },
        ),
    ]

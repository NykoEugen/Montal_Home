from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("furniture", "0028_bed_size_variant"),
    ]

    operations = [
        migrations.DeleteModel(
            name="BedSizeVariant",
        ),
    ]

from django.db import migrations

def create_initial_categories(apps, schema_editor):
    Category = apps.get_model('shop', 'Category')
    categories = [
        {'name': 'Стільці', 'slug': 'chairs'},
        {'name': 'Столи кухонні', 'slug': 'kitchen-tables'},
        {'name': 'Крісла', 'slug': 'armchairs'},
        {'name': 'Дивани', 'slug': 'sofas'},
        {'name': 'Ліжка', 'slug': 'beds'},
        {'name': 'Матраси', 'slug': 'mattresses'},
        {'name': 'Комоди', 'slug': 'dressers'},
        {'name': 'Шафи-купе', 'slug': 'wardrobes'},
    ]
    for category in categories:
        Category.objects.create(name=category['name'], slug=category['slug'])

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_categories),
    ]
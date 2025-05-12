from django.db import migrations
from typing import Dict, List

def create_initial_categories(apps, schema_editor) -> None:
    """Створює початкові категорії."""
    Category = apps.get_model('shop', 'Category')
    categories: List[Dict[str, str]] = [
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
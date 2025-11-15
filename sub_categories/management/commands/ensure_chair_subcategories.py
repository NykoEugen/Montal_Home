from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from categories.models import Category
from sub_categories.models import SubCategory

CHAIR_SUBCATEGORIES = [
    "Обідні стільці",
    "Напівбарні",
    "Барні",
    "Крісла",
    "М'які крісла",
]


class Command(BaseCommand):
    help = "Створює підкатегорії для категорії 'Стільці'."

    def handle(self, *args, **options):
        category = Category.objects.filter(name__iexact="Стільці").first()
        if not category:
            raise CommandError("Категорію 'Стільці' не знайдено.")

        created = 0
        updated = 0
        for name in CHAIR_SUBCATEGORIES:
            slug = self._generate_unique_slug(name)
            sub_category, was_created = SubCategory.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slug,
                    "category": category,
                },
            )
            if was_created:
                created += 1
            else:
                changed = False
                if sub_category.category_id != category.id:
                    sub_category.category = category
                    changed = True
                if not sub_category.slug:
                    sub_category.slug = slug
                    changed = True
                if changed:
                    sub_category.save(update_fields=["category", "slug"])
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Створено: {created}, оновлено: {updated}, всього: {len(CHAIR_SUBCATEGORIES)}"
            )
        )

    def _generate_unique_slug(self, name: str) -> str:
        base_slug = slugify(name) or "subcategory"
        candidate = base_slug
        index = 1
        while SubCategory.objects.filter(slug=candidate).exists():
            index += 1
            candidate = f"{base_slug}-{index}"
        return candidate

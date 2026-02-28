from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from categories.models import Category
from sub_categories.models import SubCategory


TARGET_SUBCATEGORIES = [
    "Полиці (Антресоль)",
    "Тумби",
    "Пенали",
    "Комоди",
    "Столи",
    "Подіуми",
    "Шафи",
    "Ергономічні елементи",
    "Модульні системи",
]

LEGACY_NAME_ALIASES = {
    "Полиці (Антресоль)": ["Полиці"],
    "Пенали": ["Пенал"],
    "Комоди": ["Комод"],
}


class Command(BaseCommand):
    help = "Створює або оновлює підкатегорії для 'Корпусні меблі'"

    def handle(self, *args, **options):
        category = Category.objects.filter(name__iexact="Корпусні меблі").first()
        if not category:
            raise CommandError("Категорію 'Корпусні меблі' не знайдено.")

        created = 0
        updated = 0

        for name in TARGET_SUBCATEGORIES:
            slug = self._generate_unique_slug(name)
            sub_category = self._find_existing_subcategory(name)
            if sub_category:
                was_created = False
            else:
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
                if sub_category.name != name:
                    sub_category.name = name
                    changed = True
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
                f"Готово. Створено: {created}, оновлено: {updated}, всього: {len(TARGET_SUBCATEGORIES)}"
            )
        )

    def _find_existing_subcategory(self, target_name: str):
        sub_category = SubCategory.objects.filter(name__iexact=target_name).first()
        if sub_category:
            return sub_category
        for legacy_name in LEGACY_NAME_ALIASES.get(target_name, []):
            legacy = SubCategory.objects.filter(name__iexact=legacy_name).first()
            if legacy:
                return legacy
        return None

    def _generate_unique_slug(self, name: str) -> str:
        base_slug = slugify(name) or "subcategory"
        candidate = base_slug
        index = 1
        while SubCategory.objects.filter(slug=candidate).exists():
            index += 1
            candidate = f"{base_slug}-{index}"
        return candidate

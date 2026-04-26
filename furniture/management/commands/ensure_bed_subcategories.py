from django.core.management.base import BaseCommand, CommandError

from categories.models import Category
from sub_categories.models import SubCategory

BED_SUBCATEGORIES = [
    "Ліжка",
]


class Command(BaseCommand):
    help = "Створює підкатегорії ліжок у категорії 'Ліжка', якщо вони ще не існують."

    def handle(self, *args, **options):
        category = Category.objects.filter(name__iexact="Ліжка").first()
        if not category:
            raise CommandError(
                "Категорію 'Ліжка' не знайдено в БД. "
                "Переконайтеся, що вона існує перед запуском цієї команди."
            )

        created_count = 0
        for name in BED_SUBCATEGORIES:
            subcat, created = SubCategory.objects.get_or_create(
                name=name,
                category=category,
                defaults={"slug": self._make_slug(name, category)},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Створено підкатегорію '{name}'"))
            else:
                self.stdout.write(f"Підкатегорія '{name}' вже існує (id={subcat.id})")

        if created_count:
            self.stdout.write(self.style.SUCCESS(f"Готово: створено {created_count} підкатегорій."))
        else:
            self.stdout.write("Усі підкатегорії вже існують.")

    @staticmethod
    def _make_slug(name: str, category: Category) -> str:
        from django.utils.text import slugify
        base = slugify(name)
        slug = base
        n = 1
        while SubCategory.objects.filter(slug=slug).exists():
            n += 1
            slug = f"{base}-{n}"
        return slug

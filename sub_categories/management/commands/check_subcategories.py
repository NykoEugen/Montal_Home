from django.core.management.base import BaseCommand, CommandError

from categories.models import Category
from sub_categories.models import SubCategory


class Command(BaseCommand):
    help = (
        "Перевіряє, що підкатегорії з заданого списку існують у певній категорії.\n"
        "Приклад:\n"
        "  python manage.py check_subcategories --category 'Стільці' \\\n"
        "      --subcategories 'Обідні стільці' 'Барні'\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            required=True,
            help="Назва категорії (наприклад, 'Стільці', 'Матраци').",
        )
        parser.add_argument(
            "--subcategories",
            nargs="+",
            help="Список підкатегорій, які потрібно перевірити.",
        )

    def handle(self, *args, **options):
        category_name = options["category"]
        subcategories = options.get("subcategories")

        category = Category.objects.filter(name__iexact=category_name).first()
        if not category:
            raise CommandError(f"Категорію '{category_name}' не знайдено.")

        if not subcategories:
            existing = list(category.sub_categories.values_list("name", flat=True))
            self.stdout.write(
                self.style.SUCCESS(
                    f"У категорії '{category_name}' знайдено підкатегорії: "
                    + ", ".join(existing) if existing else "Підкатегорій поки немає."
                )
            )
            return

        missing = []
        for name in subcategories:
            exists = SubCategory.objects.filter(category=category, name__iexact=name).exists()
            if not exists:
                missing.append(name)

        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"Відсутні підкатегорії в '{category_name}': {', '.join(missing)}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Усі вказані підкатегорії існують у категорії '{category_name}'."
                )
            )

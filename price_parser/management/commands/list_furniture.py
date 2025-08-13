from django.core.management.base import BaseCommand
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'List furniture items and their size variants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--search',
            type=str,
            help='Search furniture by name'
        )
        parser.add_argument(
            '--show-sizes',
            action='store_true',
            help='Show size variants for each furniture'
        )

    def handle(self, *args, **options):
        queryset = Furniture.objects.all()
        
        if options['search']:
            queryset = queryset.filter(name__icontains=options['search'])
        
        self.stdout.write(f"\nFound {queryset.count()} furniture items:")
        self.stdout.write("=" * 80)
        
        for furniture in queryset:
            self.stdout.write(f"\nID: {furniture.id}")
            self.stdout.write(f"Name: {furniture.name}")
            self.stdout.write(f"Article Code: {furniture.article_code}")
            self.stdout.write(f"Current Price: {furniture.price}")
            
            if options['show_sizes']:
                size_variants = furniture.size_variants.all()
                if size_variants:
                    self.stdout.write("Size Variants:")
                    for variant in size_variants:
                        self.stdout.write(f"  ID: {variant.id} - {variant.dimensions} - Price: {variant.price}")
                else:
                    self.stdout.write("  No size variants")
            
            self.stdout.write("-" * 40) 
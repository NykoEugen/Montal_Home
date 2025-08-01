from django.core.management.base import BaseCommand
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'Add test size variants to existing furniture'

    def handle(self, *args, **options):
        furniture_items = Furniture.objects.all()
        
        if not furniture_items.exists():
            self.stdout.write(self.style.WARNING('No furniture items found'))
            return
        
        for furniture in furniture_items:
            # Check if furniture already has size variants
            if furniture.size_variants.exists():
                self.stdout.write(f'Skipping {furniture.name} - already has size variants')
                continue
            
            # Add some test size variants
            variants_data = [
                {'height': 80, 'width': 120, 'length': 60, 'price': furniture.price},
                {'height': 90, 'width': 140, 'length': 70, 'price': furniture.price * 1.2},
                {'height': 100, 'width': 160, 'length': 80, 'price': furniture.price * 1.4},
            ]
            
            for variant_data in variants_data:
                FurnitureSizeVariant.objects.create(
                    furniture=furniture,
                    **variant_data
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Added {len(variants_data)} size variants to {furniture.name}')
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully added test size variants')) 
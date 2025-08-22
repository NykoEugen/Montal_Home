from django.core.management.base import BaseCommand
from django.utils import timezone
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'Set up promotional prices for furniture size variants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--furniture-id',
            type=int,
            help='Furniture item ID to set promotional prices for'
        )
        parser.add_argument(
            '--variant-id',
            type=int,
            help='Specific size variant ID to set promotional price for'
        )
        parser.add_argument(
            '--discount-percent',
            type=int,
            default=20,
            help='Discount percentage to apply (default: 20)'
        )
        parser.add_argument(
            '--apply-to-all',
            action='store_true',
            help='Apply to all size variants of promotional furniture'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear promotional prices from size variants'
        )

    def handle(self, *args, **options):
        furniture_id = options['furniture_id']
        variant_id = options['variant_id']
        discount_percent = options['discount_percent']
        apply_to_all = options['apply_to_all']
        clear = options['clear']

        if clear:
            self.clear_promotional_prices(furniture_id, variant_id)
            return

        if variant_id:
            self.set_variant_promotion(variant_id, discount_percent)
        elif furniture_id:
            self.set_furniture_variants_promotion(furniture_id, discount_percent)
        elif apply_to_all:
            self.set_all_promotional_variants(discount_percent)
        else:
            self.show_current_promotions()

    def set_variant_promotion(self, variant_id, discount_percent):
        """Set promotional price for specific size variant."""
        try:
            variant = FurnitureSizeVariant.objects.get(id=variant_id)
            promotional_price = variant.price * (1 - discount_percent / 100)
            variant.promotional_price = round(promotional_price, 2)
            variant.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Set promotional price for {variant.furniture.name} - {variant.dimensions}: '
                    f'{variant.price} грн → {variant.promotional_price} грн (-{discount_percent}%)'
                )
            )
        except FurnitureSizeVariant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Size variant with ID {variant_id} not found')
            )

    def set_furniture_variants_promotion(self, furniture_id, discount_percent):
        """Set promotional prices for all variants of a furniture item."""
        try:
            furniture = Furniture.objects.get(id=furniture_id)
            variants = furniture.size_variants.all()
            
            if not variants.exists():
                self.stdout.write(
                    self.style.WARNING(f'No size variants found for furniture "{furniture.name}"')
                )
                return
            
            updated_count = 0
            for variant in variants:
                promotional_price = variant.price * (1 - discount_percent / 100)
                variant.promotional_price = round(promotional_price, 2)
                variant.save()
                updated_count += 1
                
                self.stdout.write(
                    f'  {variant.dimensions}: {variant.price} грн → {variant.promotional_price} грн (-{discount_percent}%)'
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Updated {updated_count} size variants for "{furniture.name}"')
            )
        except Furniture.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Furniture with ID {furniture_id} not found')
            )

    def set_all_promotional_variants(self, discount_percent):
        """Set promotional prices for all variants of promotional furniture."""
        promotional_furniture = Furniture.objects.filter(is_promotional=True)
        
        if not promotional_furniture.exists():
            self.stdout.write(
                self.style.WARNING('No promotional furniture found')
            )
            return
        
        total_updated = 0
        for furniture in promotional_furniture:
            variants = furniture.size_variants.all()
            if variants.exists():
                self.stdout.write(f'\n{furniture.name}:')
                for variant in variants:
                    promotional_price = variant.price * (1 - discount_percent / 100)
                    variant.promotional_price = round(promotional_price, 2)
                    variant.save()
                    total_updated += 1
                    
                    self.stdout.write(
                        f'  {variant.dimensions}: {variant.price} грн → {variant.promotional_price} грн (-{discount_percent}%)'
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nUpdated {total_updated} size variants total')
        )

    def clear_promotional_prices(self, furniture_id, variant_id):
        """Clear promotional prices from size variants."""
        if variant_id:
            try:
                variant = FurnitureSizeVariant.objects.get(id=variant_id)
                variant.promotional_price = None
                variant.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Cleared promotional price for {variant.furniture.name} - {variant.dimensions}')
                )
            except FurnitureSizeVariant.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Size variant with ID {variant_id} not found')
                )
        elif furniture_id:
            try:
                furniture = Furniture.objects.get(id=furniture_id)
                updated = furniture.size_variants.update(promotional_price=None)
                self.stdout.write(
                    self.style.SUCCESS(f'Cleared promotional prices for {updated} variants of "{furniture.name}"')
                )
            except Furniture.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Furniture with ID {furniture_id} not found')
                )
        else:
            updated = FurnitureSizeVariant.objects.filter(promotional_price__isnull=False).update(promotional_price=None)
            self.stdout.write(
                self.style.SUCCESS(f'Cleared promotional prices for {updated} size variants')
            )

    def show_current_promotions(self):
        """Show current promotional size variants."""
        variants_with_promotions = FurnitureSizeVariant.objects.filter(promotional_price__isnull=False)
        
        if not variants_with_promotions.exists():
            self.stdout.write(self.style.WARNING('No promotional size variants found'))
            return
        
        self.stdout.write(self.style.SUCCESS('Current promotional size variants:'))
        
        current_furniture = None
        for variant in variants_with_promotions.select_related('furniture').order_by('furniture__name'):
            if current_furniture != variant.furniture:
                current_furniture = variant.furniture
                self.stdout.write(f'\n{variant.furniture.name}:')
            
            discount = int(((variant.price - variant.promotional_price) / variant.price) * 100)
            self.stdout.write(
                f'  {variant.dimensions}: {variant.price} грн → {variant.promotional_price} грн (-{discount}%)'
            )
        
        self.stdout.write(
            self.style.WARNING(
                '\nTo set promotional prices, use:\n'
                '  python manage.py setup_size_variant_promotions --furniture-id <ID> --discount-percent <PERCENT>\n'
                '  python manage.py setup_size_variant_promotions --variant-id <ID> --discount-percent <PERCENT>\n'
                '  python manage.py setup_size_variant_promotions --apply-to-all --discount-percent <PERCENT>\n'
                '\nTo clear promotional prices:\n'
                '  python manage.py setup_size_variant_promotions --clear --furniture-id <ID>\n'
                '  python manage.py setup_size_variant_promotions --clear --variant-id <ID>\n'
                '  python manage.py setup_size_variant_promotions --clear'
            )
        )

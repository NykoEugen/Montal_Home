from django.core.management.base import BaseCommand
from django.utils import timezone
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'Remove promotional prices from size variants when parent furniture sale expires'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each variant',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # Get current time
        now = timezone.now()
        
        # Find all size variants that have promotional prices and belong to furniture with expired sales
        expired_variants = FurnitureSizeVariant.objects.filter(
            promotional_price__isnull=False,
            furniture__is_promotional=True,
            furniture__sale_end_date__isnull=False,
            furniture__sale_end_date__lt=now
        )
        
        if not expired_variants.exists():
            self.stdout.write(
                self.style.SUCCESS('No size variants with expired promotional prices found.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Found {expired_variants.count()} size variants with expired promotional prices:'
            )
        )
        
        total_savings = 0
        for variant in expired_variants:
            original_price = float(variant.price)
            promotional_price = float(variant.promotional_price)
            savings = original_price - promotional_price
            
            if verbose:
                self.stdout.write(
                    f'  - {variant.furniture.name} - {variant.dimensions} (ID: {variant.id})'
                )
                self.stdout.write(
                    f'    Parent sale ended: {variant.furniture.sale_end_date.strftime("%Y-%m-%d %H:%M:%S")}'
                )
                self.stdout.write(
                    f'    Original price: {original_price} грн'
                )
                self.stdout.write(
                    f'    Promotional price: {promotional_price} грн'
                )
                self.stdout.write(
                    f'    Savings: {savings} грн'
                )
                self.stdout.write('')
            
            total_savings += savings
            
            if not dry_run:
                # Remove promotional price
                variant.promotional_price = None
                variant.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Removed promotional price from: {variant.furniture.name} - {variant.dimensions}'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would remove promotional prices from {expired_variants.count()} size variants'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f'Total savings that would be lost: {total_savings} грн'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully removed promotional prices from {expired_variants.count()} size variants'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Total savings lost: {total_savings} грн'
                )
            )

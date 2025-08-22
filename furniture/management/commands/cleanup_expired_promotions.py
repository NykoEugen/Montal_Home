from django.core.management.base import BaseCommand
from django.utils import timezone
from furniture.models import Furniture


class Command(BaseCommand):
    help = 'Remove promotional status from furniture items with expired sale timers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each item',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # Get current time
        now = timezone.now()
        
        # Find all promotional items with expired sale end dates
        expired_items = Furniture.objects.filter(
            is_promotional=True,
            sale_end_date__isnull=False,
            sale_end_date__lt=now
        )
        
        if not expired_items.exists():
            self.stdout.write(
                self.style.SUCCESS('No expired promotional items found.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Found {expired_items.count()} promotional items with expired sale timers:'
            )
        )
        
        total_savings = 0
        for item in expired_items:
            original_price = float(item.price)
            promotional_price = float(item.promotional_price) if item.promotional_price else original_price
            savings = original_price - promotional_price
            
            if verbose:
                self.stdout.write(
                    f'  - {item.name} (ID: {item.id})'
                )
                self.stdout.write(
                    f'    Sale ended: {item.sale_end_date.strftime("%Y-%m-%d %H:%M:%S")}'
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
                # Remove promotional status
                item.is_promotional = False
                item.promotional_price = None
                item.sale_end_date = None
                item.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Removed promotional status from: {item.name}'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would remove promotional status from {expired_items.count()} items'
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
                    f'\nSuccessfully removed promotional status from {expired_items.count()} items'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Total savings lost: {total_savings} грн'
                )
            )

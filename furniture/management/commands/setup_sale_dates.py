from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from furniture.models import Furniture


class Command(BaseCommand):
    help = 'Set up sale end dates for promotional furniture items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days from now to set as sale end date (default: 7)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Apply to all promotional items without sale end date'
        )
        parser.add_argument(
            '--item-id',
            type=int,
            help='Apply to specific item ID'
        )

    def handle(self, *args, **options):
        days = options['days']
        apply_to_all = options['all']
        item_id = options['item_id']
        
        sale_end_date = timezone.now() + timedelta(days=days)
        
        if item_id:
            # Apply to specific item
            try:
                item = Furniture.objects.get(id=item_id, is_promotional=True)
                item.sale_end_date = sale_end_date
                item.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Set sale end date for "{item.name}" to {sale_end_date.strftime("%Y-%m-%d %H:%M")}'
                    )
                )
            except Furniture.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Furniture item with ID {item_id} not found or not promotional')
                )
        elif apply_to_all:
            # Apply to all promotional items without sale end date
            items = Furniture.objects.filter(
                is_promotional=True,
                promotional_price__isnull=False,
                sale_end_date__isnull=True
            )
            
            updated_count = 0
            for item in items:
                item.sale_end_date = sale_end_date
                item.save()
                updated_count += 1
                self.stdout.write(
                    f'Set sale end date for "{item.name}" to {sale_end_date.strftime("%Y-%m-%d %H:%M")}'
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Updated {updated_count} promotional items')
            )
        else:
            # Show current promotional items
            items = Furniture.objects.filter(
                is_promotional=True,
                promotional_price__isnull=False
            )
            
            if not items.exists():
                self.stdout.write(self.style.WARNING('No promotional items found'))
                return
            
            self.stdout.write(self.style.SUCCESS('Current promotional items:'))
            for item in items:
                status = f"Ends: {item.sale_end_date.strftime('%Y-%m-%d %H:%M')}" if item.sale_end_date else "No end date"
                self.stdout.write(f'  {item.id}: {item.name} - {status}')
            
            self.stdout.write(
                self.style.WARNING(
                    '\nTo set sale end dates, use:\n'
                    f'  python manage.py setup_sale_dates --all --days {days}\n'
                    'Or for a specific item:\n'
                    '  python manage.py setup_sale_dates --item-id <ID> --days <DAYS>'
                )
            )

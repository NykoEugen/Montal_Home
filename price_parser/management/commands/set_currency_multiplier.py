from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig


class Command(BaseCommand):
    help = 'Set currency multiplier for configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            required=True,
            help='ID of the configuration'
        )
        parser.add_argument(
            '--multiplier',
            type=float,
            required=True,
            help='Currency multiplier (e.g., 38.5 for USD->UAH)'
        )
        parser.add_argument(
            '--currency-from',
            type=str,
            required=False,
            help='Source currency (e.g., USD, EUR)'
        )
        parser.add_argument(
            '--currency-to',
            type=str,
            required=False,
            help='Target currency (e.g., UAH)'
        )

    def handle(self, *args, **options):
        config_id = options['config_id']
        multiplier = options['multiplier']
        currency_from = options['currency_from']
        currency_to = options['currency_to']
        
        try:
            # Get configuration
            config = GoogleSheetConfig.objects.get(id=config_id)
            
            self.stdout.write(f"Configuration: {config.name}")
            self.stdout.write(f"Current multiplier: {config.price_multiplier}")
            
            # Update multiplier
            config.price_multiplier = multiplier
            config.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"Updated multiplier to: {multiplier}")
            )
            
            if currency_from and currency_to:
                self.stdout.write(f"Currency conversion: {currency_from} -> {currency_to}")
            
            # Show example conversion
            self.stdout.write("\nExample conversions:")
            self.stdout.write("-" * 40)
            test_prices = [10, 25, 50, 100, 250]
            for price in test_prices:
                converted = price * multiplier
                self.stdout.write(f"${price} -> {converted:.2f} UAH")
            
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Configuration with ID {config_id} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating multiplier: {str(e)}")
            ) 
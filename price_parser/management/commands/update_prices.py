from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from price_parser.models import GoogleSheetConfig
from price_parser.services import GoogleSheetsPriceUpdater


class Command(BaseCommand):
    help = 'Update furniture prices from Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            help='ID of specific GoogleSheetConfig to update'
        )
        parser.add_argument(
            '--config-name',
            type=str,
            help='Name of specific GoogleSheetConfig to update'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all active configurations'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test parsing without updating prices'
        )

    def handle(self, *args, **options):
        configs = []
        
        if options['config_id']:
            try:
                config = GoogleSheetConfig.objects.get(id=options['config_id'])
                configs.append(config)
            except GoogleSheetConfig.DoesNotExist:
                raise CommandError(f'Configuration with ID {options["config_id"]} not found')
        
        elif options['config_name']:
            try:
                config = GoogleSheetConfig.objects.get(name=options['config_name'])
                configs.append(config)
            except GoogleSheetConfig.DoesNotExist:
                raise CommandError(f'Configuration with name "{options["config_name"]}" not found')
        
        elif options['all']:
            configs = GoogleSheetConfig.objects.filter(is_active=True)
            if not configs:
                self.stdout.write(self.style.WARNING('No active configurations found'))
                return
        
        else:
            raise CommandError('Please specify --config-id, --config-name, or --all')
        
        total_processed = 0
        total_updated = 0
        
        for config in configs:
            self.stdout.write(f'Processing configuration: {config.name}')
            
            try:
                updater = GoogleSheetsPriceUpdater(config)
                
                if options['test']:
                    result = updater.test_parse()
                    if result['success']:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Test successful: {result["count"]} items found'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Test failed: {result["error"]}')
                        )
                else:
                    result = updater.update_prices()
                    if result['success']:
                        total_processed += result['processed_count']
                        total_updated += result['updated_count']
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated {result["updated_count"]} items from {result["processed_count"]} processed'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Update failed: {result["error"]}')
                        )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {config.name}: {str(e)}')
                )
        
        if not options['test'] and configs:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nTotal: {total_updated} items updated from {total_processed} processed'
                )
            ) 
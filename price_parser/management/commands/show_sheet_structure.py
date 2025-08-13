from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig
from price_parser.services import GoogleSheetsPriceUpdater


class Command(BaseCommand):
    help = 'Show Google Sheet structure to help identify cells'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            help='ID of specific configuration'
        )
        parser.add_argument(
            '--config-name',
            type=str,
            help='Name of specific configuration'
        )
        parser.add_argument(
            '--rows',
            type=int,
            default=20,
            help='Number of rows to show (default: 20)'
        )

    def handle(self, *args, **options):
        if options['config_id']:
            configs = GoogleSheetConfig.objects.filter(id=options['config_id'])
        elif options['config_name']:
            configs = GoogleSheetConfig.objects.filter(name=options['config_name'])
        else:
            configs = GoogleSheetConfig.objects.filter(is_active=True)
        
        for config in configs:
            self.stdout.write(f"\nAnalyzing configuration: {config.name}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write("=" * 80)
            
            try:
                updater = GoogleSheetsPriceUpdater(config)
                data = updater._fetch_sheet_data()
                
                if not data:
                    self.stdout.write("Could not fetch sheet data")
                    continue
                
                # Show the structure
                max_rows = min(options['rows'], len(data))
                self.stdout.write(f"\nShowing first {max_rows} rows:")
                self.stdout.write("-" * 80)
                
                for i, row in enumerate(data[:max_rows]):
                    self.stdout.write(f"Row {i+1:2d}: ", ending='')
                    for j, cell in enumerate(row[:15]):  # Show first 15 columns
                        col_letter = self._index_to_column(j)
                        cell_content = str(cell)[:20] if cell else ''
                        self.stdout.write(f"{col_letter}{i+1}={cell_content:20} ", ending='')
                    self.stdout.write("")
                
                # Show column headers
                if data:
                    self.stdout.write(f"\nColumn headers (Row 1):")
                    self.stdout.write("-" * 80)
                    for j, cell in enumerate(data[0][:15]):
                        col_letter = self._index_to_column(j)
                        self.stdout.write(f"{col_letter}: {cell}")
                
            except Exception as e:
                self.stdout.write(f"Error analyzing sheet: {str(e)}")
    
    def _index_to_column(self, index):
        """Convert index to Excel column letter."""
        result = ""
        while index >= 0:
            result = chr(65 + (index % 26)) + result
            index = index // 26 - 1
        return result 
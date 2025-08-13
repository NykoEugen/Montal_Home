from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig
from price_parser.services import GoogleSheetsPriceUpdater


class Command(BaseCommand):
    help = 'Test access to a specific sheet and show the data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            required=True,
            help='ID of the configuration'
        )
        parser.add_argument(
            '--rows',
            type=int,
            default=10,
            help='Number of rows to show (default: 10)'
        )

    def handle(self, *args, **options):
        try:
            config = GoogleSheetConfig.objects.get(id=options['config_id'])
            
            self.stdout.write(f"Configuration: {config.name}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write(f"Sheet Name: {config.sheet_name}")
            self.stdout.write("=" * 80)
            
            # Create updater and test access
            updater = GoogleSheetsPriceUpdater(config)
            
            # Get the GID being used
            gid = updater._get_sheet_gid()
            self.stdout.write(f"Using GID: {gid}")
            
            # Try to fetch data
            data = updater._fetch_sheet_data()
            
            if data:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully fetched data from sheet!")
                )
                self.stdout.write(f"Total rows: {len(data)}")
                
                # Show first few rows
                max_rows = min(options['rows'], len(data))
                self.stdout.write(f"\nFirst {max_rows} rows:")
                self.stdout.write("-" * 80)
                
                for i, row in enumerate(data[:max_rows]):
                    self.stdout.write(f"Row {i+1:2d}: {row[:10]}")  # Show first 10 columns
                
                # Show column headers if available
                if data:
                    self.stdout.write(f"\nColumn headers (Row 1):")
                    self.stdout.write("-" * 80)
                    for j, cell in enumerate(data[0][:10]):  # Show first 10 columns
                        col_letter = self._index_to_column(j)
                        self.stdout.write(f"{col_letter}: {cell}")
                
            else:
                self.stdout.write(
                    self.style.ERROR("Failed to fetch data from sheet")
                )
                
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Configuration with ID {options['config_id']} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            )
    
    def _index_to_column(self, index):
        """Convert index to Excel column letter."""
        result = ""
        while index >= 0:
            result = chr(65 + (index % 26)) + result
            index = index // 26 - 1
        return result 
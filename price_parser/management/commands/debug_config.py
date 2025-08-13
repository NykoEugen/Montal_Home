from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig


class Command(BaseCommand):
    help = 'Debug Google Sheet configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            help='ID of specific configuration to debug'
        )

    def handle(self, *args, **options):
        if options['config_id']:
            configs = GoogleSheetConfig.objects.filter(id=options['config_id'])
        else:
            configs = GoogleSheetConfig.objects.all()
        
        for config in configs:
            self.stdout.write(f"\nConfiguration: {config.name}")
            self.stdout.write(f"ID: {config.id}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write(f"Sheet name: {config.sheet_name} (type: {type(config.sheet_name)})")
            self.stdout.write(f"Price multiplier: {config.price_multiplier}")
            self.stdout.write(f"Is active: {config.is_active}")
            
            # Test sheet access
            try:
                from price_parser.services import GoogleSheetsPriceUpdater
                updater = GoogleSheetsPriceUpdater(config)
                gid = updater._get_sheet_gid()
                self.stdout.write(f"Sheet GID: {gid}")
            except Exception as e:
                self.stdout.write(f"Error getting sheet GID: {e}")
    
    def extract_column_letter(self, col):
        """Extract column letter from dictionary or string."""
        if isinstance(col, dict):
            # Extract the first value from the dictionary
            return list(col.values())[0]
        elif isinstance(col, str):
            return col
        else:
            raise ValueError(f"Invalid column format: {col}")
    
    def _column_to_index(self, column: str) -> int:
        """Convert Excel column letter to index (A=0, B=1, etc.)."""
        # Ensure column is a string
        if not isinstance(column, str):
            raise ValueError(f"Column must be a string, got {type(column)}: {column}")
        
        result = 0
        for char in column.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1 
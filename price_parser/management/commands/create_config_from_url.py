from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig
import re


class Command(BaseCommand):
    help = 'Create a new GoogleSheetConfig from a Google Sheets URL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            required=True,
            help='Google Sheets URL'
        )
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Configuration name'
        )
        parser.add_argument(
            '--sheet-name',
            type=str,
            required=True,
            help='Sheet/tab name'
        )
        parser.add_argument(
            '--active',
            action='store_true',
            help='Make the configuration active'
        )

    def handle(self, *args, **options):
        url = options['url']
        name = options['name']
        sheet_name = options['sheet_name']
        is_active = options['active']
        
        self.stdout.write(f"Creating configuration from URL: {url}")
        self.stdout.write("=" * 80)
        
        # Extract sheet ID
        sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not sheet_id_match:
            self.stdout.write(
                self.style.ERROR("Could not extract sheet ID from URL")
            )
            return
        
        sheet_id = sheet_id_match.group(1)
        
        # Extract GID
        gid_match = re.search(r'#gid=(\d+)', url)
        sheet_gid = gid_match.group(1) if gid_match else None
        
        # Create the configuration
        try:
            config = GoogleSheetConfig.objects.create(
                name=name,
                sheet_url=url,
                sheet_id=sheet_id,
                sheet_name=sheet_name,
                sheet_gid=sheet_gid,
                is_active=is_active
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created configuration: {config.name}")
            )
            self.stdout.write(f"ID: {config.id}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write(f"Sheet Name: {config.sheet_name}")
            self.stdout.write(f"Sheet GID: {config.sheet_gid or 'Default (0)'}")
            self.stdout.write(f"Active: {config.is_active}")
            
            # Test the configuration
            self.stdout.write("\nTesting configuration...")
            from price_parser.services import GoogleSheetsPriceUpdater
            updater = GoogleSheetsPriceUpdater(config)
            
            # Test sheet access
            data = updater._fetch_sheet_data()
            if data:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Sheet access successful! Found {len(data)} rows")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("⚠ Could not fetch data from sheet")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating configuration: {str(e)}")
            ) 
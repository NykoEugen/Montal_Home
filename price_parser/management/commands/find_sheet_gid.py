from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig


class Command(BaseCommand):
    help = 'Find the correct GID for different sheets in Google Sheets'

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

    def handle(self, *args, **options):
        if options['config_id']:
            configs = GoogleSheetConfig.objects.filter(id=options['config_id'])
        elif options['config_name']:
            configs = GoogleSheetConfig.objects.filter(name=options['config_name'])
        else:
            configs = GoogleSheetConfig.objects.filter(is_active=True)
        
        for config in configs:
            self.stdout.write(f"\nConfiguration: {config.name}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write(f"Current Sheet Name: {config.sheet_name}")
            self.stdout.write("=" * 80)
            
            self.stdout.write("\nTo find the correct GID for different sheets:")
            self.stdout.write("1. Open your Google Sheet in browser")
            self.stdout.write("2. Look at the URL when you click on different tabs")
            self.stdout.write("3. The URL will look like:")
            self.stdout.write("   https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=GID_NUMBER")
            self.stdout.write("4. The number after 'gid=' is the GID you need")
            
            self.stdout.write("\nCommon GIDs:")
            self.stdout.write("- First sheet (Sheet1): gid=0")
            self.stdout.write("- Second sheet (Sheet2): gid=1234567890 (varies)")
            self.stdout.write("- Third sheet (Sheet3): gid=1234567891 (varies)")
            
            self.stdout.write(f"\nCurrent sheet URL:")
            self.stdout.write(f"https://docs.google.com/spreadsheets/d/{config.sheet_id}/edit#gid=0")
            
            self.stdout.write("\nTo update the sheet name and GID:")
            self.stdout.write("1. Go to admin panel: /admin/price_parser/googlesheetconfig/")
            self.stdout.write("2. Edit the configuration")
            self.stdout.write("3. Update 'Sheet Name' field")
            self.stdout.write("4. The system will try to find the correct GID automatically") 
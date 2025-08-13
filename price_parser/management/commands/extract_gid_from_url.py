from django.core.management.base import BaseCommand
import re


class Command(BaseCommand):
    help = 'Extract GID from Google Sheets URL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            required=True,
            help='Google Sheets URL'
        )

    def handle(self, *args, **options):
        url = options['url']
        
        self.stdout.write(f"URL: {url}")
        self.stdout.write("=" * 80)
        
        # Extract sheet ID
        sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if sheet_id_match:
            sheet_id = sheet_id_match.group(1)
            self.stdout.write(f"Sheet ID: {sheet_id}")
        else:
            self.stdout.write(
                self.style.ERROR("Could not extract sheet ID from URL")
            )
            return
        
        # Extract GID
        gid_match = re.search(r'#gid=(\d+)', url)
        if gid_match:
            gid = gid_match.group(1)
            self.stdout.write(f"GID: {gid}")
        else:
            self.stdout.write(
                self.style.WARNING("No GID found in URL (using default gid=0)")
            )
            gid = '0'
        
        # Show the configuration fields
        self.stdout.write("\nConfiguration fields:")
        self.stdout.write("-" * 80)
        self.stdout.write(f"Sheet URL: {url}")
        self.stdout.write(f"Sheet ID: {sheet_id}")
        self.stdout.write(f"Sheet GID: {gid}")
        
        # Show example admin configuration
        self.stdout.write("\nAdmin Panel Configuration:")
        self.stdout.write("-" * 80)
        self.stdout.write("Name: [Enter a descriptive name]")
        self.stdout.write(f"Sheet URL: {url}")
        self.stdout.write(f"Sheet ID: {sheet_id}")
        self.stdout.write("Sheet Name: [Enter the sheet/tab name]")
        self.stdout.write(f"Sheet GID: {gid}")
        self.stdout.write("Is Active: ✓")
        
        # Show CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        self.stdout.write(f"\nCSV Export URL:")
        self.stdout.write(f"{csv_url}") 
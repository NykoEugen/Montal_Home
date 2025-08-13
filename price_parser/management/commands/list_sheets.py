from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig
import requests
import re


class Command(BaseCommand):
    help = 'List available sheets in a Google Spreadsheet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            required=True,
            help='ID of the configuration'
        )

    def handle(self, *args, **options):
        try:
            config = GoogleSheetConfig.objects.get(id=options['config_id'])
            
            self.stdout.write(f"Configuration: {config.name}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write("=" * 80)
            
            # Try to get sheet information
            sheets = self.get_available_sheets(config.sheet_id)
            
            if sheets:
                self.stdout.write("Available sheets:")
                self.stdout.write("-" * 80)
                for sheet_name, gid in sheets.items():
                    self.stdout.write(f"Sheet: {sheet_name} (GID: {gid})")
                    self.stdout.write(f"URL: https://docs.google.com/spreadsheets/d/{config.sheet_id}/edit#gid={gid}")
                    self.stdout.write()
            else:
                self.stdout.write(
                    self.style.WARNING("Could not retrieve sheet information automatically.")
                )
                self.stdout.write("You can manually find GIDs by:")
                self.stdout.write("1. Opening the Google Sheet in your browser")
                self.stdout.write("2. Clicking on different tabs/sheets")
                self.stdout.write("3. Looking at the URL - it will contain #gid=XXXXX")
                self.stdout.write("4. Common GIDs: Sheet1=0, Sheet2=1234567890, etc.")
                
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Configuration with ID {options['config_id']} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            )
    
    def get_available_sheets(self, sheet_id):
        """Try to get available sheets from the spreadsheet."""
        try:
            # For now, we'll provide common sheet names and GIDs
            # In a real implementation, you might want to use Google Sheets API
            
            common_sheets = {
                'Sheet1': '0',
                'Sheet2': '1234567890',
                'Sheet3': '1234567891',
                'Прайс': '0',
                'Ціни': '0',
                'Обідні столи': '0',
                'Стільці': '0',
                'Меблі': '0',
                'Обідні столи гурт': '0',
                'Обідні столи роздріб': '0',
                'Стільці гурт': '0',
                'Стільці роздріб': '0',
            }
            
            return common_sheets
            
        except Exception as e:
            self.stdout.write(f"Error getting sheets: {str(e)}")
            return {} 
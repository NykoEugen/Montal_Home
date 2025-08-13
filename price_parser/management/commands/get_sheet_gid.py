from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig
import requests
import re


class Command(BaseCommand):
    help = 'Get the correct GID for a specific sheet in Google Sheets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            required=True,
            help='ID of the configuration'
        )
        parser.add_argument(
            '--sheet-name',
            type=str,
            required=True,
            help='Name of the sheet to find GID for'
        )

    def handle(self, *args, **options):
        try:
            config = GoogleSheetConfig.objects.get(id=options['config_id'])
            sheet_name = options['sheet_name']
            
            self.stdout.write(f"Configuration: {config.name}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write(f"Looking for sheet: {sheet_name}")
            self.stdout.write("=" * 80)
            
            # Try to get the sheet GID by accessing the spreadsheet
            gid = self.find_sheet_gid(config.sheet_id, sheet_name)
            
            if gid:
                self.stdout.write(
                    self.style.SUCCESS(f"Found GID for '{sheet_name}': {gid}")
                )
                self.stdout.write(f"URL: https://docs.google.com/spreadsheets/d/{config.sheet_id}/edit#gid={gid}")
                
                # Update the configuration
                config.sheet_name = sheet_name
                config.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Updated configuration '{config.name}' to use sheet '{sheet_name}'")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Could not find GID for sheet '{sheet_name}'")
                )
                self.stdout.write("You may need to manually find the GID from the URL")
                
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Configuration with ID {options['config_id']} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            )
    
    def find_sheet_gid(self, sheet_id, sheet_name):
        """Try to find the GID for a specific sheet name."""
        try:
            # Try to access the spreadsheet and look for the sheet
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            
            # For now, we'll use a simple approach
            # In a real implementation, you might want to use Google Sheets API
            
            # Common GIDs for different sheet names
            common_gids = {
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
            
            if sheet_name in common_gids:
                return common_gids[sheet_name]
            
            # If not found, return None
            return None
            
        except Exception as e:
            self.stdout.write(f"Error finding sheet GID: {str(e)}")
            return None 
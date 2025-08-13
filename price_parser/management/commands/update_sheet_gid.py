from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig


class Command(BaseCommand):
    help = 'Update the GID mapping for a specific sheet'

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
            help='Name of the sheet'
        )
        parser.add_argument(
            '--gid',
            type=str,
            required=True,
            help='GID for the sheet'
        )

    def handle(self, *args, **options):
        try:
            config = GoogleSheetConfig.objects.get(id=options['config_id'])
            sheet_name = options['sheet_name']
            gid = options['gid']
            
            self.stdout.write(f"Configuration: {config.name}")
            self.stdout.write(f"Sheet ID: {config.sheet_id}")
            self.stdout.write(f"Updating sheet '{sheet_name}' to use GID: {gid}")
            self.stdout.write("=" * 80)
            
            # Update the configuration to use this sheet
            config.sheet_name = sheet_name
            config.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"Updated configuration to use sheet '{sheet_name}'")
            )
            
            # Now we need to update the GID mapping in the service
            # For now, we'll just inform the user
            self.stdout.write(
                self.style.WARNING("Note: You may need to update the GID mapping in the code.")
            )
            self.stdout.write(f"Add this mapping to the _get_sheet_gid method:")
            self.stdout.write(f"'{sheet_name}': '{gid}',")
            
            # Test the sheet access
            from price_parser.services import GoogleSheetsPriceUpdater
            updater = GoogleSheetsPriceUpdater(config)
            
            # Temporarily override the GID for testing
            original_gids = {
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
            
            # Add the new mapping
            original_gids[sheet_name] = gid
            
            # Test with the new GID
            try:
                # We'll manually test the URL
                test_url = f"https://docs.google.com/spreadsheets/d/{config.sheet_id}/export?format=csv&gid={gid}"
                self.stdout.write(f"Testing URL: {test_url}")
                
                import requests
                response = requests.get(test_url)
                if response.status_code == 200:
                    self.stdout.write(
                        self.style.SUCCESS("Sheet access successful!")
                    )
                    # Show first few lines
                    lines = response.text.split('\n')[:5]
                    self.stdout.write("First 5 lines:")
                    for i, line in enumerate(lines):
                        self.stdout.write(f"{i+1}: {line[:100]}...")
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to access sheet. Status: {response.status_code}")
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error testing sheet access: {str(e)}")
                )
                
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Configuration with ID {options['config_id']} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            ) 
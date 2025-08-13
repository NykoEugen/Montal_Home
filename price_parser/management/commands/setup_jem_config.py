from django.core.management.base import BaseCommand
from django.db import transaction
from price_parser.models import GoogleSheetConfig, FurniturePriceMapping
from furniture.models import Furniture


class Command(BaseCommand):
    help = 'Setup initial configuration for Jem company Google Sheet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing configuration'
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            # Check if configuration already exists
            existing_config = GoogleSheetConfig.objects.filter(
                name="Компанія Джем - Прайс"
            ).first()
            
            if existing_config and not options['force']:
                self.stdout.write(
                    self.style.WARNING(
                        'Configuration already exists. Use --force to recreate.'
                    )
                )
                return
            
            if existing_config and options['force']:
                self.stdout.write('Removing existing configuration...')
                existing_config.delete()
            
            # Create new configuration
            config = GoogleSheetConfig.objects.create(
                name="Компанія Джем - Прайс",
                sheet_url="https://docs.google.com/spreadsheets/d/11CBbJs-KCGknFYlIguwSOz-1zveyJTx7EWBLJ48m1ek/edit?gid=0#gid=0",
                furniture_name_column="A",  # Колонка з назвами меблів
                size_columns=["B", "C"],    # Колонки з розмірами (Довжина, Ширина)
                price_columns=["E", "F"],   # Колонки з цінами (Стільниця стандарт, HPL покриття)
                start_row=4,                # Початок даних з 4-го рядка
                is_active=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created configuration: {config.name}')
            )
            
            # Create furniture mappings
            self.create_furniture_mappings(config)
            
            self.stdout.write(
                self.style.SUCCESS('Setup completed successfully!')
            )
    
    def create_furniture_mappings(self, config):
        """Create furniture name mappings."""
        
            # Define mappings based on the sheet structure
    mappings = [
        {"sheet_name": "Maxi -1", "furniture_name": "Maxi-1"},
        {"sheet_name": "Maxi -2", "furniture_name": "Maxi-2"},
        {"sheet_name": "Boston", "furniture_name": "Boston"},
        {"sheet_name": "Boston А", "furniture_name": "Boston А"},  # Cyrillic А
        {"sheet_name": "Boston A", "furniture_name": "Boston А"},  # Latin A as fallback
        {"sheet_name": "Chester", "furniture_name": "Chester"},
        {"sheet_name": "Slim", "furniture_name": "Slim"},
        {"sheet_name": "Kirk", "furniture_name": "Kirk"},
    ]
        
        created_count = 0
        for mapping_data in mappings:
            # Try to find furniture by name
            furniture = Furniture.objects.filter(
                name__icontains=mapping_data["furniture_name"]
            ).first()
            
            if furniture:
                # Create mapping
                mapping, created = FurniturePriceMapping.objects.get_or_create(
                    sheet_name=mapping_data["sheet_name"],
                    config=config,
                    defaults={
                        "furniture": furniture,
                        "is_active": True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        f'Created mapping: {mapping_data["sheet_name"]} -> {furniture.name}'
                    )
                else:
                    self.stdout.write(
                        f'Mapping already exists: {mapping_data["sheet_name"]} -> {furniture.name}'
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Furniture not found: {mapping_data["furniture_name"]}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} furniture mappings')
        ) 
from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig, FurniturePriceCellMapping
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'Create cell mappings for XLSX files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config-id',
            type=int,
            required=True,
            help='ID of the configuration'
        )
        parser.add_argument(
            '--furniture-id',
            type=int,
            required=True,
            help='Furniture ID'
        )
        parser.add_argument(
            '--row',
            type=int,
            required=True,
            help='Sheet row number'
        )
        parser.add_argument(
            '--column',
            type=str,
            required=True,
            help='Sheet column (A, B, C, etc.)'
        )
        parser.add_argument(
            '--price-type',
            type=str,
            required=True,
            help='Type of price (e.g., "Ціна опт", "Ціна РРЦ")'
        )
        parser.add_argument(
            '--size-variant-id',
            type=int,
            required=False,
            help='Size variant ID (optional)'
        )

    def handle(self, *args, **options):
        config_id = options['config_id']
        furniture_id = options['furniture_id']
        row = options['row']
        column = options['column']
        price_type = options['price_type']
        size_variant_id = options['size_variant_id']
        
        try:
            # Get configuration
            config = GoogleSheetConfig.objects.get(id=config_id)
            self.stdout.write(f"Configuration: {config.name}")
            
            # Get furniture
            furniture = Furniture.objects.get(id=furniture_id)
            self.stdout.write(f"Furniture: {furniture.name}")
            
            # Get size variant if provided
            size_variant = None
            if size_variant_id:
                size_variant = FurnitureSizeVariant.objects.get(id=size_variant_id)
                self.stdout.write(f"Size Variant: {size_variant.name}")
            
            # Create mapping
            mapping = FurniturePriceCellMapping.objects.create(
                furniture=furniture,
                config=config,
                sheet_row=row,
                sheet_column=column.upper(),
                price_type=price_type,
                size_variant=size_variant,
                is_active=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created mapping ID: {mapping.id}")
            )
            self.stdout.write(f"Furniture: {furniture.name}")
            if size_variant:
                self.stdout.write(f"Size: {size_variant.name}")
            self.stdout.write(f"Cell: {column.upper()}{row}")
            self.stdout.write(f"Price Type: {price_type}")
            
            # Test the mapping
            self.stdout.write("\nTesting mapping...")
            from price_parser.services import GoogleSheetsPriceUpdater
            updater = GoogleSheetsPriceUpdater(config)
            
            # Get data
            data = updater._fetch_sheet_data()
            if data and row <= len(data) and len(data[row-1]) > 0:
                col_index = updater._column_to_index(column.upper())
                if col_index < len(data[row-1]):
                    cell_value = data[row-1][col_index]
                    self.stdout.write(f"Cell value: {cell_value}")
                    
                    # Try to parse price
                    price = updater._parse_price(cell_value)
                    if price:
                        self.stdout.write(
                            self.style.SUCCESS(f"Parsed price: {price}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Could not parse price from: {cell_value}")
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Column {column} is out of range")
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Row {row} is out of range or empty")
                )
                
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Configuration with ID {config_id} not found")
            )
        except Furniture.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Furniture with ID {furniture_id} not found")
            )
        except FurnitureSizeVariant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Size variant with ID {size_variant_id} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating mapping: {str(e)}")
            ) 
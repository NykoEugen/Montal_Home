from django.core.management.base import BaseCommand
from price_parser.models import GoogleSheetConfig, FurniturePriceCellMapping
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'Create direct cell mapping for furniture price'

    def add_arguments(self, parser):
        parser.add_argument(
            '--furniture-id',
            type=int,
            required=True,
            help='ID of the furniture item'
        )
        parser.add_argument(
            '--config-id',
            type=int,
            required=True,
            help='ID of the Google Sheet configuration'
        )
        parser.add_argument(
            '--row',
            type=int,
            required=True,
            help='Row number in the Google Sheet'
        )
        parser.add_argument(
            '--column',
            type=str,
            required=True,
            help='Column letter in the Google Sheet (e.g., E, F, G)'
        )
        parser.add_argument(
            '--price-type',
            type=str,
            required=True,
            help='Type of price (e.g., "Стільниця стандарт", "HPL покриття")'
        )
        parser.add_argument(
            '--size-variant-id',
            type=int,
            help='ID of size variant (optional)'
        )

    def handle(self, *args, **options):
        try:
            # Get furniture
            furniture = Furniture.objects.get(id=options['furniture_id'])
            self.stdout.write(f"Furniture: {furniture.name}")
            
            # Get config
            config = GoogleSheetConfig.objects.get(id=options['config_id'])
            self.stdout.write(f"Config: {config.name}")
            
            # Get size variant if provided
            size_variant = None
            if options['size_variant_id']:
                size_variant = FurnitureSizeVariant.objects.get(id=options['size_variant_id'])
                self.stdout.write(f"Size variant: {size_variant}")
            
            # Create mapping
            mapping, created = FurniturePriceCellMapping.objects.get_or_create(
                furniture=furniture,
                config=config,
                sheet_row=options['row'],
                sheet_column=options['column'].upper(),
                defaults={
                    'price_type': options['price_type'],
                    'size_variant': size_variant,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created mapping: {furniture.name} -> {mapping.cell_reference} ({options['price_type']})"
                    )
                )
            else:
                # Update existing mapping
                mapping.price_type = options['price_type']
                mapping.size_variant = size_variant
                mapping.is_active = True
                mapping.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated mapping: {furniture.name} -> {mapping.cell_reference} ({options['price_type']})"
                    )
                )
                
        except Furniture.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Furniture with ID {options['furniture_id']} not found")
            )
        except GoogleSheetConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Config with ID {options['config_id']} not found")
            )
        except FurnitureSizeVariant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Size variant with ID {options['size_variant_id']} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {str(e)}")
            ) 
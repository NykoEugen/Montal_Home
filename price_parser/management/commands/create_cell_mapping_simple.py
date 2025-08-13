from django.core.management.base import BaseCommand
from price_parser.models import FurniturePriceCellMapping
from furniture.models import Furniture, FurnitureSizeVariant


class Command(BaseCommand):
    help = 'Create a simple cell mapping for furniture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--furniture-id',
            type=int,
            required=True,
            help='Furniture ID'
        )
        parser.add_argument(
            '--size-variant-id',
            type=int,
            required=False,
            help='Size variant ID (optional)'
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

    def handle(self, *args, **options):
        furniture_id = options['furniture_id']
        size_variant_id = options['size_variant_id']
        row = options['row']
        column = options['column']
        
        try:
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
                size_variant=size_variant,
                sheet_row=row,
                sheet_column=column.upper(),
                is_active=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created mapping ID: {mapping.id}")
            )
            self.stdout.write(f"Furniture: {furniture.name}")
            if size_variant:
                self.stdout.write(f"Size: {size_variant.name}")
            self.stdout.write(f"Cell: {column.upper()}{row}")
            
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
import re
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional
from django.utils import timezone
from django.db import transaction

from .models import GoogleSheetConfig, PriceUpdateLog, FurniturePriceCellMapping
from furniture.models import Furniture, FurnitureSizeVariant

logger = logging.getLogger(__name__)


class GoogleSheetsPriceUpdater:
    """Service for updating furniture prices from Google Sheets."""
    
    def __init__(self, config: GoogleSheetConfig):
        self.config = config
        self.log = None
    
    def test_parse(self) -> Dict:
        """Test fetching sheet data without updating prices."""
        try:
            data = self._fetch_sheet_data()
            if not data:
                return {'success': False, 'error': 'Не вдалося отримати дані з таблиці'}
            
            # Count active cell mappings
            cell_mappings_count = FurniturePriceCellMapping.objects.filter(
                config=self.config,
                is_active=True
            ).count()
            
            return {
                'success': True,
                'data': data[:10],  # Return first 10 rows for preview
                'count': cell_mappings_count,
                'message': f'Sheet loaded successfully. Found {cell_mappings_count} active cell mappings.'
            }
        except Exception as e:
            logger.error(f"Error testing sheet access for config {self.config.name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_prices(self) -> Dict:
        """Update furniture prices from Google Sheets using direct cell mappings."""
        start_time = timezone.now()
        
        # Create log entry
        self.log = PriceUpdateLog.objects.create(
            config=self.config,
            status='success',
            started_at=start_time
        )
        
        try:
            # Fetch data from Google Sheets
            data = self._fetch_sheet_data()
            if not data:
                self._update_log_error("Не вдалося отримати дані з таблиці")
                return {'success': False, 'error': 'Не вдалося отримати дані з таблиці'}
            
            # Update prices using direct cell mappings only
            updated_count = self._update_prices_from_cell_mappings(data)
            
            # Update log
            self.log.items_processed = updated_count
            self.log.items_updated = updated_count
            self.log.completed_at = timezone.now()
            self.log.log_details = f"Оновлено {updated_count} товарів з прямих комірок"
            self.log.save()
            
            return {
                'success': True,
                'updated_count': updated_count
            }
            
        except Exception as e:
            error_msg = f"Помилка оновлення цін: {str(e)}"
            logger.error(error_msg)
            self._update_log_error(error_msg)
            return {'success': False, 'error': str(e)}
    
    def _fetch_sheet_data(self) -> Optional[List[List]]:
        """Fetch data from Google Sheets using the sheet ID and sheet name."""
        try:
            import requests
            
            # Use CSV export with specific sheet name
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.config.sheet_id}/export?format=csv&gid={self._get_sheet_gid()}"
            
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV data
            import csv
            from io import StringIO
            
            csv_data = StringIO(response.text)
            reader = csv.reader(csv_data)
            return list(reader)
            
        except Exception as e:
            logger.error(f"Error fetching sheet data: {str(e)}")
            return None
    
    def _get_sheet_gid(self) -> str:
        """Get the GID (Google ID) for the specific sheet."""
        try:
            # First, try to use the GID from the database
            if self.config.sheet_gid:
                logger.info(f"Using GID {self.config.sheet_gid} from database for sheet '{self.config.sheet_name}'")
                return self.config.sheet_gid
            
            # Fallback to common GIDs for different sheet names
            common_gids = {
                'Sheet1': '0',
                'Sheet2': '1234567890',
                'Sheet3': '1234567891',
                'Прайс': '0',  # Default to first sheet
                'Ціни': '0',   # Default to first sheet
                'Обідні столи': '0',
                'Стільці': '0',
                'Меблі': '0',
                'Обідні столи гурт': '1927896544',  # The sheet you're currently viewing
                'Обідні столи роздріб': '0',
                'Стільці гурт': '0',
                'Стільці роздріб': '0',
            }
            
            # Try to get from common mappings
            if self.config.sheet_name in common_gids:
                gid = common_gids[self.config.sheet_name]
                logger.info(f"Using GID {gid} for sheet '{self.config.sheet_name}' from common mappings")
                return gid
            
            # If not found, default to first sheet (gid=0)
            logger.warning(f"Sheet name '{self.config.sheet_name}' not found in common GIDs, using default (gid=0)")
            return '0'
            
        except Exception as e:
            logger.error(f"Error getting sheet GID: {str(e)}")
            return '0'  # Default to first sheet
    

    
    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """Parse price string into Decimal."""
        try:
            # Remove common non-numeric characters
            cleaned = re.sub(r'[^\d.,]', '', price_str)
            if ',' in cleaned and '.' in cleaned:
                # Handle European format (1.234,56)
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Handle comma as decimal separator
                cleaned = cleaned.replace(',', '.')
            
            return Decimal(cleaned)
        except (ValueError, InvalidOperation):
            return None
    
    def _column_to_index(self, column: str) -> int:
        """Convert Excel column letter to index (A=0, B=1, etc.)."""
        # Ensure column is a string
        if not isinstance(column, str):
            raise ValueError(f"Column must be a string, got {type(column)}: {column}")
        
        result = 0
        for char in column.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1
    
    def _update_prices_from_cell_mappings(self, data: List[List]) -> int:
        """Update prices using direct cell mappings."""
        updated_count = 0
        
        # Get all active cell mappings for this config
        cell_mappings = FurniturePriceCellMapping.objects.filter(
            config=self.config,
            is_active=True
        ).select_related('furniture', 'size_variant')
        
        for mapping in cell_mappings:
            try:
                # Convert column letter to index
                col_idx = self._column_to_index(mapping.sheet_column)
                row_idx = mapping.sheet_row - 1  # Convert to 0-based index
                
                # Check if row and column exist in data
                if row_idx < len(data) and col_idx < len(data[row_idx]):
                    price_str = data[row_idx][col_idx].strip()
                    if price_str:
                        price = self._parse_price(price_str)
                        if price:
                            # Update the price
                            if mapping.size_variant:
                                # Update size variant price
                                mapping.size_variant.price = price
                                mapping.size_variant.save()
                                updated_count += 1
                                logger.info(f"Updated size variant price for {mapping.furniture.name}: {price}")
                            else:
                                # Update main furniture price
                                mapping.furniture.price = price
                                mapping.furniture.save()
                                updated_count += 1
                                logger.info(f"Updated furniture price for {mapping.furniture.name}: {price}")
                        else:
                            self.log.errors.append({
                                'cell': mapping.cell_reference,
                                'furniture_name': mapping.furniture.name,
                                'error': f'Не вдалося розібрати ціну: {price_str}'
                            })
                    else:
                        self.log.errors.append({
                            'cell': mapping.cell_reference,
                            'furniture_name': mapping.furniture.name,
                            'error': 'Комірка порожня'
                        })
                else:
                    self.log.errors.append({
                        'cell': mapping.cell_reference,
                        'furniture_name': mapping.furniture.name,
                        'error': f'Комірка не існує (рядок {mapping.sheet_row}, колонка {mapping.sheet_column})'
                    })
                    
            except Exception as e:
                self.log.errors.append({
                    'cell': mapping.cell_reference,
                    'furniture_name': mapping.furniture.name,
                    'error': str(e)
                })
        
        return updated_count
    
    def _update_log_error(self, error_msg: str):
        """Update log with error information."""
        if self.log:
            self.log.status = 'error'
            self.log.completed_at = timezone.now()
            self.log.errors.append({'error': error_msg})
            self.log.save() 
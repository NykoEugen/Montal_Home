import re
import json
import logging
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from typing import Dict, List, Optional, Tuple

import csv
import requests
from django.db import transaction
from django.utils import timezone

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
            updated_count, processed_count = self._update_prices_from_cell_mappings(data)
            
            # Update log
            self.log.items_processed = processed_count
            self.log.items_updated = updated_count
            self.log.completed_at = timezone.now()
            self.log.log_details = f"Оновлено {updated_count} товарів з {processed_count} комірок"
            self.log.save()
            
            return {
                'success': True,
                'updated_count': updated_count,
                'processed_count': processed_count,
            }
            
        except Exception as e:
            error_msg = f"Помилка оновлення цін: {str(e)}"
            logger.error(error_msg)
            self._update_log_error(error_msg)
            return {'success': False, 'error': str(e)}
    
    def _fetch_sheet_data(self) -> Optional[List[List]]:
        """Fetch data from Google Sheets or XLSX file."""
        try:
            if self.config.xlsx_file:
                # Handle XLSX file
                return self._fetch_xlsx_data()
            else:
                # Handle Google Sheets
                return self._fetch_google_sheets_data()
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return None
    
    def _fetch_google_sheets_data(self) -> Optional[List[List]]:
        """Fetch data from Google Sheets using CSV export with GViz fallback."""
        last_error: Optional[Exception] = None

        try:
            return self._fetch_google_sheets_via_export()
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Standard sheet export failed for config %s: %s",
                self.config.name,
                exc,
            )

        try:
            return self._fetch_google_sheets_via_xlsx_export()
        except Exception as exc:
            last_error = exc
            logger.warning(
                "XLSX export fallback failed for config %s: %s",
                self.config.name,
                exc,
            )

        try:
            data = self._fetch_google_sheets_via_gviz()
            if data:
                logger.info(
                    "GViz fallback succeeded for config %s",
                    self.config.name,
                )
            return data
        except Exception as exc:
            last_error = exc
            logger.error(
                "GViz fallback failed for config %s: %s",
                self.config.name,
                exc,
            )

        if last_error:
            raise last_error
        return None

    def _fetch_google_sheets_via_export(self) -> List[List]:
        """Fetch sheet data via the export CSV endpoint."""
        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{self.config.sheet_id}/export"
            f"?format=csv&gid={self._get_sheet_gid()}"
        )
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        return list(csv.reader(csv_data))

    def _fetch_google_sheets_via_gviz(self) -> List[List]:
        """Fetch sheet data via the GViz endpoint (works when export is blocked)."""
        base_url = f"https://docs.google.com/spreadsheets/d/{self.config.sheet_id}/gviz/tq"
        params: Dict[str, str] = {"tqx": "out:csv"}

        if self.config.sheet_gid:
            params["gid"] = self.config.sheet_gid
        elif self.config.sheet_name:
            params["sheet"] = self.config.sheet_name
        else:
            params["gid"] = self._get_sheet_gid()

        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        return list(csv.reader(csv_data))

    def _fetch_google_sheets_via_xlsx_export(self) -> List[List]:
        """Download the Google Sheet as XLSX and return matrix data."""
        from openpyxl import load_workbook  # Imported lazily

        url = f"https://docs.google.com/spreadsheets/d/{self.config.sheet_id}/export?format=xlsx&id={self.config.sheet_id}"
        params: Dict[str, str] = {}
        if self.config.sheet_gid:
            params["gid"] = self.config.sheet_gid

        response = requests.get(url, params=params or None, timeout=60)
        response.raise_for_status()

        workbook = load_workbook(BytesIO(response.content), data_only=True)

        if self.config.sheet_name and self.config.sheet_name in workbook.sheetnames:
            worksheet = workbook[self.config.sheet_name]
        else:
            worksheet = workbook.active

        return self._worksheet_to_data(worksheet)

    def _fetch_xlsx_data(self) -> Optional[List[List]]:
        """Fetch data from XLSX file."""
        try:
            from openpyxl import load_workbook
        except ImportError:
            logger.error("openpyxl is not installed. Please install it with: pip install openpyxl")
            return None

        try:
            workbook = load_workbook(self.config.xlsx_file.path, data_only=True)
            if self.config.sheet_name and self.config.sheet_name in workbook.sheetnames:
                worksheet = workbook[self.config.sheet_name]
            else:
                worksheet = workbook.active
            return self._worksheet_to_data(worksheet)
        except Exception as e:
            logger.error(f"Error fetching XLSX data: {str(e)}")
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

    def _worksheet_to_data(self, worksheet) -> List[List[str]]:
        """Convert an openpyxl worksheet to a list of lists."""
        data: List[List[str]] = []
        for row in worksheet.iter_rows(values_only=True):
            row_data: List[str] = []
            for cell_value in row:
                if cell_value is None:
                    row_data.append("")
                else:
                    row_data.append(str(cell_value))
            data.append(row_data)
        return data

    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """Parse price string into Decimal and apply multiplier."""
        try:
            # Remove common non-numeric characters
            cleaned = re.sub(r'[^\d.,]', '', price_str)
            if ',' in cleaned and '.' in cleaned:
                # Handle European format (1.234,56)
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Handle comma as decimal separator
                cleaned = cleaned.replace(',', '.')
            
            price = Decimal(cleaned)
            
            # Apply multiplier if it's not 1.0
            if self.config.price_multiplier != Decimal('1.0'):
                price = price * self.config.price_multiplier
                logger.info(f"Applied multiplier {self.config.price_multiplier} to price {cleaned} -> {price}")
            
            return price
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
    
    def _update_prices_from_cell_mappings(self, data: List[List]) -> Tuple[int, int]:
        """Update prices using direct cell mappings."""
        updated_count = 0
        
        # Get all active cell mappings for this config
        cell_mappings = list(
            FurniturePriceCellMapping.objects.filter(
            config=self.config,
            is_active=True
        ).select_related('furniture', 'size_variant')
        )
        processed_count = len(cell_mappings)
        
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
        
        return updated_count, processed_count
    
    def _update_log_error(self, error_msg: str):
        """Update log with error information."""
        if self.log:
            self.log.status = 'error'
            self.log.completed_at = timezone.now()
            self.log.errors.append({'error': error_msg})
            self.log.save() 

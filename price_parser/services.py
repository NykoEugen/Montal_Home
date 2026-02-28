import re
import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from typing import Dict, List, Optional, Tuple

import csv
import requests
from django.utils import timezone

from .models import (
    GoogleSheetConfig,
    PriceUpdateLog,
    FurniturePriceCellMapping,
    SupplierFeedConfig,
    SupplierFeedUpdateLog,
)
from furniture.models import Furniture, FurnitureSizeVariant

logger = logging.getLogger(__name__)

DEFAULT_FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
}


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


@dataclass
class SupplierOffer:
    offer_id: str
    name: str
    name_ua: Optional[str]
    description: Optional[str]
    description_ua: Optional[str]
    model: Optional[str]
    price: Decimal
    old_price: Optional[Decimal]


class SupplierFeedPriceUpdater:
    """Service responsible for parsing supplier XML feeds (Matrolux etc.)."""

    def __init__(self, config: SupplierFeedConfig):
        self.config = config
        self.log: Optional[SupplierFeedUpdateLog] = None
        self._furniture_index: Optional[Dict[str, Dict]] = None

    def test_parse(self) -> Dict:
        """Preview first offers without applying changes."""
        try:
            offers = self._fetch_offers()
        except Exception as exc:  # pragma: no cover - network faults
            logger.error("Supplier feed test failed for %s: %s", self.config.name, exc)
            return {'success': False, 'error': str(exc)}

        preview = [
            {
                'offer_id': offer.offer_id,
                'name': offer.name,
                'model': offer.model,
                'price': str(offer.price),
                'old_price': str(offer.old_price) if offer.old_price else None,
            }
            for offer in offers[:10]
        ]
        return {
            'success': True,
            'offers_total': len(offers),
            'preview': preview,
        }

    def update_prices(self) -> Dict:
        if not self.config.is_active:
            return {'success': False, 'error': 'Конфігурація неактивна'}

        self.log = SupplierFeedUpdateLog.objects.create(
            config=self.config,
            status='success',
            started_at=timezone.now(),
        )

        try:
            offers = self._fetch_offers()
            if not offers:
                self._finalize_log(errors=[{'error': 'Фід не містить пропозицій'}])
                return {'success': False, 'error': 'Фід не містить пропозицій'}

            offers_processed = len(offers)
            items_matched = 0
            items_updated = 0
            errors: List[Dict[str, str]] = []
            seen_furniture: set[int] = set()

            for offer in offers:
                try:
                    furniture = self._match_offer_to_furniture(offer)
                except Exception as exc:  # Defensive to log unexpected parsing issues
                    errors.append({
                        'offer_id': offer.offer_id,
                        'name': offer.name,
                        'error': f'Помилка підбору товару: {exc}'
                    })
                    continue

                if not furniture:
                    errors.append({
                        'offer_id': offer.offer_id,
                        'name': offer.name,
                        'model': offer.model,
                        'name_ua': offer.name_ua,
                        'article_candidates': self._article_candidates(offer.model) if offer.model else [],
                        'error': 'Не знайдено відповідний товар'
                    })
                    continue

                items_matched += 1

                if furniture.pk in seen_furniture:
                    # Avoid double updates for дублікати offerів на один товар
                    continue

                try:
                    changed = self._apply_offer_prices(furniture, offer)
                except Exception as exc:
                    errors.append({
                        'offer_id': offer.offer_id,
                        'name': offer.name,
                        'model': offer.model,
                        'error': f'Не вдалося оновити ціну: {exc}'
                    })
                    continue

                seen_furniture.add(furniture.pk)
                if changed:
                    items_updated += 1

            self._finalize_log(
                offers_processed=offers_processed,
                items_matched=items_matched,
                items_updated=items_updated,
                errors=errors,
            )

            success = not errors or items_updated > 0
            return {
                'success': success,
                'offers_processed': offers_processed,
                'items_matched': items_matched,
                'items_updated': items_updated,
                'errors': errors,
            }

        except Exception as exc:
            logger.exception("Supplier feed update failed for %s", self.config.name)
            self._finalize_log(errors=[{'error': str(exc)}], force_status='error')
            return {'success': False, 'error': str(exc)}

    # --- Internal helpers -------------------------------------------------

    def _fetch_offers(self) -> List[SupplierOffer]:
        response = requests.get(
            self.config.feed_url,
            headers=DEFAULT_FEED_HEADERS,
            timeout=60,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)

        offers: List[SupplierOffer] = []
        for offer_el in root.findall('.//offer'):
            model_text = (
                (offer_el.findtext('model') or '')
                or (offer_el.findtext('article') or '')
                or (offer_el.findtext('vendorCode') or '')
            ).strip()
            price = self._parse_decimal(offer_el.findtext('price'))
            if price is None:
                continue
            # support multiple tag spellings for old price
            old_price = self._parse_decimal(
                offer_el.findtext('oldprice')
                or offer_el.findtext('old_price')
                or offer_el.findtext('old-price')
                or offer_el.findtext('old price')
            )
            name_ua = (offer_el.findtext('name_ua') or '').strip() or None
            description = (offer_el.findtext('description') or '').strip() or None
            description_ua = (offer_el.findtext('description_ua') or '').strip() or None
            offer = SupplierOffer(
                offer_id=offer_el.get('id') or model_text or (offer_el.findtext('name') or '').strip() or 'unknown',
                name=(offer_el.findtext('name') or '').strip(),
                name_ua=name_ua,
                description=description,
                description_ua=description_ua,
                model=model_text or None,
                price=price,
                old_price=old_price,
            )
            offers.append(offer)
        return offers

    def _parse_decimal(self, value: Optional[str]) -> Optional[Decimal]:
        if not value:
            return None
        cleaned = re.sub(r'[^0-9,.-]', '', value)
        if not cleaned:
            return None
        if cleaned.count(',') == 1 and cleaned.count('.') == 0:
            cleaned = cleaned.replace(',', '.')
        elif cleaned.count(',') > 0 and cleaned.count('.') > 0:
            cleaned = cleaned.replace('.', '').replace(',', '.')
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _match_offer_to_furniture(self, offer: SupplierOffer) -> Optional[Furniture]:
        index = self._get_furniture_index()

        if self.config.match_by_article and offer.model:
            candidates = self._article_candidates(offer.model)
            for candidate in candidates:
                furniture = index['article'].get(candidate)
                if furniture:
                    return furniture
            # Soft prefix match: allow base code to match colored variants
            article_index = index['article']
            for candidate in candidates:
                matches = {
                    furniture
                    for key, furniture in article_index.items()
                    if key.startswith(candidate) or candidate.startswith(key)
                }
                if len(matches) == 1:
                    return next(iter(matches))

        if not (self.config.match_by_name and offer.name_ua):
            return None

        name_sources: List[str] = []
        # Prefer UA name, but if порожнє — використати name як запасний варіант
        if offer.name_ua:
            name_sources.append(offer.name_ua)
        elif offer.name:
            name_sources.append(offer.name)

        offer_variants: List[str] = []
        for raw in name_sources:
            offer_variants.extend(self._generate_name_variants(raw))

        candidates = self._collect_name_matches(offer_variants)
        if len(candidates) == 1:
            return candidates[0]

        # Fallback: partial contains search across index
        partial_candidates: List[Furniture] = []
        name_index = index['names']
        for variant in offer_variants:
            if not variant:
                continue
            for stored_name, furnitures in name_index.items():
                if variant in stored_name or stored_name in variant:
                    partial_candidates.extend(furnitures)
        unique_partial = self._deduplicate(partial_candidates)
        if len(unique_partial) == 1:
            return unique_partial[0]

        # Fallback 2: token-overlap similarity (helps UA/RU wording differences)
        best_match = self._find_best_token_overlap(offer_variants, name_index)
        if best_match:
            return best_match

        # Fallback 3: use description text (UA preferred)
        description_variants: List[str] = []
        if offer.description_ua:
            description_variants.append(self._normalize_name(offer.description_ua))
        elif offer.description:
            description_variants.append(self._normalize_name(offer.description))

        best_match_desc = self._find_best_token_overlap(description_variants, name_index)
        if best_match_desc:
            return best_match_desc
        return None

    def _collect_name_matches(self, offer_variants: List[str]) -> List[Furniture]:
        index = self._get_furniture_index()['names']
        matches: List[Furniture] = []
        for variant in offer_variants:
            if not variant:
                continue
            matches.extend(index.get(variant, []))
        return self._deduplicate(matches)

    def _deduplicate(self, items: List[Furniture]) -> List[Furniture]:
        seen: set[int] = set()
        unique: List[Furniture] = []
        for furniture in items:
            pk = furniture.pk
            if pk and pk not in seen:
                seen.add(pk)
                unique.append(furniture)
        return unique

    def _generate_name_variants(self, raw_name: str) -> List[str]:
        variants = [raw_name]
        split_parts = re.split(r'[\\/|,:;()+\-]+', raw_name)
        variants.extend(split_parts)
        normalized = [self._normalize_name(part) for part in variants if part]
        # Remove duplicates while preserving order
        seen: set[str] = set()
        result: List[str] = []
        for value in normalized:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _normalize_name(self, value: str) -> str:
        value = value.lower()
        value = value.replace('ё', 'е').replace('ї', 'і').replace('є', 'е').replace('ґ', 'г')
        value = re.sub(r'[^a-z0-9а-яіїєґ ]+', ' ', value)
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    def _normalize_article_code(self, value: str) -> str:
        value = value.lower().strip()
        # Remove any non-alphanumeric chars to align vendor formats:
        # "R-63-black/ black" -> "r63blackblack"
        return re.sub(r'[^a-z0-9]+', '', value)

    def _article_candidates(self, raw: str) -> List[str]:
        """Generate multiple article variants to bridge color/texture suffixes."""
        candidates: List[str] = []
        norm_full = self._normalize_article_code(raw)
        if norm_full:
            candidates.append(norm_full)

        # Split by common separators and take prefixes
        tokens = [t for t in re.split(r'[^a-z0-9]+', raw.lower()) if t]
        if tokens:
            for length in (1, 2, 3):
                base = ''.join(tokens[:length])
                if base:
                    candidates.append(base)

        # Before first slash/hyphen segment
        slash_split = re.split(r'[\\/]', raw)
        if slash_split:
            first = slash_split[0]
            norm_first = self._normalize_article_code(first)
            if norm_first:
                candidates.append(norm_first)

        # Deduplicate preserving order
        seen: set[str] = set()
        result: List[str] = []
        for cand in candidates:
            if cand and cand not in seen:
                seen.add(cand)
                result.append(cand)
        return result

    def _find_best_token_overlap(
        self,
        offer_variants: List[str],
        name_index: Dict[str, List[Furniture]],
    ) -> Optional[Furniture]:
        """Pick the best match by token overlap to bridge ru/ua wording differences."""
        best_furniture: Optional[Furniture] = None
        best_score: float = 0.0
        ambiguous = False

        for variant in offer_variants:
            tokens_variant = variant.split()
            if not tokens_variant:
                continue
            set_variant = set(tokens_variant)

            for stored_name, furnitures in name_index.items():
                tokens_stored = stored_name.split()
                if not tokens_stored:
                    continue
                set_stored = set(tokens_stored)
                overlap = len(set_variant & set_stored)
                score = overlap / max(len(set_variant), len(set_stored))

                if overlap < 2 or score < 0.6:
                    continue

                for furniture in furnitures:
                    if score > best_score:
                        best_furniture = furniture
                        best_score = score
                        ambiguous = False
                    elif score == best_score:
                        ambiguous = True

        if ambiguous:
            return None
        return best_furniture

    def _get_furniture_index(self) -> Dict[str, Dict]:
        if self._furniture_index is not None:
            return self._furniture_index

        article_index: Dict[str, Furniture] = {}
        name_index: Dict[str, List[Furniture]] = {}
        furnitures = Furniture.objects.all().only('id', 'name', 'article_code', 'price', 'promotional_price', 'is_promotional')
        for furniture in furnitures:
            if furniture.article_code:
                raw_key = furniture.article_code.strip().lower()
                norm_key = self._normalize_article_code(raw_key)
                article_index[raw_key] = furniture
                article_index[norm_key] = furniture
            for variant in self._generate_name_variants(furniture.name):
                if not variant:
                    continue
                name_index.setdefault(variant, []).append(furniture)
        self._furniture_index = {'article': article_index, 'names': name_index}
        return self._furniture_index

    def _apply_offer_prices(self, furniture: Furniture, offer: SupplierOffer) -> bool:
        base_price, promo_price = self._resolve_prices(offer)
        if base_price is None:
            raise ValueError('Не вдалося визначити ціну')

        updated_fields: List[str] = []
        changed = False

        if furniture.price != base_price:
            furniture.price = base_price
            updated_fields.append('price')
            changed = True

        if promo_price is not None:
            if (furniture.promotional_price != promo_price) or (not furniture.is_promotional):
                furniture.promotional_price = promo_price
                furniture.is_promotional = True
                updated_fields.extend(['promotional_price', 'is_promotional'])
                changed = True
        else:
            if furniture.is_promotional or furniture.promotional_price is not None:
                furniture.is_promotional = False
                furniture.promotional_price = None
                updated_fields.extend(['is_promotional', 'promotional_price'])
                changed = True

        if changed:
            furniture.save(update_fields=list(dict.fromkeys(updated_fields)))

        return changed

    def _resolve_prices(self, offer: SupplierOffer) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        price = self._apply_multiplier(offer.price)
        old_price = self._apply_multiplier(offer.old_price) if offer.old_price is not None else None
        if price is None:
            return None, None
        if old_price is not None and old_price > 0:
            return old_price, price
        return price, None

    def _apply_multiplier(self, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        multiplier = self.config.price_multiplier or Decimal('1')
        try:
            result = value * multiplier
        except (TypeError, InvalidOperation):
            result = value
        return result.quantize(Decimal('0.01'))

    def _finalize_log(
        self,
        offers_processed: int = 0,
        items_matched: int = 0,
        items_updated: int = 0,
        errors: Optional[List[Dict]] = None,
        force_status: Optional[str] = None,
    ) -> None:
        if not self.log:
            return

        errors = errors or []
        status = force_status or ('success' if not errors else ('partial' if items_updated or items_matched else 'error'))
        self.log.status = status
        self.log.offers_processed = offers_processed
        self.log.items_matched = items_matched
        self.log.items_updated = items_updated
        self.log.errors = errors
        self.log.completed_at = timezone.now()
        self.log.log_details = (
            f"Матчів: {items_matched}, оновлено: {items_updated}, "
            f"помилок: {len(errors)}"
        )
        self.log.save()

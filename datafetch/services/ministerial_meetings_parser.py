"""
GOV.UK Ministerial Meetings Parser

Parses ministerial transparency publications (CSV and XLSX formats) from GOV.UK.
Handles column name variations across departments and date format inconsistencies.

Phase 2: CSV and XLSX parsing support
"""

import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MinisterialMeetingsParser:
    """Parse GOV.UK ministerial meetings CSV files."""

    # Column name variations across departments
    # GOV.UK departments use inconsistent column naming - these mappings handle all variants
    COLUMN_MAPPINGS = {
        'minister': [
            'Minister',
            'minister',
            'Minister Name',
            'Ministerial Name',
            'Name of Minister',
            'Official',
        ],
        'date': [
            'Date',
            'date',
            'Date of Meeting',
            'Meeting Date',
            'Date of meeting',
        ],
        'external_actor': [
            'Name of Individual or Organisation',
            'Name of organisation or individual',  # Case variation
            'Name of Organisation',  # Older format (pre-2014)
            'Name of External Organisation',  # Another older variation
            'External Party',
            'Organisation/Individual',
            'Organisation / Individual',
            'Name',
            'Individual/Organisation',
            'Individual / Organisation',
            'External attendee(s)',
            'External Attendees',
            'Attendees (External Organisation)',  # Some departments use this
        ],
        'purpose': [
            'Purpose of Meeting',
            'Purpose',
            'Subject',
            'Details',
            'Purpose of meeting',
            'Meeting Purpose',
        ],
    }

    def parse_csv(self, filepath: str, year: int = None) -> List[Dict]:
        """
        Parse CSV with auto-detection of columns and dates.

        Args:
            filepath: Path to CSV file
            year: Optional year for month-only dates (e.g., "April" -> April of this year)

        Returns:
            List of dicts: [
                {
                    'minister': str,
                    'date': datetime.date,
                    'external_actor': str,
                    'purpose': str
                },
                ...
            ]
        """
        self._context_year = year  # Store for use in date parsing
        # Try multiple encodings (GOV.UK files vary)
        content = None
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.debug(f"Successfully read file with encoding: {encoding}")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            raise ValueError(f"Could not read file {filepath} with any known encoding")

        # Parse CSV
        lines = content.splitlines()
        reader = csv.DictReader(lines)

        # Auto-detect columns
        column_map = self._detect_columns(reader.fieldnames)

        if not column_map:
            logger.error(f"Could not detect required columns in {filepath}")
            logger.error(f"Available columns: {reader.fieldnames}")
            return []

        # Log detected columns for debugging
        logger.info(f"Detected columns: {column_map}")

        # Parse rows
        meetings = []
        skipped_rows = 0

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            try:
                # Extract fields using detected columns
                minister = row.get(column_map.get('minister', ''), '').strip() if column_map.get('minister') else ''
                external_actor = row.get(column_map.get('external_actor', ''), '').strip() if column_map.get('external_actor') else ''
                date_str = row.get(column_map.get('date', ''), '').strip() if column_map.get('date') else ''
                purpose = row.get(column_map.get('purpose', ''), '').strip() if column_map.get('purpose') else ''

                # Parse date
                meeting_date = self._parse_date(date_str)

                # Validate required fields
                if not minister or not external_actor or not meeting_date:
                    if minister or external_actor or date_str:  # Only log if row has some data
                        logger.debug(
                            f"Row {row_num}: Skipping incomplete record - "
                            f"minister='{minister}', actor='{external_actor}', date='{date_str}'"
                        )
                    skipped_rows += 1
                    continue

                # Clean up common data quality issues
                if external_actor.lower() in ['n/a', 'none', 'nil', '-', '']:
                    skipped_rows += 1
                    continue

                meetings.append({
                    'minister': minister,
                    'date': meeting_date,
                    'external_actor': external_actor,
                    'purpose': purpose,
                })

            except (KeyError, ValueError, AttributeError) as e:
                logger.warning(f"Row {row_num}: Error parsing row - {e}")
                skipped_rows += 1
                continue

        logger.info(f"Parsed {len(meetings)} meetings ({skipped_rows} rows skipped)")
        return meetings

    def _detect_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """
        Auto-detect column names using COLUMN_MAPPINGS.

        Args:
            fieldnames: CSV column headers

        Returns:
            Dict mapping standard field names to actual column names
        """
        if not fieldnames:
            return {}

        column_map = {}

        # Strip BOM and whitespace from fieldnames
        cleaned_fieldnames = {
            fieldname: fieldname.lstrip('\ufeff').strip()
            for fieldname in fieldnames
        }

        for standard_key, variations in self.COLUMN_MAPPINGS.items():
            for fieldname in fieldnames:
                # Check both original and cleaned fieldname
                cleaned = cleaned_fieldnames.get(fieldname, fieldname)
                if fieldname in variations or cleaned in variations:
                    column_map[standard_key] = fieldname
                    break

        # Handle edge case 1: older GOV.UK files (2010-2016) have blank first column
        # containing minister name, e.g.: [blank], Date, Name of Organisation, Purpose
        # If we have external_actor and date but not minister, AND the first column is blank,
        # treat the first column as the minister column
        if 'minister' not in column_map and 'external_actor' in column_map and 'date' in column_map:
            first_col = fieldnames[0] if fieldnames else ''
            first_col_cleaned = cleaned_fieldnames.get(first_col, first_col)
            if first_col_cleaned == '' or first_col_cleaned.isspace():
                column_map['minister'] = first_col
                logger.info(f"Detected blank first column as minister column (older GOV.UK format)")

        # Handle edge case 2: some files have "Name" for minister AND
        # "Name of organisation or individual" for external actor
        # If "Name" was mapped to external_actor but we also have a more specific external actor column,
        # re-map "Name" to minister
        if 'minister' not in column_map and 'external_actor' in column_map:
            external_col = column_map['external_actor']
            external_col_cleaned = cleaned_fieldnames.get(external_col, external_col).lower()

            # If external_actor is just "Name" but there's a more specific column available
            if external_col_cleaned == 'name':
                # Look for a more specific external actor column
                specific_external_patterns = [
                    'name of organisation',
                    'name of individual',
                    'organisation or individual',
                    'external attendee',
                ]
                for fieldname in fieldnames:
                    cleaned = cleaned_fieldnames.get(fieldname, fieldname).lower()
                    if any(pattern in cleaned for pattern in specific_external_patterns):
                        # Found a more specific column - use "Name" as minister instead
                        column_map['minister'] = external_col
                        column_map['external_actor'] = fieldname
                        logger.info(f"Re-mapped 'Name' to minister, using '{fieldname}' for external actor")

        # Require at minimum: minister, date, external_actor
        required_fields = ['minister', 'date', 'external_actor']
        if not all(field in column_map for field in required_fields):
            logger.warning(f"Missing required fields. Found: {list(column_map.keys())}")
            logger.warning(f"Available columns: {fieldnames}")

        return column_map

    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """
        Parse date with multiple format support.

        GOV.UK publications use inconsistent date formats across departments
        and even within the same department over time.

        Args:
            date_str: Date string in various formats

        Returns:
            datetime.date object or None if parsing fails
        """
        if not date_str or date_str.strip() == '':
            return None

        date_str = date_str.strip()

        # Try common formats in order of likelihood
        formats = [
            '%Y-%m-%d',      # 2024-01-15 (ISO format)
            '%d/%m/%Y',      # 15/01/2024 (UK format - most common)
            '%d/%m/%y',      # 15/01/24 (UK short year)
            '%d-%m-%Y',      # 15-01-2024
            '%d.%m.%Y',      # 15.01.2024
            '%d %B %Y',      # 15 January 2024
            '%d %b %Y',      # 15 Jan 2024
            '%B %d, %Y',     # January 15, 2024 (US format - rare)
            '%b %d, %Y',     # Jan 15, 2024
            '%Y/%m/%d',      # 2024/01/15
            '%d-%b-%Y',      # 15-Jan-2024
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try month-year formats (use 1st of month for older GOV.UK files)
        month_year_formats = [
            '%B %Y',         # April 2011
            '%b %Y',         # Apr 2011
            '%B %y',         # April 11
            '%b %y',         # Apr 11
        ]

        for fmt in month_year_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # Use 1st of month as the date
                return parsed.replace(day=1).date()
            except ValueError:
                continue

        # Try month-only formats (use context year if provided, otherwise current year)
        month_only_formats = [
            '%B',            # April
            '%b',            # Apr
        ]

        context_year = getattr(self, '_context_year', None) or datetime.now().year
        for fmt in month_only_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # Use 1st of month with context year
                return parsed.replace(year=context_year, day=1).date()
            except ValueError:
                continue

        # If all formats fail, log and return None
        logger.debug(f"Could not parse date: '{date_str}'")
        return None

    def validate_file(self, filepath: str) -> tuple[bool, str]:
        """
        Validate a CSV file before parsing.

        Args:
            filepath: Path to CSV file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # Read first 1KB

            # Check if file is empty
            if not content.strip():
                return False, "File is empty"

            # Try to parse as CSV
            lines = content.splitlines()
            reader = csv.DictReader(lines)

            # Check if we can detect columns
            column_map = self._detect_columns(reader.fieldnames)
            required_fields = ['minister', 'date', 'external_actor']

            missing_fields = [f for f in required_fields if f not in column_map]
            if missing_fields:
                return False, f"Missing required columns: {', '.join(missing_fields)}"

            return True, "Valid"

        except Exception as e:
            return False, str(e)

    def parse_xlsx(self, filepath: str, year: int = None) -> List[Dict]:
        """
        Parse XLSX file (pre-April 2024 format used by many departments).

        Args:
            filepath: Path to XLSX file
            year: Optional year for month-only dates

        Returns:
            List of dicts with same structure as parse_csv()
        """
        self._context_year = year  # Store for use in date parsing

        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ImportError(
                "openpyxl is required for XLSX parsing. "
                "Install with: pip install openpyxl"
            )

        logger.info(f"Parsing XLSX file: {filepath}")

        # Load workbook (read-only for performance)
        wb = load_workbook(filepath, read_only=True, data_only=True)

        # Find "Meetings" sheet or use first sheet
        if 'Meetings' in wb.sheetnames:
            ws = wb['Meetings']
            logger.debug("Using 'Meetings' sheet")
        elif 'meetings' in wb.sheetnames:
            ws = wb['meetings']
            logger.debug("Using 'meetings' sheet")
        else:
            ws = wb.active
            logger.debug(f"Using default sheet: {ws.title}")

        # Find header row (may not be first row due to title rows, etc.)
        header_row = None
        headers = None

        for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if not row:
                continue

            # Check if this row looks like a header
            # (contains 'Minister' or 'Date' or similar keywords)
            row_text = ' '.join([str(cell) for cell in row if cell])

            if any(keyword in row_text for keyword in ['Minister', 'Date', 'Meeting', 'Organisation']):
                header_row = idx
                headers = [str(cell).strip() if cell else '' for cell in row]
                logger.debug(f"Found header row at line {idx}: {headers}")
                break

        if not header_row:
            logger.error("Cannot find header row in XLSX file")
            return []

        # Auto-detect columns
        column_map = self._detect_columns(headers)

        if not column_map:
            logger.error(f"Could not detect required columns")
            logger.error(f"Available columns: {headers}")
            return []

        logger.info(f"Detected columns: {column_map}")

        # Get column indices for faster access
        column_indices = {
            key: headers.index(col_name)
            for key, col_name in column_map.items()
        }

        # Parse data rows
        meetings = []
        skipped_rows = 0

        for row_num, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue  # Skip empty rows

            try:
                # Extract fields using column indices
                minister = str(row[column_indices['minister']]).strip() if column_indices.get('minister') is not None and row[column_indices['minister']] else ''
                external_actor = str(row[column_indices['external_actor']]).strip() if column_indices.get('external_actor') is not None and row[column_indices['external_actor']] else ''
                date_value = row[column_indices['date']] if column_indices.get('date') is not None else None
                purpose = str(row[column_indices.get('purpose', 0)]).strip() if column_indices.get('purpose') is not None and len(row) > column_indices.get('purpose', 0) and row[column_indices.get('purpose', 0)] else ''

                # Parse date (handles both Excel dates and string dates)
                meeting_date = self._parse_date_xlsx(date_value)

                # Validate required fields
                if not minister or not external_actor or not meeting_date:
                    if minister or external_actor or date_value:
                        logger.debug(
                            f"Row {row_num}: Skipping incomplete record - "
                            f"minister='{minister}', actor='{external_actor}', date='{date_value}'"
                        )
                    skipped_rows += 1
                    continue

                # Clean up common data quality issues
                if external_actor.lower() in ['n/a', 'none', 'nil', '-', '']:
                    skipped_rows += 1
                    continue

                meetings.append({
                    'minister': minister,
                    'date': meeting_date,
                    'external_actor': external_actor,
                    'purpose': purpose,
                })

            except (IndexError, ValueError, AttributeError) as e:
                logger.warning(f"Row {row_num}: Error parsing row - {e}")
                skipped_rows += 1
                continue

        wb.close()

        logger.info(f"Parsed {len(meetings)} meetings ({skipped_rows} rows skipped)")
        return meetings

    def _parse_date_xlsx(self, date_value) -> Optional[datetime.date]:
        """
        Parse date from XLSX cell (handles Excel serial dates and strings).

        Args:
            date_value: Cell value (can be datetime, int, float, or string)

        Returns:
            datetime.date object or None if parsing fails
        """
        if date_value is None:
            return None

        # If already a datetime.date or datetime.datetime, use it
        if isinstance(date_value, datetime):
            return date_value.date()
        elif hasattr(date_value, 'date'):
            return date_value.date()

        # If string, use existing string parser
        if isinstance(date_value, str):
            return self._parse_date(date_value)

        # If number, treat as Excel serial date
        if isinstance(date_value, (int, float)):
            try:
                # Excel serial date: days since 1899-12-30
                # (Excel has a leap year bug for 1900, but we're post-2010 so it doesn't affect us)
                base_date = datetime(1899, 12, 30)
                return (base_date + timedelta(days=date_value)).date()
            except (ValueError, OverflowError):
                logger.debug(f"Could not parse Excel date: {date_value}")
                return None

        logger.debug(f"Unknown date type: {type(date_value)} - {date_value}")
        return None

    def parse_file(self, filepath: str, year: int = None) -> List[Dict]:
        """
        Auto-detect file type and parse accordingly.

        Args:
            filepath: Path to CSV or XLSX file
            year: Optional year for month-only dates (extracted from quarter like "2016-Q2")

        Returns:
            List of meeting dicts
        """
        if filepath.lower().endswith('.xlsx') or filepath.lower().endswith('.xls'):
            return self.parse_xlsx(filepath, year=year)
        else:
            return self.parse_csv(filepath, year=year)

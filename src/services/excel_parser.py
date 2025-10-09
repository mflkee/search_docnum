import re
from datetime import datetime
from typing import Optional

import pandas as pd

from src.models.excel_data import ExcelRegistryData
from src.utils.date_utils import parse_verification_date
from src.utils.logging_config import app_logger
from src.utils.validators import validate_certificate_format_detailed


class ExcelParserService:
    """
    Service for parsing Excel files with specific requirements for Arshin registry synchronization.
    By default searches for columns named "Дата поверки" and
    "Наличие документа с отметкой о поверке (№ св-ва о поверке)" but can also
    work with explicit Excel references (e.g., AE, AI).
    """

    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls']
        self.verification_date_aliases = [
            "дата поверки",
            "verification date",
        ]
        self.certificate_number_aliases = [
            "наличие документа с отметкой о поверке (№ св-ва о поверке)",
            "номер свидетельства о поверке",
            "номер свидетельства",
            "certificate number",
        ]
        self.valid_until_aliases = [
            "действительна до",
            "дата окончания поверки",
            "срок действия",
            "valid until",
            "valid_to",
            "valid date",
            "окончание поверки",
        ]

    def _find_sheet_by_name(self, available_sheets, target_sheet_name):
        """
        Find a sheet that matches the target sheet name (case-insensitive, partial match).

        Args:
            available_sheets: List of available sheet names in the Excel file
            target_sheet_name: Target sheet name to find

        Returns:
            Found sheet name or None if not found
        """
        app_logger.info(f"Looking for sheet: '{target_sheet_name}' in available sheets: {available_sheets}")
        
        # Prioritize exact matches for the default "Перечень" sheet
        if target_sheet_name.lower() in ["перечень", "perechen"]:
            for sheet in available_sheets:
                if sheet.lower() in ['перечень', 'perechen', 'reestr', 'реестр']:
                    app_logger.info(f"Found priority match for Перечень sheet: '{sheet}'")
                    return sheet

        # Try exact match first
        for sheet in available_sheets:
            if sheet.lower() == target_sheet_name.lower():
                app_logger.info(f"Found exact match: '{sheet}'")
                return sheet

        # Try partial match
        for sheet in available_sheets:
            if target_sheet_name.lower() in sheet.lower() or sheet.lower() in target_sheet_name.lower():
                app_logger.info(f"Found partial match: '{sheet}'")
                return sheet

        # Try common variations of "Перечень" (higher priority)
        if target_sheet_name.lower() in ["перечень", "perечень", "perechen", "list", "список", "reestr", "реестр"]:
            common_variations = ["перечень", "reestr", "реестр", "list", "список", "perechen", "main"]
            for variation in common_variations:
                for sheet in available_sheets:
                    if variation.lower().replace('ё', 'е') in sheet.lower().replace('ё', 'е'):  # Handle ё/е variations
                        app_logger.info(f"Found common variation match: '{sheet}'")
                        return sheet

        app_logger.warning(f"Could not find sheet matching: '{target_sheet_name}', available sheets: {available_sheets}")
        return None

    @staticmethod
    def _normalize_header(value: str) -> str:
        """
        Normalize column headers for comparison (lowercase, collapse spaces, replace ё->е).
        """
        if value is None:
            return ""
        normalized = str(value).strip().lower()
        normalized = normalized.replace('ё', 'е')
        normalized = normalized.replace('\n', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    @staticmethod
    def _excel_ref_to_index(reference: str) -> Optional[int]:
        """
        Convert Excel column reference (e.g. 'AE') to zero-based index.
        """
        if not reference:
            return None

        if not re.fullmatch(r'[A-Za-z]+', reference.strip()):
            return None

        ref = reference.strip().upper()
        index = 0
        for char in ref:
            index = index * 26 + (ord(char) - ord('A') + 1)
        return index - 1

    def _find_column_index(
        self,
        df: pd.DataFrame,
        identifier: Optional[str],
        aliases: list[str],
        keyword_groups: list[list[str]],
    ) -> Optional[int]:
        """
        Locate column index using provided identifier, alias list and keyword fallbacks.
        """
        normalized_columns = [self._normalize_header(col) for col in df.columns]

        # 1. Exact match by provided identifier
        if identifier:
            normalized_identifier = self._normalize_header(identifier)
            if normalized_identifier:
                for idx, column_name in enumerate(normalized_columns):
                    if column_name == normalized_identifier:
                        return idx

        # 2. Exact match by aliases (in order of priority)
        for alias in aliases:
            normalized_alias = self._normalize_header(alias)
            if not normalized_alias:
                continue
            for idx, column_name in enumerate(normalized_columns):
                if column_name == normalized_alias:
                    return idx

        # 3. Partial match using identifier tokens
        if identifier:
            normalized_identifier = self._normalize_header(identifier)
            if normalized_identifier:
                tokens = [token for token in normalized_identifier.split(' ') if token]
                if tokens:
                    for idx, column_name in enumerate(normalized_columns):
                        if all(token in column_name for token in tokens):
                            return idx

        # 4. Keyword fallbacks (first match wins)
        for keyword_group in keyword_groups:
            normalized_group = [self._normalize_header(keyword) for keyword in keyword_group if keyword]
            if not normalized_group:
                continue
            for idx, column_name in enumerate(normalized_columns):
                if all(keyword in column_name for keyword in normalized_group):
                    return idx

        return None

    def parse_excel_file(self, file_path: str, verification_date_column: str = "Дата поверки", certificate_number_column: str = "Наличие документа с отметкой о поверке (№ св-ва о поверке)", sheet_name: str = "Перечень") -> list[ExcelRegistryData]:
        """
        Parse an Excel file to extract verification data.

        Args:
            file_path: Path to the Excel file to parse
            verification_date_column: Column header or Excel reference for verification date (e.g., 'Дата поверки' or 'AE')
            certificate_number_column: Column header or Excel reference for certificate number (e.g., 'Наличие документа с отметкой о поверке (№ св-ва о поверке)' or 'AI')
            sheet_name: Name of the sheet to parse (default 'Перечень')

        Returns:
            List of ExcelRegistryData objects

        Raises:
            ValueError: If file format is unsupported or parsing fails
        """
        # Read the Excel file using pandas
        try:
            # Determine if it's .xls or .xlsx to use the appropriate engine
            if file_path.lower().endswith('.xls'):
                # For .xls files, try to read the specified sheet, fall back to first sheet
                try:
                    df = pd.read_excel(file_path, engine='xlrd', sheet_name=sheet_name)
                except ValueError:
                    # If the specified sheet doesn't exist, try first sheet
                    xl_file = pd.ExcelFile(file_path, engine='xlrd')
                    available_sheets = xl_file.sheet_names
                    # Try to find sheet by searching for "Перечень" or similar in available sheets
                    found_sheet = self._find_sheet_by_name(available_sheets, sheet_name)
                    if found_sheet:
                        df = pd.read_excel(file_path, engine='xlrd', sheet_name=found_sheet)
                    else:
                        df = pd.read_excel(file_path, engine='xlrd', sheet_name=0)
            else:  # .xlsx
                # For .xlsx files, try to read the specified sheet, fall back to first sheet
                try:
                    df = pd.read_excel(file_path, engine='openpyxl', sheet_name=sheet_name)
                except ValueError:
                    # If the specified sheet doesn't exist, try first sheet
                    xl_file = pd.ExcelFile(file_path, engine='openpyxl')
                    available_sheets = xl_file.sheet_names
                    # Try to find sheet by searching for "Перечень" or similar in available sheets
                    found_sheet = self._find_sheet_by_name(available_sheets, sheet_name)
                    if found_sheet:
                        df = pd.read_excel(file_path, engine='openpyxl', sheet_name=found_sheet)
                    else:
                        df = pd.read_excel(file_path, engine='openpyxl', sheet_name=0)
        except Exception as e:
            app_logger.error(f"Error reading Excel file {file_path}: {e}")
            raise ValueError(f"Could not read Excel file: {e}")

        # Locate columns based on identifiers / headers
        verification_date_col_idx = None
        certificate_number_col_idx = None
        valid_until_col_idx = None

        app_logger.info(
            f"Looking for columns: verification_date='{verification_date_column}', "
            f"certificate_number='{certificate_number_column}'"
        )
        app_logger.info(f"Available columns: {list(df.columns[:20])}...")

        # Allow referencing by Excel letter (e.g. AE) if explicitly provided
        date_letter_idx = self._excel_ref_to_index(verification_date_column)
        if date_letter_idx is not None and date_letter_idx < len(df.columns):
            verification_date_col_idx = date_letter_idx
            app_logger.info(f"Using Excel column reference '{verification_date_column}' -> index {verification_date_col_idx}")

        cert_letter_idx = self._excel_ref_to_index(certificate_number_column)
        if cert_letter_idx is not None and cert_letter_idx < len(df.columns):
            certificate_number_col_idx = cert_letter_idx
            app_logger.info(f"Using Excel column reference '{certificate_number_column}' -> index {certificate_number_col_idx}")

        if verification_date_col_idx is None:
            verification_date_col_idx = self._find_column_index(
                df,
                verification_date_column,
                self.verification_date_aliases,
                keyword_groups=[
                    ["дата", "поверки"],
                    ["verification", "date"],
                ],
            )
            if verification_date_col_idx is not None:
                app_logger.info(
                    f"Selected verification date column at index {verification_date_col_idx}: '{df.columns[verification_date_col_idx]}'"
                )

        if certificate_number_col_idx is None:
            certificate_number_col_idx = self._find_column_index(
                df,
                certificate_number_column,
                self.certificate_number_aliases,
                keyword_groups=[
                    ["наличие", "свидетельства"],
                    ["номер", "свидетельства"],
                    ["certificate"],
                ],
            )
            if certificate_number_col_idx is not None:
                app_logger.info(
                    f"Selected certificate number column at index {certificate_number_col_idx}: '{df.columns[certificate_number_col_idx]}'"
                )

        if valid_until_col_idx is None:
            valid_until_col_idx = self._find_column_index(
                df,
                "Действительна до",
                self.valid_until_aliases,
                keyword_groups=[
                    ["действительна", "до"],
                    ["дата", "окончания", "поверки"],
                    ["valid", "until"],
                ],
            )
            if valid_until_col_idx is not None:
                app_logger.info(
                    f"Selected valid-until column at index {valid_until_col_idx}: '{df.columns[valid_until_col_idx]}'"
                )

        # If columns still not found, raise an error
        if verification_date_col_idx is None:
            app_logger.error(f"Verification date column '{verification_date_column}' not found in the Excel file")
            raise ValueError(f"Could not find verification date column. Expected: {verification_date_column}, Available: {list(df.columns[:10])}...")

        if certificate_number_col_idx is None:
            app_logger.error(f"Certificate number column '{certificate_number_column}' not found in the Excel file")
            raise ValueError(f"Could not find certificate number column. Expected: {certificate_number_column}, Available: {list(df.columns[:10])}...")

        # Validate that the date column actually contains date-like values by checking a sample
        date_sample = df.iloc[:min(100, len(df)), verification_date_col_idx] if len(df) > 0 else []
        date_sample = [x for x in date_sample if pd.notna(x) and str(x).lower() not in ['nan', 'none', 'nat']]  # Remove NaN values
        if len(date_sample) > 0:
            # Check if a significant portion of the sample can be parsed as dates
            parseable_dates = 0
            for val in date_sample[:20]:  # Check first 20 non-null values
                if parse_verification_date(str(val)):
                    parseable_dates += 1
            
            # If less than 50% of sample values are parseable as dates, log a warning
            if len(date_sample[:20]) > 0 and parseable_dates / len(date_sample[:20]) < 0.5:
                app_logger.warning(f"Less than 50% of values in date column are parseable as dates. Found {parseable_dates}/{len(date_sample[:20])} parseable dates. Column might be incorrect.")

        parsed_data = []
        invalid_rows = []

        for index, row in df.iterrows():
            excel_row_number = index + 2  # account for header row when reporting row numbers
            try:
                # Get the verification date value from the identified column
                verification_date_val = row.iloc[verification_date_col_idx] if verification_date_col_idx < len(row) else None
                # Get the certificate number value from the identified column
                certificate_number_val = row.iloc[certificate_number_col_idx] if certificate_number_col_idx < len(row) else None

                # Parse the verification date
                # Handle pandas NaN values properly
                verification_date = None
                if pd.isna(verification_date_val):
                    verification_date = None
                else:
                    if isinstance(verification_date_val, pd.Timestamp):
                        verification_date = verification_date_val.to_pydatetime()
                    elif isinstance(verification_date_val, datetime):
                        verification_date = verification_date_val
                    else:
                        verification_date_val_str = str(verification_date_val)
                        if 'IP' in verification_date_val_str or verification_date_val_str.lower() in ['nan', 'nat']:
                            app_logger.warning(
                                f"Found potentially problematic value in verification date column (row {excel_row_number}): {verification_date_val} (type: {type(verification_date_val).__name__})"
                            )

                            if 'IP' in verification_date_val_str:
                                app_logger.info(f"Skipping row {excel_row_number} due to 'IP' value in date column")
                                continue

                        verification_date = parse_verification_date(verification_date_val_str)

                if verification_date and verification_date.tzinfo is not None:
                    # Normalize to naive datetime to avoid timezone comparison issues downstream
                    verification_date = verification_date.replace(tzinfo=None)

                if not verification_date:
                    app_logger.warning(f"Could not parse verification date in row {excel_row_number}, value: {verification_date_val}")
                    continue  # Skip this row if we can't parse the date

                # Parse valid-until date when available
                valid_until_date = None
                if valid_until_col_idx is not None and valid_until_col_idx < len(row):
                    valid_until_val = row.iloc[valid_until_col_idx]
                    if pd.notna(valid_until_val):
                        if isinstance(valid_until_val, pd.Timestamp):
                            valid_until_date = valid_until_val.to_pydatetime()
                        elif isinstance(valid_until_val, datetime):
                            valid_until_date = valid_until_val
                        else:
                            parsed_valid_until = parse_verification_date(str(valid_until_val))
                            if parsed_valid_until:
                                valid_until_date = parsed_valid_until
                        if valid_until_date and valid_until_date.tzinfo is not None:
                            valid_until_date = valid_until_date.replace(tzinfo=None)

                # Get certificate number and convert to string
                # Handle pandas NaN values properly
                if pd.isna(certificate_number_val):
                    app_logger.warning(f"Certificate number is empty in row {excel_row_number}")
                    continue  # Skip this row if certificate number is empty

                certificate_number = str(certificate_number_val).strip()

                # Validate certificate format
                is_valid, error_msg = validate_certificate_format_detailed(certificate_number)
                if not is_valid:
                    app_logger.warning(f"Invalid certificate format in row {excel_row_number}: {error_msg}")
                    # Add to invalid rows but continue processing
                    invalid_rows.append((excel_row_number, error_msg))
                    continue

                # Extract additional data (from other columns)
                additional_data = {}
                for col_idx, col_val in enumerate(row):
                    if pd.notna(col_val):  # Only include non-null values
                        col_name = str(df.columns[col_idx]) if col_idx < len(df.columns) else f'column_{col_idx}'
                        additional_data[col_name] = col_val

                # Try to extract device name and serial number from common columns
                device_name = None
                serial_number = None

                # Look for common column names in the additional data
                for col_name, col_value in additional_data.items():
                    if 'Наименование прибора' in col_name or 'Название' in col_name:
                        device_name = str(col_value) if pd.notna(col_value) else None
                    elif 'Заводской номер' in col_name or 'Серийный номер' in col_name:
                        serial_number = str(col_value) if pd.notna(col_value) else None

                # Create ExcelRegistryData object
                excel_data = ExcelRegistryData(
                    verification_date=verification_date,
                    certificate_number=certificate_number,
                    device_name=device_name,
                    serial_number=serial_number,
                    valid_until_date=valid_until_date,
                    source_row_number=excel_row_number,
                    additional_data=additional_data
                )

                parsed_data.append(excel_data)

            except Exception as e:
                app_logger.error(f"Error parsing row {excel_row_number} in file {file_path}: {e}")
                continue  # Skip this row if there's an error

        app_logger.info(f"Parsed {len(parsed_data)} valid records from {file_path}")
        if invalid_rows:
            app_logger.warning(f"Found {len(invalid_rows)} invalid rows: {invalid_rows}")

        return parsed_data

    def validate_excel_structure(self, file_path: str) -> tuple[bool, str]:
        """
        Validate the Excel file structure to ensure it matches expected format.

        Args:
            file_path: Path to the Excel file to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if file_path.lower().endswith('.xls'):
                df = pd.read_excel(file_path, engine='xlrd', nrows=1)  # Read just first row
            else:  # .xlsx
                df = pd.read_excel(file_path, engine='openpyxl', nrows=1)  # Read just first row

            # We expect the file to contain identifiable verification date and certificate columns
            verification_idx = self._find_column_index(
                df,
                "Дата поверки",
                self.verification_date_aliases,
                keyword_groups=[["дата", "поверки"]],
            )
            certificate_idx = self._find_column_index(
                df,
                "Наличие документа с отметкой о поверке (№ св-ва о поверке)",
                self.certificate_number_aliases,
                keyword_groups=[["наличие", "свидетельства"]],
            )

            if verification_idx is None or certificate_idx is None:
                missing = []
                if verification_idx is None:
                    missing.append("Дата поверки")
                if certificate_idx is None:
                    missing.append("Наличие документа с отметкой о поверке (№ св-ва о поверке)")
                return False, f"Required columns not found: {', '.join(missing)}"

            return True, ""

        except Exception as e:
            app_logger.error(f"Error validating Excel structure for {file_path}: {e}")
            return False, f"Could not validate Excel file structure: {e}"

    def extract_year_from_file(self, file_path: str, sheet_name: str = "Перечень") -> Optional[int]:
        """
        Extract year from the first valid verification date in the file.

        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet to extract from (default 'Перечень')

        Returns:
            Year as integer or None if no valid date found
        """
        try:
            if file_path.lower().endswith('.xls'):
                try:
                    df = pd.read_excel(file_path, engine='xlrd', sheet_name=sheet_name, nrows=5)  # Read first 5 rows
                except ValueError:
                    # If the specified sheet doesn't exist, try first sheet
                    xl_file = pd.ExcelFile(file_path, engine='xlrd')
                    available_sheets = xl_file.sheet_names
                    found_sheet = self._find_sheet_by_name(available_sheets, sheet_name)
                    if found_sheet:
                        df = pd.read_excel(file_path, engine='xlrd', sheet_name=found_sheet, nrows=5)
                    else:
                        df = pd.read_excel(file_path, engine='xlrd', sheet_name=0, nrows=5)
            else:  # .xlsx
                try:
                    df = pd.read_excel(file_path, engine='openpyxl', sheet_name=sheet_name, nrows=5)  # Read first 5 rows
                except ValueError:
                    # If the specified sheet doesn't exist, try first sheet
                    xl_file = pd.ExcelFile(file_path, engine='openpyxl')
                    available_sheets = xl_file.sheet_names
                    found_sheet = self._find_sheet_by_name(available_sheets, sheet_name)
                    if found_sheet:
                        df = pd.read_excel(file_path, engine='openpyxl', sheet_name=found_sheet, nrows=5)
                    else:
                        df = pd.read_excel(file_path, engine='openpyxl', sheet_name=0, nrows=5)

            # Try to find verification date column flexibly instead of fixed AE column
            verification_date_col_idx = None
            for idx, col_name in enumerate(df.columns):
                col_name_str = str(col_name).lower()
                if any(date_indicators in col_name_str for date_indicators in
                      ['дата', 'date', 'verification', 'поверки', 'verification date', 'дата поверки']):
                    verification_date_col_idx = idx
                    break

            # If we found a date column, try to extract a year from it
            if verification_date_col_idx is not None and verification_date_col_idx < len(df.columns):
                date_column = df.iloc[:, verification_date_col_idx]
                for value in date_column:
                    if pd.notna(value):
                        year = parse_verification_date(str(value))
                        if year:
                            return year.year

        except Exception as e:
            app_logger.error(f"Error extracting year from {file_path}: {e}")

        return None

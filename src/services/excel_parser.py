from typing import Optional

import pandas as pd

from src.models.excel_data import ExcelRegistryData
from src.utils.date_utils import parse_verification_date
from src.utils.logging_config import app_logger
from src.utils.validators import validate_certificate_format_detailed


class ExcelParserService:
    """
    Service for parsing Excel files with specific requirements for Arshin registry synchronization.
    Parses columns AE (verification date) and AI (certificate number) as specified.
    """

    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls']

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

    def parse_excel_file(self, file_path: str, verification_date_column: str = "AE", certificate_number_column: str = "AI", sheet_name: str = "Перечень") -> list[ExcelRegistryData]:
        """
        Parse an Excel file to extract verification data.

        Args:
            file_path: Path to the Excel file to parse
            verification_date_column: Column identifier for verification date (default 'AE' or 'Дата поверки')
            certificate_number_column: Column identifier for certificate number (default 'AI' or 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
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

        # First try to find columns by their names if they match common Russian names
        verification_date_col_idx = None
        certificate_number_col_idx = None

        app_logger.info(f"Looking for columns: verification_date='{verification_date_column}', certificate_number='{certificate_number_column}'")
        app_logger.info(f"Available columns: {list(df.columns[:20])}...")  # Log first 20 columns

        # Check if column names exist in the dataframe
        for idx, col_name in enumerate(df.columns):
            col_name_str = str(col_name).strip().lower()
            verification_date_column_lower = verification_date_column.lower()
            certificate_number_column_lower = certificate_number_column.lower()

            # Check for verification date column
            if (verification_date_column_lower == 'дата поверки' or
                verification_date_column_lower in col_name_str or
                'дата поверки' in col_name_str or
                'verification date' in col_name_str or
                'date' in col_name_str or
                'дата' in col_name_str):
                verification_date_col_idx = idx
                app_logger.info(f"Found verification date column at index {idx}: '{col_name}'")

            # Check for certificate number column
            if (certificate_number_column_lower == 'наличие документа с отметкой о поверке (№ св-ва о поверке)' or
                certificate_number_column_lower in col_name_str or
                'св-ва о поверке' in col_name_str or
                'certificate' in col_name_str or
                'свидетельство' in col_name_str or
                'номер' in col_name_str):
                certificate_number_col_idx = idx
                app_logger.info(f"Found certificate number column at index {idx}: '{col_name}'")

        # If not found by name, try by Excel column positions (AE = 30th column = index 29, AI = 32nd column = index 31)
        if verification_date_col_idx is None:
            if verification_date_column == 'AE':
                verification_date_col_idx = 29  # 30th column (0-indexed)
        if certificate_number_col_idx is None:
            if certificate_number_column == 'AI':
                certificate_number_col_idx = 31  # 32nd column (0-indexed)

        # If still not found, try to find common column names in a more flexible way
        if verification_date_col_idx is None:
            # Look for various date-related column names
            for idx, col_name in enumerate(df.columns):
                col_name_str = str(col_name).lower()
                if any(date_indicators in col_name_str for date_indicators in
                      ['дата', 'date', 'verification', 'поверки', 'verification date', 'дата поверки']):
                    verification_date_col_idx = idx
                    break

        if certificate_number_col_idx is None:
            # Look for various certificate-related column names
            for idx, col_name in enumerate(df.columns):
                col_name_str = str(col_name).lower()
                if any(cert_indicators in col_name_str for cert_indicators in
                      ['свидетельство', 'certificate', 'св-ва', 'номер', 'счет', 'num', 'document', 'св-во']):
                    certificate_number_col_idx = idx
                    break

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
            try:
                # Get the verification date value from the identified column
                verification_date_val = row.iloc[verification_date_col_idx] if verification_date_col_idx < len(row) else None
                # Get the certificate number value from the identified column
                certificate_number_val = row.iloc[certificate_number_col_idx] if certificate_number_col_idx < len(row) else None

                # Parse the verification date
                # Handle pandas NaN values properly
                if pd.isna(verification_date_val):
                    verification_date = None
                else:
                    verification_date_val_str = str(verification_date_val)
                    # Log problematic values for debugging
                    if 'IP' in str(verification_date_val) or str(verification_date_val).lower() in ['nan', 'nat']:
                        app_logger.warning(f"Found potentially problematic value in verification date column (row {index+1}): {verification_date_val} (type: {type(verification_date_val).__name__})")
                        
                        # Skip rows with 'IP' values as these are not verification dates
                        if 'IP' in str(verification_date_val):
                            app_logger.info(f"Skipping row {index+1} due to 'IP' value in date column")
                            continue
                            
                    verification_date = parse_verification_date(verification_date_val_str)

                if not verification_date:
                    app_logger.warning(f"Could not parse verification date in row {index+1}, value: {verification_date_val}")
                    continue  # Skip this row if we can't parse the date

                # Get certificate number and convert to string
                # Handle pandas NaN values properly
                if pd.isna(certificate_number_val):
                    app_logger.warning(f"Certificate number is empty in row {index+1}")
                    continue  # Skip this row if certificate number is empty

                certificate_number = str(certificate_number_val).strip()

                # Validate certificate format
                is_valid, error_msg = validate_certificate_format_detailed(certificate_number)
                if not is_valid:
                    app_logger.warning(f"Invalid certificate format in row {index+1}: {error_msg}")
                    # Add to invalid rows but continue processing
                    invalid_rows.append((index, error_msg))
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
                    additional_data=additional_data
                )

                parsed_data.append(excel_data)

            except Exception as e:
                app_logger.error(f"Error parsing row {index+1} in file {file_path}: {e}")
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

            # Check if the file has at least the required columns (AE=30, AI=32)
            num_cols = len(df.columns)
            if num_cols < 32:  # Need at least 32 columns to have AI column (0-indexed 31)
                return False, f"Excel file has only {num_cols} columns, need at least 32 for required columns AE and AI"

            # Additional validation could be added here based on header names or expected structure
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

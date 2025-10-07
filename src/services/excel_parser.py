import pandas as pd
from typing import List, Optional
from src.models.excel_data import ExcelRegistryData
from src.utils.date_utils import parse_verification_date
from src.utils.validators import validate_certificate_format_detailed
from src.utils.logging_config import app_logger


class ExcelParserService:
    """
    Service for parsing Excel files with specific requirements for Arshin registry synchronization.
    Parses columns AE (verification date) and AI (certificate number) as specified.
    """
    
    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls']
    
    def parse_excel_file(self, file_path: str, verification_date_column: str = "AE", certificate_number_column: str = "AI") -> List[ExcelRegistryData]:
        """
        Parse an Excel file to extract verification data.
        
        Args:
            file_path: Path to the Excel file to parse
            verification_date_column: Column identifier for verification date (default 'AE' or 'Дата поверки')
            certificate_number_column: Column identifier for certificate number (default 'AI' or 'Наличие документа с отметкой о поверке (№ св-ва о поверке)')
            
        Returns:
            List of ExcelRegistryData objects
            
        Raises:
            ValueError: If file format is unsupported or parsing fails
        """
        # Read the Excel file using pandas
        try:
            # Determine if it's .xls or .xlsx to use the appropriate engine
            if file_path.lower().endswith('.xls'):
                df = pd.read_excel(file_path, engine='xlrd')
            else:  # .xlsx
                df = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            app_logger.error(f"Error reading Excel file {file_path}: {e}")
            raise ValueError(f"Could not read Excel file: {e}")
        
        # First try to find columns by their names if they match common Russian names
        verification_date_col_idx = None
        certificate_number_col_idx = None
        
        # Check if column names exist in the dataframe
        for idx, col_name in enumerate(df.columns):
            col_name_str = str(col_name).strip()
            if verification_date_column == 'Дата поверки' or verification_date_column in col_name_str or 'Дата поверки' in col_name_str:
                verification_date_col_idx = idx
            if certificate_number_column == 'Наличие документа с отметкой о поверке (№ св-ва о поверке)' or certificate_number_column in col_name_str or 'Наличие документа с отметкой о поверке (№ св-ва о поверке)' in col_name_str:
                certificate_number_col_idx = idx
        
        # If not found by name, try by Excel column positions (AE = 30th column = index 29, AI = 32nd column = index 31)
        if verification_date_col_idx is None:
            if verification_date_column == 'AE':
                verification_date_col_idx = 29  # 30th column (0-indexed)
        if certificate_number_col_idx is None:
            if certificate_number_column == 'AI':
                certificate_number_col_idx = 31  # 32nd column (0-indexed)
        
        # If still not found, try default Russian column names
        if verification_date_col_idx is None:
            # Look for column with 'Дата поверки' in the name
            for idx, col_name in enumerate(df.columns):
                if 'Дата поверки' in str(col_name):
                    verification_date_col_idx = idx
                    break
        
        if certificate_number_col_idx is None:
            # Look for column with 'св-ва о поверке' in the name
            for idx, col_name in enumerate(df.columns):
                if 'св-ва о поверке' in str(col_name):
                    certificate_number_col_idx = idx
                    break
        
        # If columns still not found, raise an error
        if verification_date_col_idx is None:
            app_logger.error(f"Verification date column '{verification_date_column}' not found in the Excel file")
            raise ValueError(f"Could not find verification date column. Expected: {verification_date_column}, Available: {list(df.columns[:10])}...")
        
        if certificate_number_col_idx is None:
            app_logger.error(f"Certificate number column '{certificate_number_column}' not found in the Excel file")
            raise ValueError(f"Could not find certificate number column. Expected: {certificate_number_column}, Available: {list(df.columns[:10])}...")
        
        parsed_data = []
        invalid_rows = []
        
        for index, row in df.iterrows():
            try:
                # Get the verification date value from the identified column
                verification_date_val = row.iloc[verification_date_col_idx] if verification_date_col_idx < len(row) else None
                # Get the certificate number value from the identified column
                certificate_number_val = row.iloc[certificate_number_col_idx] if certificate_number_col_idx < len(row) else None
                
                # Parse the verification date
                verification_date = parse_verification_date(str(verification_date_val)) if verification_date_val else None
                if not verification_date:
                    app_logger.warning(f"Could not parse verification date in row {index+1}, value: {verification_date_val}")
                    continue  # Skip this row if we can't parse the date
                
                # Get certificate number and convert to string
                if not certificate_number_val:
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
    
    def extract_year_from_file(self, file_path: str) -> Optional[int]:
        """
        Extract year from the first valid verification date in the file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Year as integer or None if no valid date found
        """
        try:
            if file_path.lower().endswith('.xls'):
                df = pd.read_excel(file_path, engine='xlrd', nrows=5)  # Read first 5 rows
            else:  # .xlsx
                df = pd.read_excel(file_path, engine='openpyxl', nrows=5)  # Read first 5 rows
            
            # Check column AE (index 29) for dates
            if len(df.columns) > 30:  # Check if AE column exists
                ae_column = df.iloc[:, 29] if 29 < len(df.columns) else None
                
                if ae_column is not None:
                    for value in ae_column:
                        if pd.notna(value):
                            year = parse_verification_date(str(value))
                            if year:
                                return year.year
            
        except Exception as e:
            app_logger.error(f"Error extracting year from {file_path}: {e}")
        
        return None
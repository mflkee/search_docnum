from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re


class ExcelRegistryData(BaseModel):
    """
    Represents input data from Excel files containing measurement instruments information.
    """
    verification_date: datetime
    certificate_number: str
    device_name: Optional[str] = None
    serial_number: Optional[str] = None
    additional_data: dict = {}
    
    @field_validator('certificate_number')
    @classmethod
    def validate_certificate_format(cls, v):
        """
        Validate certificate number format using regex pattern
        Expected format: e.g. "C-XXXX/YY-ZZ/NNNNNN" (certificate-number/verification-year/verification-month/sequence)
        """
        if not v:
            raise ValueError('Certificate number cannot be empty')
        
        # General pattern for certificate numbers: Letter-Text/Numbers
        # This is a flexible pattern - can be refined based on specific requirements
        pattern = r'^[A-Z]-[A-Z0-9/]+\d+$'
        if not re.match(pattern, v):
            raise ValueError(f'Invalid certificate number format: {v}')
        
        return v
    
    @field_validator('verification_date')
    @classmethod
    def validate_verification_date(cls, v):
        """
        Validate that verification date is not in the future
        """
        if v and v > datetime.now():
            raise ValueError('Verification date cannot be in the future')
        return v
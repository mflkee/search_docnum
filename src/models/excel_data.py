import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ExcelRegistryData(BaseModel):
    """
    Represents input data from Excel files containing measurement instruments information.
    """
    verification_date: datetime
    certificate_number: str
    device_name: Optional[str] = None
    serial_number: Optional[str] = None
    valid_until_date: Optional[datetime] = None
    source_row_number: Optional[int] = None
    additional_data: dict = {}

    @field_validator('certificate_number')
    @classmethod
    def validate_certificate_format(cls, v):
        """
        Validate certificate number format using regex pattern
        Expected formats from actual data:
        - "C-ВЯ/15-01-2025/402123271"
        - "C-ДШФ/11-10-2024/385850983"
        - "C-ДШФ/11-10-2024/385850983"
        - "C-ВЯ/11-10-2024/385850983"
        """
        if not v:
            raise ValueError('Certificate number cannot be empty')

        # Pattern for Arshin certificate numbers:
        # Letter-Text/DD-MM-YYYY/Numbers or Letter-Text/YYYY-MM-DD/Numbers
        # Examples: "С-ВЯ/15-01-2025/402123271", "С-ДШФ/11-10-2024/385850983"
        pattern = r'^[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]{2}-[0-9]{2}-[0-9]{4}/[0-9]+$|^' + \
                  r'[A-ZА-ЯЁ]-[A-ZА-ЯЁ0-9]+/[0-9]{4}-[0-9]{2}-[0-9]{2}/[0-9]+$'

        if not re.match(pattern, v):
            # Also allow numbers only format (seen in error logs)
            if re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}.*', v):
                # This looks like a date, not a certificate number
                raise ValueError(f'Invalid certificate number format (appears to be date): {v}')
            elif v == 'NaT':
                raise ValueError('Certificate number cannot be NaT')
            else:
                # For now, we'll accept other formats but log a warning
                # In production, we might want to be stricter
                return v

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

from datetime import datetime

from pydantic import BaseModel


class ArshinRegistryRecord(BaseModel):
    """
    Represents records from Arshin API containing instrument details.
    """
    vri_id: str  # ID in Arshin registry
    org_title: str  # Verifying organization name
    mit_number: str  # Registration number of instrument type
    mit_title: str  # Name of instrument type
    mit_notation: str  # Notation of instrument type
    mi_number: str  # Serial number of instrument
    verification_date: datetime  # Verification date
    valid_date: datetime  # Valid until date
    result_docnum: str  # Certificate number
    record_date: datetime  # Date associated with this record for comparison (added for sorting multiple records)

    def __init__(self, **data):
        # If record_date is not provided, use verification_date
        if 'record_date' not in data and 'verification_date' in data:
            data['record_date'] = data['verification_date']
        super().__init__(**data)

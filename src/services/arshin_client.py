import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.models.arshin_record import ArshinRegistryRecord
from src.config.settings import settings
from src.utils.date_utils import format_date_for_arshin_api
from src.utils.logging_config import app_logger
import time


class ArshinClientService:
    """
    Service for interacting with the Arshin API using a two-stage verification process.
    """
    
    def __init__(self):
        self.base_url = settings.arshin_api_base_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 second timeout
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self._last_request_time = 0
        self.rate_limit_period = settings.arshin_api_rate_period
        self.rate_limit_requests = settings.arshin_api_rate_limit
    
    async def close(self):
        """Close the httpx client"""
        await self.client.aclose()
    
    async def _rate_limit(self):
        """Implement rate limiting to prevent overloading the external API"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # Calculate how much time we need to wait to stay within rate limits
        min_interval = self.rate_limit_period / self.rate_limit_requests
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            app_logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Optional[httpx.Response]:
        """
        Make an HTTP request with retry logic for temporary failures.
        """
        max_retries = 3
        base_delay = 1  # Initial delay in seconds
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = await self.client.get(url, **kwargs)
                elif method.upper() == 'POST':
                    response = await self.client.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # If successful, return the response
                if response.status_code < 500:  # Not a server error
                    return response
                
                # For server errors (5xx), continue to retry
                app_logger.warning(f"Server error {response.status_code} on attempt {attempt + 1}, retrying...")
                
            except httpx.TimeoutException:
                app_logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
            except httpx.RequestError as e:
                app_logger.warning(f"Request error on attempt {attempt + 1}: {e}, retrying...")
            except Exception as e:
                app_logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}, retrying...")
            
            # Wait before retrying (exponential backoff)
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
        
        # If all retries failed, log and return None
        app_logger.error(f"All {max_retries} retry attempts failed for {method} {url}")
        return None
    
    async def search_by_certificate_and_year(self, certificate_number: str, year: int) -> Optional[List[Dict[str, Any]]]:
        """
        First stage of verification: Search by year and certificate number to get instrument parameters.
        
        Args:
            certificate_number: The certificate number to search for
            year: The year to search in
            
        Returns:
            List of matching records with instrument parameters, or None if error
        """
        await self._rate_limit()
        
        try:
            # Construct the URL for the first stage search
            url = f"{self.base_url}/vri"
            params = {
                "year": str(year),
                "result_docnum": certificate_number
            }
            
            app_logger.info(f"Searching Arshin API (stage 1) with params: {params}")
            
            response = await self._make_request_with_retry('GET', url, params=params)
            
            if response is None:
                return []
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different possible response formats
                if 'result' in data:
                    # Standard format: data.result contains the actual results
                    if isinstance(data['result'], dict) and 'items' in data['result']:
                        return data['result']['items'] if data['result']['items'] else []
                    elif isinstance(data['result'], list):
                        return data['result']
                    else:
                        # If result is neither a list nor a dict with items, return as is
                        return [data['result']] if data['result'] else []
                elif isinstance(data, list):
                    # Direct array response
                    return data
                elif 'data' in data:
                    # Alternative format
                    return data['data'].get('items', []) if isinstance(data['data'], dict) else data['data']
                else:
                    # If no standard wrapper, assume the whole response is the data
                    return [data] if data else []
            else:
                app_logger.warning(f"Arshin API returned status code {response.status_code} for stage 1 search")
                return []
                
        except httpx.RequestError as e:
            app_logger.error(f"Request error in stage 1 search: {e}")
            return []
        except Exception as e:
            app_logger.error(f"Unexpected error in stage 1 search: {e}")
            return []
    
    async def search_by_instrument_params(
        self, 
        mit_number: Optional[str] = None,
        mit_title: Optional[str] = None, 
        mit_notation: Optional[str] = None,
        mi_modification: Optional[str] = None,
        mi_number: Optional[str] = None,
        year: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Second stage of verification: Search by instrument parameters for the actual record.
        
        Args:
            mit_number: Registration number of instrument type
            mit_title: Name of instrument type
            mit_notation: Notation of instrument type
            mi_modification: Modification of the instrument
            mi_number: Serial number of instrument
            year: Year to search in
            
        Returns:
            List of matching records, or None if error
        """
        await self._rate_limit()
        
        try:
            # Construct the URL for the second stage search
            url = f"{self.base_url}/vri"
            params = {}
            
            if mit_number:
                params["mit_number"] = mit_number
            if mit_title:
                params["mit_title"] = mit_title
            if mit_notation:
                params["mit_notation"] = mit_notation
            if mi_modification:
                params["mi_modification"] = mi_modification
            if mi_number:
                params["mi_number"] = mi_number
            if year:
                params["year"] = str(year)
            
            app_logger.info(f"Searching Arshin API (stage 2) with params: {params}")
            
            response = await self._make_request_with_retry('GET', url, params=params)
            
            if response is None:
                return []
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different possible response formats (same logic as stage 1)
                if 'result' in data:
                    if isinstance(data['result'], dict) and 'items' in data['result']:
                        return data['result']['items'] if data['result']['items'] else []
                    elif isinstance(data['result'], list):
                        return data['result']
                    else:
                        return [data['result']] if data['result'] else []
                elif isinstance(data, list):
                    return data
                elif 'data' in data:
                    return data['data'].get('items', []) if isinstance(data['data'], dict) else data['data']
                else:
                    return [data] if data else []
            else:
                app_logger.warning(f"Arshin API returned status code {response.status_code} for stage 2 search")
                return []
                
        except httpx.RequestError as e:
            app_logger.error(f"Request error in stage 2 search: {e}")
            return []
        except Exception as e:
            app_logger.error(f"Unexpected error in stage 2 search: {e}")
            return []
    
    async def get_instrument_by_certificate(self, certificate_number: str, year: int) -> Optional[ArshinRegistryRecord]:
        """
        Perform the complete two-stage verification process to get a specific instrument record.
        
        Args:
            certificate_number: The certificate number to search for
            year: The year to search in
            
        Returns:
            ArshinRegistryRecord if found, None otherwise
        """
        # Stage 1: Search by certificate number and year to get instrument parameters
        stage1_results = await self.search_by_certificate_and_year(certificate_number, year)
        
        if not stage1_results:
            app_logger.info(f"No results found in stage 1 for certificate {certificate_number}, year {year}")
            return None
        
        app_logger.info(f"Stage 1 returned {len(stage1_results)} potential matches")
        
        # If multiple records are found, select the most recent one
        selected_record = self._select_most_recent_record(stage1_results)
        if selected_record is None:
            app_logger.warning(f"No valid record found after selecting most recent for certificate {certificate_number}")
            return None
        
        # Extract parameters from the selected record for stage 2 search
        mit_number = selected_record.get('mit_number')
        mit_title = selected_record.get('mit_title')
        mit_notation = selected_record.get('mit_notation')
        mi_number = selected_record.get('mi_number')
        mi_modification = selected_record.get('mi_modification')  # if available
        
        # Stage 2: Search by instrument parameters to get the actual verification record
        stage2_results = await self.search_by_instrument_params(
            mit_number=mit_number,
            mit_title=mit_title,
            mit_notation=mit_notation,
            mi_modification=mi_modification,
            mi_number=mi_number,
            year=year
        )
        
        if not stage2_results:
            app_logger.info(f"No results found in stage 2 for certificate {certificate_number}")
            # If no specific record found, return the one from stage 1 as the best match
            return self._convert_to_arshin_record(selected_record, is_stage1_result=True)
        
        # From stage 2 results, select the most recent one again
        final_record = self._select_most_recent_record(stage2_results)
        if final_record:
            return self._convert_to_arshin_record(final_record, is_stage1_result=False)
        else:
            # If we couldn't select a final record, return the stage 1 result
            return self._convert_to_arshin_record(selected_record, is_stage1_result=True)
    
    async def batch_search_instruments(self, certificate_numbers: List[str], year: int) -> Dict[str, Optional[ArshinRegistryRecord]]:
        """
        Search for multiple instruments at once.
        
        Args:
            certificate_numbers: List of certificate numbers to search for
            year: The year to search in
            
        Returns:
            Dictionary mapping certificate numbers to their Arshin records (or None if not found)
        """
        results = {}
        for cert_number in certificate_numbers:
            record = await self.get_instrument_by_certificate(cert_number, year)
            results[cert_number] = record
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.1)
        
        return results
    
    def _select_most_recent_record(self, records: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Select the most recent record by date from a list of records.
        """
        if not records:
            return None
        
        # Try to find the record with the most recent date
        # Arshin records may have different date fields depending on the API response
        # Common date fields to check: verification_date, valid_date, created_date, etc.
        
        def extract_date_from_record(record: Dict[str, Any]) -> Optional[datetime]:
            # Check common date fields in order of preference
            for field in ['verification_date', 'valid_date', 'created_at', 'date']:
                date_value = record.get(field)
                if date_value:
                    try:
                        if isinstance(date_value, str):
                            # Try to parse the date string
                            # Common formats: ISO format, or already in the correct format
                            if 'T' in date_value:  # ISO format with time
                                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                            else:  # Date only
                                return datetime.fromisoformat(date_value)
                        elif isinstance(date_value, (int, float)):
                            # If it's a timestamp
                            return datetime.fromtimestamp(date_value)
                    except (ValueError, TypeError):
                        continue
            return None
        
        # Filter records that have valid dates and find the most recent
        records_with_dates = []
        for record in records:
            date = extract_date_from_record(record)
            if date:
                records_with_dates.append((record, date))
        
        if records_with_dates:
            # Sort by date descending and return the most recent record
            most_recent = max(records_with_dates, key=lambda x: x[1])
            return most_recent[0]
        else:
            # If no records have usable dates, return the first one
            app_logger.warning(f"No records with valid dates found, returning first record")
            return records[0]
    
    def _convert_to_arshin_record(self, api_record: Dict[str, Any], is_stage1_result: bool = True) -> Optional[ArshinRegistryRecord]:
        """
        Convert an API response record to an ArshinRegistryRecord model.
        
        Args:
            api_record: Dictionary from API response
            is_stage1_result: Whether this record is from stage 1 (less detailed) or stage 2 (detailed)
            
        Returns:
            ArshinRegistryRecord or None if conversion fails
        """
        try:
            # Extract required fields
            vri_id = str(api_record.get('vri_id', api_record.get('id', '')))
            org_title = str(api_record.get('org_title', ''))
            mit_number = str(api_record.get('mit_number', ''))
            mit_title = str(api_record.get('mit_title', ''))
            mit_notation = str(api_record.get('mit_notation', ''))
            mi_number = str(api_record.get('mi_number', ''))
            result_docnum = str(api_record.get('result_docnum', ''))
            
            # Parse verification date
            verification_date_str = api_record.get('verification_date', api_record.get('verif_date', ''))
            try:
                if isinstance(verification_date_str, str) and verification_date_str:
                    if 'T' in verification_date_str:
                        verification_date = datetime.fromisoformat(verification_date_str.replace('Z', '+00:00'))
                    else:
                        # Try different date formats
                        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                verification_date = datetime.strptime(verification_date_str, fmt)
                                break
                            except ValueError:
                                continue
                else:
                    verification_date = datetime.now()
            except:
                verification_date = datetime.now()
            
            # Parse validity date
            valid_date_str = api_record.get('valid_date', api_record.get('validity_date', ''))
            try:
                if isinstance(valid_date_str, str) and valid_date_str:
                    if 'T' in valid_date_str:
                        valid_date = datetime.fromisoformat(valid_date_str.replace('Z', '+00:00'))
                    else:
                        # Try different date formats
                        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                valid_date = datetime.strptime(valid_date_str, fmt)
                                break
                            except ValueError:
                                continue
                else:
                    valid_date = datetime.now()
            except:
                valid_date = datetime.now()
            
            # For the record_date (used for selecting most recent), use verification_date if available
            record_date = verification_date
            
            return ArshinRegistryRecord(
                vri_id=vri_id,
                org_title=org_title,
                mit_number=mit_number,
                mit_title=mit_title,
                mit_notation=mit_notation,
                mi_number=mi_number,
                verification_date=verification_date,
                valid_date=valid_date,
                result_docnum=result_docnum,
                record_date=record_date
            )
        
        except Exception as e:
            app_logger.error(f"Error converting API record to ArshinRegistryRecord: {e}, record: {api_record}")
            return None
    
    async def check_api_health(self) -> bool:
        """
        Check if the Arshin API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self._rate_limit()
            test_url = f"{self.base_url}/vri"
            response = await self._make_request_with_retry('GET', test_url, params={"year": "2024"}, timeout=10.0)
            
            if response is None:
                return False
                
            return response.status_code in [200, 400, 404]  # 200 = OK, 400/404 = API accessible but no results
        except:
            return False
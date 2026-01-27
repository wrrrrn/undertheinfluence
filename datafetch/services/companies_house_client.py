"""
Companies House API Client

Provides access to the Companies House API for company search and data retrieval.

API Documentation: https://developer.company-information.service.gov.uk/

Features:
- Basic Auth using API key
- Rate limiting (600 requests per 5 minutes)
- Response caching to data/companieshouse/
- Exponential backoff on rate limit errors
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from os.path import exists, join
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from datafetch import helpers

logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://api.company-information.service.gov.uk"
RATE_LIMIT_REQUESTS = 600
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes
MAX_RETRIES = 5  # More retries to handle rate limiting
INITIAL_BACKOFF_SECONDS = 1


@dataclass
class CompanySearchResult:
    """A single company from search results."""
    company_number: str
    title: str  # Company name
    company_status: str
    company_type: str
    date_of_creation: Optional[str]
    date_of_cessation: Optional[str]
    address_snippet: Optional[str]
    matches: Optional[Dict[str, Any]]  # What matched in the search

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CompanySearchResult':
        """Create from Companies House API response."""
        return cls(
            company_number=data.get('company_number', ''),
            title=data.get('title', ''),
            company_status=data.get('company_status', ''),
            company_type=data.get('company_type', ''),
            date_of_creation=data.get('date_of_creation'),
            date_of_cessation=data.get('date_of_cessation'),
            address_snippet=data.get('address_snippet'),
            matches=data.get('matches'),
        )


@dataclass
class CompanyOfficer:
    """
    A company officer (director, secretary, etc.) from Companies House.

    Officer data comes from the /company/{num}/officers endpoint.
    """
    officer_id: str           # From links.officer.appointments URL
    name: str                 # "SURNAME, Forenames" format
    officer_role: str         # director, secretary, etc.
    appointed_on: Optional[str]
    resigned_on: Optional[str]
    nationality: Optional[str]
    occupation: Optional[str]
    country_of_residence: Optional[str]
    date_of_birth: Optional[Dict[str, int]]  # {month: int, year: int}
    is_corporate: bool        # True if corporate director

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CompanyOfficer':
        """Create from Companies House API response."""
        # Extract officer_id from links.officer.appointments URL
        # Format: /officers/{officer_id}/appointments
        officer_id = ''
        links = data.get('links', {})
        if 'officer' in links:
            officer_appointments = links['officer'].get('appointments', '')
            # Extract ID from path like /officers/abc123.../appointments
            if officer_appointments:
                parts = officer_appointments.strip('/').split('/')
                if len(parts) >= 2:
                    officer_id = parts[1]

        # Determine if corporate director
        officer_role = data.get('officer_role', '')
        is_corporate = 'corporate' in officer_role.lower()

        return cls(
            officer_id=officer_id,
            name=data.get('name', ''),
            officer_role=officer_role,
            appointed_on=data.get('appointed_on'),
            resigned_on=data.get('resigned_on'),
            nationality=data.get('nationality'),
            occupation=data.get('occupation'),
            country_of_residence=data.get('country_of_residence'),
            date_of_birth=data.get('date_of_birth'),
            is_corporate=is_corporate,
        )


@dataclass
class PersonWithSignificantControl:
    """
    A Person with Significant Control (PSC) - beneficial owner from Companies House.

    PSC data comes from the /company/{num}/persons-with-significant-control endpoint.

    Note: PSCs don't have unique IDs like officers - they're identified by name + DOB.
    The psc_id is extracted from the self link but may not be stable across API calls.
    """
    psc_id: str                      # From links.self URL
    name: str                        # Individual or corporate name
    kind: str                        # individual-person-with-significant-control, corporate-entity, etc.
    natures_of_control: List[str]    # ownership-of-shares-25-to-50-percent, etc.
    notified_on: Optional[str]       # When registered
    ceased_on: Optional[str]         # When ceased
    nationality: Optional[str]
    country_of_residence: Optional[str]
    date_of_birth: Optional[Dict[str, int]]  # {month: int, year: int} - partial DOB
    is_corporate: bool
    is_exempt: bool                  # True if PSC exemption applies

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'PersonWithSignificantControl':
        """Create from Companies House API response."""
        # Extract psc_id from links.self URL
        # Format: /company/{num}/persons-with-significant-control/{type}/{id}
        psc_id = ''
        links = data.get('links', {})
        if 'self' in links:
            self_link = links['self']
            # Extract ID from path
            parts = self_link.strip('/').split('/')
            if parts:
                psc_id = parts[-1]

        # Determine kind and if corporate
        kind = data.get('kind', '')
        is_corporate = any(x in kind.lower() for x in ['corporate', 'legal-person'])

        # Handle different name fields based on kind
        if is_corporate:
            name = data.get('name', '')
        else:
            name = data.get('name', data.get('name_elements', {}).get('forename', '') + ' ' + data.get('name_elements', {}).get('surname', ''))

        # Check for exemption
        is_exempt = 'exempt' in kind.lower() or data.get('exemptions') is not None

        return cls(
            psc_id=psc_id,
            name=name.strip(),
            kind=kind,
            natures_of_control=data.get('natures_of_control', []),
            notified_on=data.get('notified_on'),
            ceased_on=data.get('ceased_on'),
            nationality=data.get('nationality'),
            country_of_residence=data.get('country_of_residence'),
            date_of_birth=data.get('date_of_birth'),
            is_corporate=is_corporate,
            is_exempt=is_exempt,
        )


@dataclass
class CompanyProfile:
    """Full company profile from Companies House."""
    company_number: str
    company_name: str
    company_status: str
    company_type: str
    date_of_creation: Optional[str]
    date_of_cessation: Optional[str]
    registered_office_address: Optional[Dict[str, str]]
    sic_codes: List[str]
    previous_company_names: List[Dict[str, str]]
    has_charges: bool
    has_insolvency_history: bool
    jurisdiction: str

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CompanyProfile':
        """Create from Companies House API response."""
        return cls(
            company_number=data.get('company_number', ''),
            company_name=data.get('company_name', ''),
            company_status=data.get('company_status', ''),
            company_type=data.get('type', ''),
            date_of_creation=data.get('date_of_creation'),
            date_of_cessation=data.get('date_of_cessation'),
            registered_office_address=data.get('registered_office_address'),
            sic_codes=data.get('sic_codes', []),
            previous_company_names=data.get('previous_company_names', []),
            has_charges=data.get('has_charges', False),
            has_insolvency_history=data.get('has_insolvency_history', False),
            jurisdiction=data.get('jurisdiction', ''),
        )


class RateLimiter:
    """
    Tracks API requests to stay within rate limits.

    Companies House allows 600 requests per 5 minutes.
    """

    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS,
                 window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times: List[datetime] = []

    def _clean_old_requests(self) -> None:
        """Remove requests older than the rate limit window."""
        cutoff = datetime.now() - timedelta(seconds=self.window_seconds)
        self.request_times = [t for t in self.request_times if t > cutoff]

    def can_make_request(self) -> bool:
        """Check if we can make another request within rate limits."""
        self._clean_old_requests()
        return len(self.request_times) < self.max_requests

    def requests_remaining(self) -> int:
        """Return number of requests remaining in current window."""
        self._clean_old_requests()
        return max(0, self.max_requests - len(self.request_times))

    def wait_time_seconds(self) -> float:
        """Return seconds to wait before next request is allowed."""
        self._clean_old_requests()
        if len(self.request_times) < self.max_requests:
            return 0.0

        # Wait until oldest request expires
        oldest = min(self.request_times)
        wait_until = oldest + timedelta(seconds=self.window_seconds)
        wait_seconds = (wait_until - datetime.now()).total_seconds()
        return max(0.0, wait_seconds)

    def record_request(self) -> None:
        """Record that a request was made."""
        self.request_times.append(datetime.now())

    def wait_if_needed(self) -> None:
        """Block until a request can be made."""
        wait_time = self.wait_time_seconds()
        if wait_time > 0:
            logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(wait_time)


class CompaniesHouseClient:
    """
    Client for the Companies House API.

    Features:
    - Automatic rate limiting
    - Response caching
    - Exponential backoff on errors
    - Structured response types
    """

    def __init__(self, api_key: Optional[str] = None, cache_enabled: bool = True):
        """
        Initialize the client.

        Args:
            api_key: Companies House API key. If not provided, reads from settings.
            cache_enabled: Whether to cache API responses to disk.
        """
        self.api_key = api_key or getattr(settings, 'COMPANIES_HOUSE_API_KEY', '')
        self.cache_enabled = cache_enabled
        self.rate_limiter = RateLimiter()

        if not self.api_key:
            logger.warning(
                "No Companies House API key configured. "
                "Set COMPANIES_HOUSE_API_KEY in .env or pass to constructor."
            )

        # Ensure cache directory exists
        if self.cache_enabled:
            helpers.create_data_folder('companieshouse')
            helpers.create_data_folder('companieshouse/search')
            helpers.create_data_folder('companieshouse/company')
            helpers.create_data_folder('companieshouse/officers')
            helpers.create_data_folder('companieshouse/pscs')

    def _get_auth(self) -> tuple:
        """Return Basic Auth tuple (API key as username, empty password)."""
        return (self.api_key, '')

    def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                      cache_filename: Optional[str] = None,
                      cache_path: str = 'companieshouse',
                      refresh: bool = False) -> Optional[Dict]:
        """
        Make an API request with rate limiting, caching, and retries.

        Args:
            endpoint: API endpoint (e.g., '/search/companies')
            params: Query parameters
            cache_filename: Filename for caching (without path)
            cache_path: Subdirectory within data/ for cache
            refresh: Force refresh even if cached

        Returns:
            JSON response dict, or None on error
        """
        # Check cache first
        if self.cache_enabled and cache_filename and not refresh:
            cache_file = join(settings.BASE_DIR, 'data', cache_path, cache_filename)
            if exists(cache_file):
                logger.debug(f"Cache hit: {cache_filename}")
                with open(cache_file) as f:
                    return json.load(f)

        # Rate limit
        self.rate_limiter.wait_if_needed()

        # Add small delay between requests to stay well under rate limit
        # (600 requests per 5 min = 2/sec max, we'll do ~1/sec to be safe)
        time.sleep(0.5)

        url = f"{BASE_URL}{endpoint}"
        backoff = INITIAL_BACKOFF_SECONDS

        for attempt in range(MAX_RETRIES):
            try:
                self.rate_limiter.record_request()
                response = requests.get(
                    url,
                    params=params,
                    auth=self._get_auth(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()

                    # Cache successful response
                    if self.cache_enabled and cache_filename:
                        cache_file = join(settings.BASE_DIR, 'data', cache_path, cache_filename)
                        with open(cache_file, 'w') as f:
                            json.dump(data, f, indent=2)

                    return data

                elif response.status_code == 404:
                    logger.debug(f"Not found: {endpoint}")
                    return None

                elif response.status_code == 401:
                    logger.error("Invalid API key - check COMPANIES_HOUSE_API_KEY")
                    return None

                elif response.status_code == 429:
                    # Rate limited - use exponential backoff starting at 60s
                    # Companies House rate limit is 600/5min, so worst case wait is ~5 min
                    base_wait = 60
                    wait_time = base_wait * (2 ** attempt)  # 60s, 120s, 240s, etc.
                    wait_time = min(wait_time, 300)  # Cap at 5 minutes
                    logger.warning(f"Rate limited (429), waiting {wait_time:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue

                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    logger.warning(f"Server error {response.status_code}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue

                else:
                    logger.error(f"Unexpected status {response.status_code}: {response.text[:200]}")
                    return None

            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue
                return None

        logger.error(f"Failed after {MAX_RETRIES} attempts: {endpoint}")
        return None

    def search_companies(self, query: str, items_per_page: int = 20,
                        start_index: int = 0,
                        refresh: bool = False) -> List[CompanySearchResult]:
        """
        Search for companies by name.

        Args:
            query: Company name to search for
            items_per_page: Number of results per page (max 100)
            start_index: Pagination offset
            refresh: Force refresh even if cached

        Returns:
            List of CompanySearchResult objects
        """
        if not query:
            return []

        # Sanitize query for cache filename
        safe_query = "".join(c if c.isalnum() else '_' for c in query.lower())[:50]
        cache_filename = f"search_{safe_query}_{start_index}.json"

        params = {
            'q': query,
            'items_per_page': min(items_per_page, 100),
            'start_index': start_index,
        }

        data = self._make_request(
            '/search/companies',
            params=params,
            cache_filename=cache_filename,
            cache_path='companieshouse/search',
            refresh=refresh
        )

        if not data or 'items' not in data:
            return []

        return [CompanySearchResult.from_api_response(item) for item in data['items']]

    def get_company(self, company_number: str,
                   refresh: bool = False) -> Optional[CompanyProfile]:
        """
        Get full company profile by company number.

        Args:
            company_number: Companies House company number (e.g., '00000001')
            refresh: Force refresh even if cached

        Returns:
            CompanyProfile object, or None if not found
        """
        if not company_number:
            return None

        # Normalize company number (pad with leading zeros if needed)
        company_number = company_number.upper().zfill(8)
        cache_filename = f"company_{company_number}.json"

        data = self._make_request(
            f'/company/{company_number}',
            cache_filename=cache_filename,
            cache_path='companieshouse/company',
            refresh=refresh
        )

        if not data:
            return None

        return CompanyProfile.from_api_response(data)

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return {
            'requests_remaining': self.rate_limiter.requests_remaining(),
            'wait_time_seconds': self.rate_limiter.wait_time_seconds(),
        }

    def test_connection(self) -> bool:
        """
        Test API connection and credentials.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.api_key:
            logger.error("No API key configured")
            return False

        # Try a simple search - directly test the API response
        try:
            self.rate_limiter.wait_if_needed()
            self.rate_limiter.record_request()

            response = requests.get(
                f"{BASE_URL}/search/companies",
                params={'q': 'test', 'items_per_page': 1},
                auth=self._get_auth(),
                timeout=30
            )

            if response.status_code == 200:
                logger.info("Companies House API connection successful")
                return True
            elif response.status_code == 401:
                logger.error(
                    "Invalid API key. Get a valid key from: "
                    "https://developer.company-information.service.gov.uk/"
                )
                return False
            else:
                logger.error(f"API test failed with status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_company_officers(
        self,
        company_number: str,
        include_resigned: bool = False,
        officer_roles: Optional[List[str]] = None,
        refresh: bool = False
    ) -> List[CompanyOfficer]:
        """
        Get company officers (directors, secretaries, etc.).

        Args:
            company_number: Companies House company number
            include_resigned: Include officers who have resigned
            officer_roles: Filter by role (default: ['director', 'corporate-director'])
            refresh: Force refresh even if cached

        Returns:
            List of CompanyOfficer objects
        """
        if not company_number:
            return []

        # Normalize company number
        company_number = company_number.upper().strip()
        if not company_number[:2].isalpha():
            company_number = company_number.zfill(8)

        # Default to directors only
        if officer_roles is None:
            officer_roles = ['director', 'corporate-director']

        cache_filename = f"officers_{company_number}.json"

        # Try cache first
        if self.cache_enabled and not refresh:
            cache_file = join(settings.BASE_DIR, 'data', 'companieshouse/officers', cache_filename)
            if exists(cache_file):
                logger.debug(f"Cache hit: {cache_filename}")
                with open(cache_file) as f:
                    cached_data = json.load(f)
                    officers = [CompanyOfficer.from_api_response(item) for item in cached_data.get('items', [])]
                    return self._filter_officers(officers, include_resigned, officer_roles)

        # Fetch from API (may need pagination)
        all_items = []
        start_index = 0
        items_per_page = 100

        while True:
            params = {
                'items_per_page': items_per_page,
                'start_index': start_index,
            }

            data = self._make_request(
                f'/company/{company_number}/officers',
                params=params,
                cache_filename=None,  # Don't cache individual pages
                refresh=refresh
            )

            if not data:
                break

            items = data.get('items', [])
            all_items.extend(items)

            # Check if there are more pages
            total_results = data.get('total_results', 0)
            if start_index + len(items) >= total_results:
                break

            start_index += items_per_page

        # Cache the combined results
        if self.cache_enabled and all_items:
            cache_file = join(settings.BASE_DIR, 'data', 'companieshouse/officers', cache_filename)
            with open(cache_file, 'w') as f:
                json.dump({'items': all_items}, f, indent=2)

        officers = [CompanyOfficer.from_api_response(item) for item in all_items]
        return self._filter_officers(officers, include_resigned, officer_roles)

    def _filter_officers(
        self,
        officers: List[CompanyOfficer],
        include_resigned: bool,
        officer_roles: List[str]
    ) -> List[CompanyOfficer]:
        """Filter officers by resignation status and role."""
        result = []
        for officer in officers:
            # Filter by resignation status
            if not include_resigned and officer.resigned_on:
                continue

            # Filter by role (if specified)
            if officer_roles:
                role_lower = officer.officer_role.lower()
                if not any(r.lower() in role_lower for r in officer_roles):
                    continue

            result.append(officer)

        return result

    def get_company_pscs(
        self,
        company_number: str,
        include_ceased: bool = False,
        refresh: bool = False
    ) -> List[PersonWithSignificantControl]:
        """
        Get Persons with Significant Control (beneficial owners).

        Args:
            company_number: Companies House company number
            include_ceased: Include PSCs who have ceased
            refresh: Force refresh even if cached

        Returns:
            List of PersonWithSignificantControl objects
        """
        if not company_number:
            return []

        # Normalize company number
        company_number = company_number.upper().strip()
        if not company_number[:2].isalpha():
            company_number = company_number.zfill(8)

        cache_filename = f"pscs_{company_number}.json"

        # Try cache first
        if self.cache_enabled and not refresh:
            cache_file = join(settings.BASE_DIR, 'data', 'companieshouse/pscs', cache_filename)
            if exists(cache_file):
                logger.debug(f"Cache hit: {cache_filename}")
                with open(cache_file) as f:
                    cached_data = json.load(f)
                    pscs = [PersonWithSignificantControl.from_api_response(item) for item in cached_data.get('items', [])]
                    return self._filter_pscs(pscs, include_ceased)

        # Fetch from API (may need pagination)
        all_items = []
        start_index = 0
        items_per_page = 100

        while True:
            params = {
                'items_per_page': items_per_page,
                'start_index': start_index,
            }

            data = self._make_request(
                f'/company/{company_number}/persons-with-significant-control',
                params=params,
                cache_filename=None,  # Don't cache individual pages
                refresh=refresh
            )

            if not data:
                break

            items = data.get('items', [])
            all_items.extend(items)

            # Check if there are more pages
            total_results = data.get('total_results', 0)
            if start_index + len(items) >= total_results:
                break

            start_index += items_per_page

        # Cache the combined results
        if self.cache_enabled and all_items:
            cache_file = join(settings.BASE_DIR, 'data', 'companieshouse/pscs', cache_filename)
            with open(cache_file, 'w') as f:
                json.dump({'items': all_items}, f, indent=2)

        pscs = [PersonWithSignificantControl.from_api_response(item) for item in all_items]
        return self._filter_pscs(pscs, include_ceased)

    def _filter_pscs(
        self,
        pscs: List[PersonWithSignificantControl],
        include_ceased: bool
    ) -> List[PersonWithSignificantControl]:
        """Filter PSCs by ceased status."""
        if include_ceased:
            return pscs

        return [p for p in pscs if not p.ceased_on]

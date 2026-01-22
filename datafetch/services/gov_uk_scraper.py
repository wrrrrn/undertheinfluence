"""
GOV.UK Web Scraper for Ministerial Transparency Publications

Automatically discovers quarterly ministerial meetings publications
from GOV.UK department collection pages.

Phase 2: Web scraping for bulk import automation
"""

import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from datafetch import helpers

logger = logging.getLogger(__name__)


class GovUkScraper:
    """Scrape GOV.UK for ministerial transparency publications."""

    def discover_publications(self, collection_url: str, since_year: int = None) -> List[Dict]:
        """
        Scrape collection page to find all quarterly publications.

        Args:
            collection_url: GOV.UK collection page URL
            since_year: Only return publications from this year onwards (optional)

        Returns:
            List of dicts: [
                {
                    'url': str,  # Download URL for CSV/XLSX
                    'title': str,
                    'quarter': str,  # "2024-Q1"
                    'format': str,  # "csv" or "xlsx"
                },
                ...
            ]
        """
        logger.info(f"Discovering publications from: {collection_url}")

        # Ensure cache directory exists
        helpers.create_data_folder('ministerial_meetings/scrape')

        # Fetch collection page HTML (cached)
        collection_slug = collection_url.split('/')[-1]
        html = helpers.fetch_text(
            collection_url,
            f'{collection_slug}_collection.html',
            path='ministerial_meetings/scrape'
        )

        soup = BeautifulSoup(html, 'html.parser')
        publications = []

        # Find all publication links
        # GOV.UK uses <a> tags with specific classes for publication links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)

            # Match ministerial transparency publications
            # Look for keywords: "ministerial", "meeting", "transparency"
            if not any(keyword in text.lower() for keyword in ['ministerial', 'meeting', 'transparency']):
                continue

            # Skip if it's the collection page itself or navigation
            if 'collection' in href or href.endswith('#'):
                continue

            # Extract quarter from title
            quarter = self._extract_quarter(text)

            if quarter:
                year = int(quarter.split('-')[0])

                # Filter by year if requested
                if since_year and year < since_year:
                    logger.debug(f"Skipping {text} (year {year} < {since_year})")
                    continue

                # Visit publication page to get download URL
                pub_url = f"https://www.gov.uk{href}" if href.startswith('/') else href

                logger.debug(f"Checking publication: {text}")
                download_url, fmt = self._find_download_url(pub_url)

                if download_url:
                    # _find_download_url now prioritizes meetings files
                    publications.append({
                        'url': download_url,
                        'title': text,
                        'quarter': quarter,
                        'format': fmt,
                        'publication_url': pub_url,
                    })
                    logger.info(f"Found: {text} ({quarter}) - {fmt.upper()}")

        logger.info(f"Discovered {len(publications)} publications")
        return publications

    def _extract_quarter(self, title: str) -> Optional[str]:
        """
        Extract quarter from publication title.

        Args:
            title: Publication title

        Returns:
            Quarter string like "2024-Q1" or None
        """
        # Pattern 1: "January to March 2024" or "Jan-Mar 2024"
        month_to_quarter = {
            'january': 'Q1', 'february': 'Q1', 'march': 'Q1',
            'april': 'Q2', 'may': 'Q2', 'june': 'Q2',
            'july': 'Q3', 'august': 'Q3', 'september': 'Q3',
            'october': 'Q4', 'november': 'Q4', 'december': 'Q4',
        }

        title_lower = title.lower()

        # Find year first
        year_match = re.search(r'20\d{2}', title)
        if year_match:
            year = year_match.group()

            # Then find month to determine quarter
            for month, quarter in month_to_quarter.items():
                if month in title_lower:
                    return f"{year}-{quarter}"

        # Pattern 2: Explicit "Q1 2024" or "Quarter 1 2024"
        q_match = re.search(r'[Qq](?:uarter\s*)?([1-4])\s*(20\d{2})', title)
        if q_match:
            return f"{q_match.group(2)}-Q{q_match.group(1)}"

        # Pattern 3: "2024 Q1" or "2024-Q1"
        q_match2 = re.search(r'(20\d{2})[-\s]*[Qq]([1-4])', title)
        if q_match2:
            return f"{q_match2.group(1)}-Q{q_match2.group(2)}"

        logger.debug(f"Could not extract quarter from: {title}")
        return None

    def _find_download_url(self, publication_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Find CSV/XLSX download URL from publication page.

        Prioritizes files with "meeting" in the filename since publication pages
        often contain multiple files (gifts, hospitality, meetings, travel).

        Args:
            publication_url: URL of the publication page

        Returns:
            Tuple of (download_url, format) or (None, None)
        """
        # Ensure cache directory exists
        helpers.create_data_folder('ministerial_meetings/scrape')

        # Fetch publication page
        pub_slug = publication_url.split('/')[-1]
        html = helpers.fetch_text(
            publication_url,
            f'{pub_slug}_pub.html',
            path='ministerial_meetings/scrape'
        )

        soup = BeautifulSoup(html, 'html.parser')

        # Collect all download links
        csv_links = []
        xlsx_links = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            # Skip preview links and relative paths that aren't assets
            if '/csv-preview/' in href or href.startswith('#'):
                continue

            if href.endswith('.csv'):
                url = f"https://www.gov.uk{href}" if href.startswith('/') else href
                csv_links.append(url)
            elif href.endswith('.xlsx') or href.endswith('.xls'):
                url = f"https://www.gov.uk{href}" if href.startswith('/') else href
                xlsx_links.append(url)

        # Priority 1: CSV with "meeting" in filename
        for url in csv_links:
            filename = url.split('/')[-1].lower()
            if 'meeting' in filename:
                logger.debug(f"Found meetings CSV: {url}")
                return (url, 'csv')

        # Priority 2: XLSX with "meeting" in filename
        for url in xlsx_links:
            filename = url.split('/')[-1].lower()
            if 'meeting' in filename:
                logger.debug(f"Found meetings XLSX: {url}")
                return (url, 'xlsx')

        # Priority 3: Any CSV (fallback for older publications with different naming)
        if csv_links:
            logger.debug(f"No meetings file found, using first CSV: {csv_links[0]}")
            return (csv_links[0], 'csv')

        # Priority 4: Any XLSX (fallback)
        if xlsx_links:
            logger.debug(f"No meetings file found, using first XLSX: {xlsx_links[0]}")
            return (xlsx_links[0], 'xlsx')

        logger.warning(f"Could not find download link on: {publication_url}")
        return (None, None)

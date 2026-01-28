"""
Companies House Matcher

Matches Organization records to Companies House companies using multiple strategies:
1. Existing CH identifier (confidence=1.0)
2. Exact name match from search results (confidence=0.95)
3. Normalized name match (confidence=0.85)
4. CH-specific similarity match (confidence=0.80) - handles trading names vs legal names
5. Fuzzy match with validation (confidence=0.75)

Creates ActorResolution records when the same company number is found on multiple orgs
(deduplication via identifier matching).
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from datafetch import models
from datafetch.services.companies_house_client import (
    CompaniesHouseClient,
    CompanyProfile,
    CompanySearchResult,
)
from datafetch.utils.normalization import (
    calculate_name_similarity,
    normalize_actor_name,
)


# Common suffixes to strip from company names for matching
CH_LEGAL_SUFFIXES = [
    r'\bplc\b',
    r'\bp\.l\.c\.?\b',
    r'\blimited\b',
    r'\bltd\b',
    r'\bl\.t\.d\.?\b',
    r'\bllp\b',
    r'\bl\.l\.p\.?\b',
    r'\binc\b',
    r'\bincorporated\b',
    r'\bcorp\b',
    r'\bcorporation\b',
    r'\bco\b',
    r'\bcompany\b',
    r'^the\s+',  # Leading "THE " - very common difference
]

# Common business words that can be stripped for core name matching
CH_COMMON_SUFFIXES = [
    r'\buk\b',
    r'\b\(uk\)\b',
    r'\binternational\b',
    r'\bgroup\b',
    r'\bholdings?\b',
    r'\bconsulting\b',
    r'\bconsultants?\b',
    r'\bcommunications?\b',
    r'\badvisou?rs?\b',
    r'\bstrategic\b',
    r'\bstrategies\b',
    r'\bpartners\b',
    r'\bpartnership\b',
    r'\bassociates?\b',
    r'\bservices?\b',
    r'\bsolutions?\b',
    r'\bagency\b',
    r'\bengineering\b',
    r'\beurope\b',
    r'\bglobal\b',
]


def normalize_company_name(name: str, strip_legal: bool = True,
                           strip_common: bool = False) -> str:
    """
    Normalize a company name for matching.

    Args:
        name: Company name to normalize
        strip_legal: Remove legal suffixes (Ltd, PLC, etc.)
        strip_common: Remove common business words (UK, International, etc.)

    Returns:
        Normalized name for comparison
    """
    if not name:
        return ''

    # Lowercase
    result = name.lower().strip()

    # Normalize punctuation
    result = result.replace('&', ' and ')
    result = result.replace('+', ' and ')
    result = result.replace('-', ' ')
    result = result.replace('.', ' ')
    result = result.replace(',', ' ')
    result = result.replace("'", '')
    result = result.replace('"', '')

    # Remove parenthetical content like "(UK)" or "(trading as X)"
    result = re.sub(r'\([^)]*\)', ' ', result)

    # Normalize spacing around single characters (e.g., "5 x 15" → "5x15")
    # This handles dimension-style names and isolated characters
    result = re.sub(r'(\w)\s+([a-z])\s+(\w)', r'\1\2\3', result)

    # Also handle "A & B" → "a and b" already done, but "A B" where B is single char
    # Remove spaces between alphanumeric sequences that look like one unit
    # e.g., "5 x 15" → "5x15", "A 1" → "a1"
    result = re.sub(r'(\d)\s*x\s*(\d)', r'\1x\2', result)  # Specifically for dimensions like "5x15"

    # Handle number-letter combinations like "90 UP" → "90up"
    # This catches patterns where a number is followed by short text (1-3 chars)
    result = re.sub(r'(\d+)\s+([a-z]{1,3})\b', r'\1\2', result)

    # Strip legal suffixes
    if strip_legal:
        for suffix in CH_LEGAL_SUFFIXES:
            result = re.sub(suffix, ' ', result, flags=re.IGNORECASE)

    # Strip common business words
    if strip_common:
        for suffix in CH_COMMON_SUFFIXES:
            result = re.sub(suffix, ' ', result, flags=re.IGNORECASE)

    # Collapse whitespace and trim
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def split_camelcase(name: str) -> str:
    """
    Split camelCase or PascalCase words into separate words.

    "FleishmanHillard" → "fleishman hillard"
    "BCW" → "bcw" (no change for all caps)
    """
    # Insert space before uppercase letters that follow lowercase letters
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    return result.lower()


def calculate_ch_similarity(query_name: str, ch_name: str) -> Tuple[float, str]:
    """
    Calculate Companies House-specific similarity between a query and CH result.

    Handles common patterns like:
    - "Grayling" vs "GRAYLING COMMUNICATIONS LIMITED" → high match
    - "BCW" vs "BCW LIMITED" → high match
    - "Hanover Communications" vs "HANOVER COMMUNICATIONS UK LTD" → high match
    - "FleishmanHillard" vs "FLEISHMAN-HILLARD GROUP LIMITED" → high match (camelCase)

    Args:
        query_name: Organization name we're searching for
        ch_name: Company name from Companies House search results

    Returns:
        Tuple of (similarity_score, match_reason)
        - similarity_score: 0.0 to 1.0
        - match_reason: Description of why it matched
    """
    if not query_name or not ch_name:
        return 0.0, 'empty'

    # Level 1: Normalize with legal suffixes stripped (includes THE prefix)
    query_norm = normalize_company_name(query_name, strip_legal=True, strip_common=False)
    ch_norm = normalize_company_name(ch_name, strip_legal=True, strip_common=False)

    # Also try with camelCase split (for "FleishmanHillard" → "fleishman hillard")
    query_camel = normalize_company_name(split_camelcase(query_name), strip_legal=True, strip_common=False)

    # Exact match after basic normalization
    if query_norm == ch_norm:
        return 0.95, 'exact_normalized'

    # Try camelCase version
    if query_camel == ch_norm:
        return 0.95, 'exact_camelcase'

    # Level 1.5: Handle THE prefix separately (belt and suspenders)
    # "Trussell Trust" vs "THE TRUSSELL TRUST" should be 0.95
    query_no_the = re.sub(r'^the\s+', '', query_norm, flags=re.IGNORECASE)
    ch_no_the = re.sub(r'^the\s+', '', ch_norm, flags=re.IGNORECASE)
    if query_no_the == ch_no_the and query_no_the:
        return 0.95, 'exact_the_variant'

    # Level 2: Normalize with common business words stripped
    query_core = normalize_company_name(query_name, strip_legal=True, strip_common=True)
    ch_core = normalize_company_name(ch_name, strip_legal=True, strip_common=True)
    query_core_camel = normalize_company_name(split_camelcase(query_name), strip_legal=True, strip_common=True)

    # Exact match on core name
    if query_core == ch_core:
        return 0.90, 'exact_core'

    # Exact match with camelCase split
    if query_core_camel == ch_core:
        return 0.90, 'exact_core_camel'

    # Level 3: Word-based matching (try both original and camelCase split)
    query_words = set(query_core.split())
    query_words_camel = set(query_core_camel.split())
    ch_words = set(ch_core.split())

    # Use whichever query word set gives better overlap
    if len(query_words_camel & ch_words) > len(query_words & ch_words):
        query_words = query_words_camel

    if not query_words or not ch_words:
        return 0.0, 'no_words'

    # Check if query words are a subset of CH words (trading name → full legal name)
    if query_words <= ch_words:
        # All query words found in CH name
        coverage = len(query_words) / len(ch_words)
        # Higher confidence if query covers more of the CH name
        if coverage >= 0.5:
            return 0.88, f'query_subset_{coverage:.0%}'
        else:
            return 0.80, f'query_subset_{coverage:.0%}'

    # Check if CH words are a subset of query words (unlikely but handle it)
    if ch_words <= query_words:
        coverage = len(ch_words) / len(query_words)
        if coverage >= 0.5:
            return 0.85, f'ch_subset_{coverage:.0%}'
        else:
            return 0.75, f'ch_subset_{coverage:.0%}'

    # Level 4: Jaccard similarity on words
    intersection = len(query_words & ch_words)
    union = len(query_words | ch_words)
    jaccard = intersection / union if union > 0 else 0.0

    if jaccard >= 0.5:
        return 0.75 + (jaccard * 0.15), f'jaccard_{jaccard:.0%}'

    # Level 5: Check if first word matches (common for trading names)
    query_first = query_core.split()[0] if query_core else ''
    ch_first = ch_core.split()[0] if ch_core else ''

    if query_first and ch_first and query_first == ch_first:
        # First word matches - moderate confidence
        return 0.70, 'first_word_match'

    # Level 6: Prefix matching (query is prefix of CH name)
    if ch_norm.startswith(query_norm) and len(query_norm) >= 4:
        return 0.75, 'prefix_match'

    # No good match found
    return jaccard * 0.6, f'low_jaccard_{jaccard:.0%}'


def detect_partial_match(org_name: str, ch_name: str) -> Tuple[bool, float]:
    """
    Detect if this appears to be a partial match to a concatenated org name.

    Returns:
        Tuple of (is_partial, penalty_factor)
        - is_partial: True if match appears to be partial
        - penalty_factor: Multiplier to apply to confidence (0.0-1.0)
    """
    # Normalize names for comparison
    org_norm = normalize_company_name(org_name, strip_legal=True, strip_common=False).lower()
    ch_norm = normalize_company_name(ch_name, strip_legal=True, strip_common=False).lower()

    # Get significant words (length >= 3, not common filler words)
    filler_words = {'the', 'and', 'for', 'of', 'ltd', 'plc', 'llp', 'inc', 'limited', 'uk', 'group'}
    org_words = [w for w in org_norm.split() if len(w) >= 3 and w not in filler_words]
    ch_words = [w for w in ch_norm.split() if len(w) >= 3 and w not in filler_words]

    if len(org_words) < 2 or len(ch_words) < 1:
        return False, 1.0

    # Count how many org words appear in CH name
    org_words_in_ch = sum(1 for w in org_words if w in ch_norm)
    match_ratio = org_words_in_ch / len(org_words)
    unmatched_count = len(org_words) - org_words_in_ch

    # Check for 2+ unmatched words (key indicator of partial match per data quality report)
    if unmatched_count >= 2:
        return True, 0.7  # Significant penalty

    # If less than 60% of org words are in CH name, likely partial match
    if match_ratio < 0.6 and len(org_words) >= 4:
        # Severe penalty for very low match ratio
        return True, 0.7  # 30% penalty
    elif match_ratio < 0.75 and len(org_words) >= 3:
        # Moderate penalty
        return True, 0.85  # 15% penalty

    # Check for specific concatenation patterns
    # Pattern: First half of words match OR second half of words match (but not both)
    first_half = org_words[:len(org_words)//2]
    second_half = org_words[len(org_words)//2:]

    first_half_matches = sum(1 for w in first_half if w in ch_norm) / max(len(first_half), 1)
    second_half_matches = sum(1 for w in second_half if w in ch_norm) / max(len(second_half), 1)

    # If one half matches well but other doesn't, likely concatenated
    if (first_half_matches > 0.8 and second_half_matches < 0.3) or \
       (second_half_matches > 0.8 and first_half_matches < 0.3):
        return True, 0.75  # 25% penalty

    return False, 1.0


logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of matching an organization to Companies House."""
    org: 'models.Organization'
    company_number: Optional[str]
    company_profile: Optional[CompanyProfile]
    confidence: float
    match_reason: str
    matched_on: str  # What we matched on (exact name, normalized name, etc.)
    search_results_count: int = 0
    has_tie: bool = False  # True if multiple results had same top confidence
    tie_count: int = 1  # Number of results with same top confidence
    tie_companies: Optional[List[dict]] = None  # Tied results: [{company_number, company_name, confidence}, ...]

    @property
    def is_match(self) -> bool:
        return self.company_number is not None and self.confidence >= 0.75


class CompaniesHouseMatcher:
    """
    Matches Organization records to Companies House companies.

    Uses a multi-strategy approach to find the best match:
    1. Check if org already has a CH identifier
    2. Search by name and look for exact matches
    3. Fall back to normalized name matching
    4. Use fuzzy matching for close matches
    """

    # Company type mappings for validation
    COMPANY_TYPE_CLASSIFICATIONS = {
        'ltd': 'Private Limited Company',
        'private-limited-guarant-nsc': 'Private Limited by Guarantee',
        'private-limited-guarant-nsc-limited-exemption': 'Private Limited by Guarantee',
        'plc': 'Public Limited Company',
        'llp': 'Limited Liability Partnership',
        'registered-society-non-jurisdictional': 'Registered Society',
        'charitable-incorporated-organisation': 'Charitable Incorporated Organisation',
        'scottish-charitable-incorporated-organisation': 'Scottish CIO',
        'industrial-and-provident-society': 'Industrial and Provident Society',
        'royal-charter': 'Royal Charter Company',
        'limited-partnership': 'Limited Partnership',
        'private-unlimited': 'Private Unlimited Company',
        'old-public-company': 'Old Public Company',
        'scottish-partnership': 'Scottish Partnership',
        'unregistered-company': 'Unregistered Company',
    }

    def __init__(self, client: Optional[CompaniesHouseClient] = None,
                 min_confidence: float = 0.75,
                 dry_run: bool = False):
        """
        Initialize the matcher.

        Args:
            client: CompaniesHouseClient instance. Created if not provided.
            min_confidence: Minimum confidence score for a match (0.0-1.0)
            dry_run: If True, don't create ActorResolution records
        """
        self.client = client or CompaniesHouseClient()
        self.min_confidence = min_confidence
        self.dry_run = dry_run

        # Statistics
        self.stats = {
            'orgs_processed': 0,
            'already_has_identifier': 0,
            'exact_matches': 0,
            'normalized_matches': 0,
            'ch_matches': 0,  # CH-specific matching (trading names)
            'fuzzy_matches': 0,
            'no_match': 0,
            'api_errors': 0,
            'duplicates_found': 0,
        }

    def match_organization(self, org: 'models.Organization',
                          refresh: bool = False) -> MatchResult:
        """
        Match a single organization to Companies House.

        Args:
            org: Organization to match
            refresh: Force API refresh even if cached

        Returns:
            MatchResult with match details
        """
        self.stats['orgs_processed'] += 1

        # Strategy 1: Check for existing CH identifier
        existing_id = self._get_existing_ch_identifier(org)
        if existing_id:
            self.stats['already_has_identifier'] += 1
            profile = self.client.get_company(existing_id, refresh=refresh)
            return MatchResult(
                org=org,
                company_number=existing_id,
                company_profile=profile,
                confidence=1.0,
                match_reason='identifier',
                matched_on=f"Existing identifier: {existing_id}"
            )

        # Strategy 2-4: Search by name
        org_name = org.name
        if not org_name:
            return MatchResult(
                org=org,
                company_number=None,
                company_profile=None,
                confidence=0.0,
                match_reason='no_name',
                matched_on="Organization has no name"
            )

        # Search Companies House
        search_results = self.client.search_companies(org_name, refresh=refresh)

        if not search_results:
            self.stats['no_match'] += 1
            return MatchResult(
                org=org,
                company_number=None,
                company_profile=None,
                confidence=0.0,
                match_reason='no_results',
                matched_on=f"No search results for: {org_name}",
                search_results_count=0
            )

        # Try matching strategies
        match = self._find_best_match(org_name, search_results)

        if match:
            (company_number, confidence, match_reason, matched_on,
             has_tie, tie_count, tie_companies) = match

            # Update stats
            if match_reason == 'exact':
                self.stats['exact_matches'] += 1
            elif match_reason == 'normalized':
                self.stats['normalized_matches'] += 1
            elif match_reason == 'ch_match':
                self.stats['ch_matches'] += 1
            elif match_reason == 'fuzzy':
                self.stats['fuzzy_matches'] += 1

            # Get full company profile
            profile = self.client.get_company(company_number, refresh=refresh)

            # Check for duplicates (same company number on different orgs)
            if not self.dry_run:
                self._check_for_duplicates(org, company_number, confidence)

            return MatchResult(
                org=org,
                company_number=company_number,
                company_profile=profile,
                confidence=confidence,
                match_reason=match_reason,
                matched_on=matched_on,
                search_results_count=len(search_results),
                has_tie=has_tie,
                tie_count=tie_count,
                tie_companies=tie_companies
            )

        self.stats['no_match'] += 1
        return MatchResult(
            org=org,
            company_number=None,
            company_profile=None,
            confidence=0.0,
            match_reason='no_confident_match',
            matched_on=f"No match above {self.min_confidence} confidence",
            search_results_count=len(search_results)
        )

    def _get_existing_ch_identifier(self, org: 'models.Organization') -> Optional[str]:
        """Check if org already has a Companies House identifier."""
        try:
            identifier = models.Identifier.objects.filter(
                content_type__model='organization',
                object_id=org.pk,
                scheme='uk.gov.companieshouse'
            ).first()
            return identifier.identifier if identifier else None
        except Exception as e:
            logger.error(f"Error checking identifier for {org.pk}: {e}")
            return None

    def _find_best_match(self, org_name: str,
                        results: List[CompanySearchResult]
                        ) -> Optional[Tuple[str, float, str, str, bool, int, List[str]]]:
        """
        Find the best match from search results.

        Uses CH-specific matching that handles:
        - Trading names vs legal names ("Grayling" → "Grayling Communications Limited")
        - Legal suffix variations (Ltd, Limited, PLC, LLP)
        - Common business words (UK, International, Group, Holdings)

        Returns:
            Tuple of (company_number, confidence, match_reason, matched_on,
                     has_tie, tie_count, tie_companies) or None
        """
        org_name_normalized = normalize_actor_name(org_name, strength='strong')
        org_name_weak = normalize_actor_name(org_name, strength='weak')

        # Track all matches with their scores
        all_matches = []

        for result in results:
            # Skip dissolved companies unless explicitly looking for them
            if result.company_status == 'dissolved':
                continue

            result_name = result.title
            result_name_normalized = normalize_actor_name(result_name, strength='strong')
            result_name_weak = normalize_actor_name(result_name, strength='weak')

            match_info = None

            # Strategy 2: Exact match (case-insensitive)
            if org_name_normalized.lower() == result_name_normalized.lower():
                confidence = 0.95
                match_info = (result.company_number, confidence, 'exact',
                             f"Exact: '{org_name}' == '{result_name}'", result_name)

            # Strategy 3: Normalized match (weak normalization)
            elif org_name_weak == result_name_weak:
                confidence = 0.85
                match_info = (result.company_number, confidence, 'normalized',
                             f"Normalized: '{org_name_weak}'", result_name)

            # Strategy 4: CH-specific similarity (handles trading names)
            else:
                ch_similarity, ch_reason = calculate_ch_similarity(org_name, result_name)
                if ch_similarity >= self.min_confidence:
                    match_info = (result.company_number, ch_similarity, 'ch_match',
                                 f"CH ({ch_reason}): '{org_name}' → '{result_name}'", result_name)
                else:
                    # Strategy 5: Generic fuzzy match (fallback)
                    similarity = calculate_name_similarity(org_name, result_name)
                    if similarity >= self.min_confidence:
                        confidence = min(0.80, similarity * 0.85)  # Cap at 0.80 for fuzzy
                        match_info = (result.company_number, confidence, 'fuzzy',
                                     f"Fuzzy ({similarity:.2f}): '{org_name}' ~ '{result_name}'", result_name)

            if match_info:
                all_matches.append(match_info)

        if not all_matches:
            return None

        # Find the best confidence score
        best_confidence = max(m[1] for m in all_matches)

        if best_confidence < self.min_confidence:
            return None

        # For TIE DETECTION, use CH similarity to get CONSISTENT scoring
        # (Different matching strategies may assign different scores for equivalent matches)
        # Re-compute CH similarity for all matches to detect true ties
        ch_scores = []
        for m in all_matches:
            company_number, conf, reason, matched_on, ch_name = m
            ch_sim, _ = calculate_ch_similarity(org_name, ch_name)
            ch_scores.append((m, ch_sim))

        # Find best CH similarity score
        best_ch_score = max(cs[1] for cs in ch_scores)

        # Find all matches at the best CH similarity level (ties)
        # Use a small tolerance (0.01) to catch near-ties
        tie_tolerance = 0.01
        tie_candidates = [cs for cs in ch_scores if cs[1] >= best_ch_score - tie_tolerance]

        # Sort by original confidence descending, then by company number for consistency
        all_matches.sort(key=lambda m: (-m[1], m[0]))

        best_match = all_matches[0]
        company_number, confidence, match_reason, matched_on, ch_name = best_match

        # Check for ties using CH similarity scores
        has_tie = len(tie_candidates) > 1
        tie_count = len(tie_candidates)
        tie_companies = [
            {
                'company_number': cs[0][0],
                'company_name': cs[0][4],
                'confidence': cs[1],  # Use CH similarity score for display
                'match_reason': cs[0][2],
            }
            for cs in sorted(tie_candidates, key=lambda x: (-x[1], x[0][0]))
        ] if has_tie else None

        # Apply partial match penalty for concatenated names
        is_partial, penalty = detect_partial_match(org_name, ch_name)
        if is_partial:
            confidence *= penalty
            match_reason = f"{match_reason}_partial"
            matched_on = f"{matched_on} [PARTIAL: {penalty:.0%}]"

        return (company_number, confidence, match_reason, matched_on,
                has_tie, tie_count, tie_companies)

    def _check_for_duplicates(self, org: 'models.Organization',
                             company_number: str, confidence: float) -> None:
        """
        Check if another org already has this company number.

        If so, create or update an ActorResolution record for deduplication.
        Uses get_or_create with consistent ordering (lower ID first) to avoid
        duplicate key errors.
        """
        # Find other orgs with this company number
        existing = models.Identifier.objects.filter(
            scheme='uk.gov.companieshouse',
            identifier=company_number
        ).exclude(
            object_id=org.pk
        ).select_related('content_type')

        for identifier in existing:
            try:
                other_org = identifier.content_object
                if not other_org or not isinstance(other_org, models.Organization):
                    continue

                # Ensure consistent ordering (lower ID first) to match unique constraint
                if org.pk < other_org.pk:
                    actor1, actor2 = org, other_org
                else:
                    actor1, actor2 = other_org, org

                # Determine which should be canonical (more data = better)
                canonical = self._choose_canonical(org, other_org)

                # Use get_or_create to avoid duplicate key errors
                resolution, created = models.ActorResolution.objects.get_or_create(
                    actor1=actor1,
                    actor2=actor2,
                    defaults={
                        'canonical_actor': canonical,
                        'confidence': 1.0,  # Identifier match = highest confidence
                        'decision': 'auto_merge',
                        'match_reason': 'identifier',
                        'notes': f"Same Companies House number: {company_number}"
                    }
                )

                if created:
                    self.stats['duplicates_found'] += 1
                    logger.info(
                        f"Found duplicate: {org.name} <-> {other_org.name} "
                        f"(CH: {company_number})"
                    )

            except Exception as e:
                logger.error(f"Error creating resolution: {e}")

    def _choose_canonical(self, org1: 'models.Organization',
                         org2: 'models.Organization') -> 'models.Organization':
        """
        Choose which organization should be canonical.

        Prefers the one with more data/relationships.
        """
        # Count relationships for each
        def score(org):
            score = 0
            # Has more identifiers
            score += org.identifiers.count() * 2
            # Has other names
            score += org.other_names.count()
            # Has contact details
            score += org.contact_details.count()
            # Is part of consultancies (lobbying client)
            score += models.Consultancy.objects.filter(client=org).count()
            # Is lobbying agency
            score += models.Consultancy.objects.filter(agency=org).count()
            # Has donations
            score += models.Donation.objects.filter(donor=org).count()
            score += models.Donation.objects.filter(recipient=org).count()
            return score

        return org1 if score(org1) >= score(org2) else org2

    def get_stats(self) -> dict:
        """Return matching statistics."""
        return self.stats.copy()

    def log_stats(self) -> None:
        """Log matching statistics."""
        logger.info("=== Companies House Matching Statistics ===")
        logger.info(f"Organizations processed: {self.stats['orgs_processed']}")
        logger.info(f"Already had identifier: {self.stats['already_has_identifier']}")
        logger.info(f"Exact matches: {self.stats['exact_matches']}")
        logger.info(f"Normalized matches: {self.stats['normalized_matches']}")
        logger.info(f"CH-specific matches: {self.stats['ch_matches']}")
        logger.info(f"Fuzzy matches: {self.stats['fuzzy_matches']}")
        logger.info(f"No match found: {self.stats['no_match']}")
        logger.info(f"API errors: {self.stats['api_errors']}")
        logger.info(f"Duplicates found: {self.stats['duplicates_found']}")


def get_company_type_classification(company_type: str) -> str:
    """
    Convert Companies House company type code to human-readable classification.

    Args:
        company_type: Companies House type code (e.g., 'ltd', 'plc')

    Returns:
        Human-readable classification for Organization.classification field
    """
    return CompaniesHouseMatcher.COMPANY_TYPE_CLASSIFICATIONS.get(
        company_type,
        company_type.replace('-', ' ').title()  # Fallback: titlecase the code
    )


def normalize_company_number(number: str) -> str:
    """
    Normalize a Companies House company number.

    Args:
        number: Raw company number (e.g., '123456', 'SC123456')

    Returns:
        Normalized 8-character company number
    """
    if not number:
        return ''

    # Remove any whitespace
    number = number.strip()

    # Handle Scottish/Northern Irish prefixes
    if number[:2].upper() in ('SC', 'NI', 'OC', 'SO', 'NC'):
        prefix = number[:2].upper()
        rest = number[2:].zfill(6)
        return prefix + rest

    # Standard company number - pad to 8 digits
    return number.zfill(8)

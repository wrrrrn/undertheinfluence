"""
Director/PSC Matcher

Matches Companies House officers and PSCs to existing Person/Organization records.

Matching strategies (in order):
1. Existing CH identifier (officer_id or psc_id) - exact match
2. Name + DOB match (for PSCs with partial DOB)
3. Exact normalized name match
4. Create new if no match

Confidence scoring (all auto-approved ≥0.75):
- Identifier match: 1.0
- Name + DOB match: 0.95
- Exact name match: 0.85
- Created new: 0.75
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from django.contrib.contenttypes.models import ContentType

from datafetch import models
from datafetch.helpers import parse_ch_officer_name
from datafetch.services.companies_house_client import (
    CompanyOfficer,
    PersonWithSignificantControl,
)
from datafetch.utils.normalization import normalize_actor_name

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of matching a director/PSC to an Actor."""
    actor: Optional['models.Actor']
    confidence: float
    match_reason: str
    created: bool = False

    @property
    def is_match(self) -> bool:
        return self.actor is not None


class DirectorMatcher:
    """
    Match CH officers/PSCs to existing Person/Organization records.

    Matching strategies (in order):
    1. Existing CH identifier (officer_id or psc_id)
    2. Exact normalized name match
    3. Family name + given name + DOB match (for PSCs with DOB)
    4. Create new if no match

    All matches ≥0.75 are auto-approved (faster processing, cleanup false matches later).
    """

    # Identifier schemes for CH data
    OFFICER_SCHEME = 'uk.gov.companieshouse.officer'
    PSC_SCHEME = 'uk.gov.companieshouse.psc'

    def __init__(self, dry_run: bool = False):
        """
        Initialize the matcher.

        Args:
            dry_run: If True, don't create new actors
        """
        self.dry_run = dry_run

        # Statistics for reporting
        self.stats = {
            'identifier_matches': 0,
            'name_dob_matches': 0,
            'exact_name_matches': 0,
            'created_persons': 0,
            'created_organizations': 0,
            'processed': 0,
        }

    def match_officer(self, officer: CompanyOfficer) -> MatchResult:
        """
        Match a Companies House officer to an existing Actor.

        Args:
            officer: CompanyOfficer from CH API

        Returns:
            MatchResult with matched or newly created actor
        """
        self.stats['processed'] += 1

        # Strategy 1: Check for existing CH officer identifier
        if officer.officer_id:
            existing = self._find_by_identifier(
                officer.officer_id,
                self.OFFICER_SCHEME
            )
            if existing:
                self.stats['identifier_matches'] += 1
                return MatchResult(
                    actor=existing,
                    confidence=1.0,
                    match_reason='identifier',
                    created=False
                )

        # Parse the name
        parsed = parse_ch_officer_name(officer.name)

        if officer.is_corporate or parsed['is_corporate']:
            # Corporate director - match as Organization
            return self._match_corporate_officer(officer, parsed)
        else:
            # Individual - match as Person
            return self._match_individual_officer(officer, parsed)

    def match_psc(self, psc: PersonWithSignificantControl) -> MatchResult:
        """
        Match a PSC (beneficial owner) to an existing Actor.

        Args:
            psc: PersonWithSignificantControl from CH API

        Returns:
            MatchResult with matched or newly created actor
        """
        self.stats['processed'] += 1

        # Strategy 1: Check for existing CH PSC identifier
        if psc.psc_id:
            existing = self._find_by_identifier(
                psc.psc_id,
                self.PSC_SCHEME
            )
            if existing:
                self.stats['identifier_matches'] += 1
                return MatchResult(
                    actor=existing,
                    confidence=1.0,
                    match_reason='identifier',
                    created=False
                )

        if psc.is_corporate:
            # Corporate PSC - match as Organization
            return self._match_corporate_psc(psc)
        else:
            # Individual PSC - match as Person
            return self._match_individual_psc(psc)

    def _find_by_identifier(
        self,
        identifier_value: str,
        scheme: str
    ) -> Optional['models.Actor']:
        """Find an Actor by CH identifier."""
        try:
            identifier = models.Identifier.objects.filter(
                scheme=scheme,
                identifier=identifier_value
            ).select_related('content_type').first()

            if identifier:
                return identifier.content_object
            return None
        except Exception as e:
            logger.warning(f"Error finding identifier {scheme}:{identifier_value}: {e}")
            return None

    def _match_individual_officer(
        self,
        officer: CompanyOfficer,
        parsed: dict
    ) -> MatchResult:
        """Match an individual officer to a Person."""
        full_name = parsed['name']
        family_name = parsed['family_name']
        given_name = parsed['given_name']

        # Strategy 2: Exact name match
        existing = self._find_person_by_name(full_name, family_name, given_name)
        if existing:
            self.stats['exact_name_matches'] += 1
            return MatchResult(
                actor=existing,
                confidence=0.85,
                match_reason='exact_name',
                created=False
            )

        # Strategy 3: Name + DOB match (if DOB available)
        if officer.date_of_birth and family_name:
            existing = self._find_person_by_name_and_dob(
                family_name, given_name, officer.date_of_birth
            )
            if existing:
                self.stats['name_dob_matches'] += 1
                return MatchResult(
                    actor=existing,
                    confidence=0.95,
                    match_reason='name_dob',
                    created=False
                )

        # Strategy 4: Create new Person
        if self.dry_run:
            return MatchResult(
                actor=None,
                confidence=0.75,
                match_reason='would_create',
                created=False
            )

        person = self._create_person(
            full_name, family_name, given_name,
            officer.officer_id, self.OFFICER_SCHEME,
            nationality=officer.nationality,
            date_of_birth=officer.date_of_birth
        )
        self.stats['created_persons'] += 1
        return MatchResult(
            actor=person,
            confidence=0.75,
            match_reason='created',
            created=True
        )

    def _match_corporate_officer(
        self,
        officer: CompanyOfficer,
        parsed: dict
    ) -> MatchResult:
        """Match a corporate director to an Organization."""
        name = parsed['name'] if parsed['name'] else officer.name

        # Strategy 2: Exact name match
        existing = self._find_organization_by_name(name)
        if existing:
            self.stats['exact_name_matches'] += 1
            return MatchResult(
                actor=existing,
                confidence=0.85,
                match_reason='exact_name',
                created=False
            )

        # Strategy 3: Create new Organization
        if self.dry_run:
            return MatchResult(
                actor=None,
                confidence=0.75,
                match_reason='would_create',
                created=False
            )

        org = self._create_organization(
            name, 'Corporate Director',
            officer.officer_id, self.OFFICER_SCHEME
        )
        self.stats['created_organizations'] += 1
        return MatchResult(
            actor=org,
            confidence=0.75,
            match_reason='created',
            created=True
        )

    def _match_individual_psc(self, psc: PersonWithSignificantControl) -> MatchResult:
        """Match an individual PSC to a Person."""
        # Parse PSC name - format may vary
        parsed = parse_ch_officer_name(psc.name)
        full_name = parsed['name'] if parsed['name'] else psc.name
        family_name = parsed['family_name']
        given_name = parsed['given_name']

        # If parsing failed (corporate detection), try direct name
        if parsed['is_corporate']:
            # PSC marked as individual but name looks corporate - use raw name
            full_name = psc.name.title()
            family_name = ''
            given_name = ''

        # Strategy 2: Name + DOB match (PSCs often have partial DOB)
        if psc.date_of_birth and family_name:
            existing = self._find_person_by_name_and_dob(
                family_name, given_name, psc.date_of_birth
            )
            if existing:
                self.stats['name_dob_matches'] += 1
                return MatchResult(
                    actor=existing,
                    confidence=0.95,
                    match_reason='name_dob',
                    created=False
                )

        # Strategy 3: Exact name match
        existing = self._find_person_by_name(full_name, family_name, given_name)
        if existing:
            self.stats['exact_name_matches'] += 1
            return MatchResult(
                actor=existing,
                confidence=0.85,
                match_reason='exact_name',
                created=False
            )

        # Strategy 4: Create new Person
        if self.dry_run:
            return MatchResult(
                actor=None,
                confidence=0.75,
                match_reason='would_create',
                created=False
            )

        person = self._create_person(
            full_name, family_name, given_name,
            psc.psc_id, self.PSC_SCHEME,
            nationality=psc.nationality,
            date_of_birth=psc.date_of_birth
        )
        self.stats['created_persons'] += 1
        return MatchResult(
            actor=person,
            confidence=0.75,
            match_reason='created',
            created=True
        )

    def _match_corporate_psc(self, psc: PersonWithSignificantControl) -> MatchResult:
        """Match a corporate PSC to an Organization."""
        name = psc.name.strip()

        # Strategy 2: Exact name match
        existing = self._find_organization_by_name(name)
        if existing:
            self.stats['exact_name_matches'] += 1
            return MatchResult(
                actor=existing,
                confidence=0.85,
                match_reason='exact_name',
                created=False
            )

        # Strategy 3: Create new Organization
        if self.dry_run:
            return MatchResult(
                actor=None,
                confidence=0.75,
                match_reason='would_create',
                created=False
            )

        org = self._create_organization(
            name, 'Corporate Beneficial Owner',
            psc.psc_id, self.PSC_SCHEME
        )
        self.stats['created_organizations'] += 1
        return MatchResult(
            actor=org,
            confidence=0.75,
            match_reason='created',
            created=True
        )

    def _find_person_by_name(
        self,
        full_name: str,
        family_name: str,
        given_name: str
    ) -> Optional['models.Person']:
        """Find a Person by name."""
        # Normalize for comparison
        normalized_name = normalize_actor_name(full_name, strength='strong')

        # Try exact match on full name first
        person = models.Person.objects.filter(
            name__iexact=full_name
        ).first()
        if person:
            return person

        # Try family_name + given_name match
        if family_name and given_name:
            person = models.Person.objects.filter(
                family_name__iexact=family_name,
                given_name__iexact=given_name
            ).first()
            if person:
                return person

        # Try normalized name match via other_names
        person_ct = ContentType.objects.get_for_model(models.Person)
        other_name = models.OtherName.objects.filter(
            content_type=person_ct,
            name__iexact=normalized_name,
            alias_type='strong'
        ).first()
        if other_name:
            return other_name.content_object

        return None

    def _find_person_by_name_and_dob(
        self,
        family_name: str,
        given_name: str,
        date_of_birth: dict
    ) -> Optional['models.Person']:
        """
        Find a Person by name and partial date of birth.

        CH provides partial DOB: {month: int, year: int}
        """
        if not date_of_birth:
            return None

        month = date_of_birth.get('month')
        year = date_of_birth.get('year')

        if not year:
            return None

        # Build partial DOB string (YYYY-MM format)
        if month:
            dob_prefix = f"{year}-{month:02d}"
        else:
            dob_prefix = str(year)

        # Search for matching person
        persons = models.Person.objects.filter(
            family_name__iexact=family_name,
            birth_date__startswith=dob_prefix
        )

        # If given_name provided, filter further
        if given_name:
            persons = persons.filter(given_name__iexact=given_name)

        return persons.first()

    def _find_organization_by_name(
        self,
        name: str
    ) -> Optional['models.Organization']:
        """Find an Organization by name."""
        # Try exact match
        org = models.Organization.objects.filter(
            name__iexact=name
        ).first()
        if org:
            return org

        # Try normalized name
        normalized = normalize_actor_name(name, strength='strong')
        org = models.Organization.objects.filter(
            name__iexact=normalized
        ).first()
        if org:
            return org

        # Try via other_names
        org_ct = ContentType.objects.get_for_model(models.Organization)
        other_name = models.OtherName.objects.filter(
            content_type=org_ct,
            name__iexact=name
        ).first()
        if other_name:
            return other_name.content_object

        return None

    def _create_person(
        self,
        full_name: str,
        family_name: str,
        given_name: str,
        ch_id: str,
        ch_scheme: str,
        nationality: Optional[str] = None,
        date_of_birth: Optional[dict] = None
    ) -> 'models.Person':
        """Create a new Person with CH identifier."""
        person = models.Person.objects.create(
            name=full_name,
            family_name=family_name,
            given_name=given_name,
            national_identity=nationality or '',
        )

        # Add CH identifier if provided
        if ch_id:
            person_ct = ContentType.objects.get_for_model(models.Person)
            models.Identifier.objects.create(
                content_type=person_ct,
                object_id=person.pk,
                scheme=ch_scheme,
                identifier=ch_id
            )

        # Add normalized name as other_name for future matching
        normalized = normalize_actor_name(full_name, strength='strong')
        if normalized.lower() != full_name.lower():
            person_ct = ContentType.objects.get_for_model(models.Person)
            models.OtherName.objects.create(
                content_type=person_ct,
                object_id=person.pk,
                name=normalized,
                alias_type='strong',
                note='Normalized name for matching'
            )

        logger.debug(f"Created Person: {full_name} (ID: {person.pk})")
        return person

    def _create_organization(
        self,
        name: str,
        classification: str,
        ch_id: str,
        ch_scheme: str
    ) -> 'models.Organization':
        """Create a new Organization with CH identifier."""
        org = models.Organization.objects.create(
            name=name,
            classification=classification
        )

        # Add CH identifier if provided
        if ch_id:
            org_ct = ContentType.objects.get_for_model(models.Organization)
            models.Identifier.objects.create(
                content_type=org_ct,
                object_id=org.pk,
                scheme=ch_scheme,
                identifier=ch_id
            )

        # Add normalized name as other_name for future matching
        normalized = normalize_actor_name(name, strength='strong')
        if normalized.lower() != name.lower():
            org_ct = ContentType.objects.get_for_model(models.Organization)
            models.OtherName.objects.create(
                content_type=org_ct,
                object_id=org.pk,
                name=normalized,
                alias_type='strong',
                note='Normalized name for matching'
            )

        logger.debug(f"Created Organization: {name} (ID: {org.pk})")
        return org

    def get_stats(self) -> dict:
        """Return matching statistics."""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        for key in self.stats:
            self.stats[key] = 0

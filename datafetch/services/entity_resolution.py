"""
Entity Resolution Service for UnderTheInfluence.

Application-wide service for entity resolution that serves:
- Import commands (auto-resolve new records)
- Cleanup commands (backfill existing records)
- API views (cross-dataset queries)

Phase 3.2 Implementation - Comprehensive Entity Resolution

Resolution Strategy (Multi-Pass):
1. Identifier-based (confidence: 1.0) - Match by CH number, EC donor ID, etc.
2. Exact name match (confidence: 0.95) - Exact name after normalization
3. Strong normalization match (confidence: 0.85) - Conservative normalization
4. Weak normalization match (confidence: 0.70) - Aggressive normalization

Usage:
    from datafetch.services.entity_resolution import EntityResolutionService

    service = EntityResolutionService()

    # During import - resolve and link new records
    service.resolve_and_link(meeting_attendee, 'canonical_actor_id')

    # During cleanup - backfill canonical fields
    canonical = service.resolve(actor)

    # Merge duplicates
    service.merge_actors(source=duplicate_actor, target=canonical_actor)
"""

import logging
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass

from django.db import models, transaction
from django.db.models import Count, Sum, Q, F
from django.contrib.contenttypes.models import ContentType

from datafetch.utils.normalization import normalize_actor_name, build_search_key

logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of an entity resolution attempt."""
    canonical: Optional['models.Actor']
    confidence: float
    match_reason: str
    details: str = ''

    @property
    def is_resolved(self) -> bool:
        return self.canonical is not None and self.confidence >= 0.70


class EntityResolutionService:
    """
    Application-wide entity resolution service.

    Serves the WHOLE APPLICATION - import, cleanup, queries.
    Called automatically when new records are created or during cleanup.
    """

    # Confidence thresholds
    CONFIDENCE_IDENTIFIER = 1.0  # External ID match
    CONFIDENCE_EC_DONOR = 0.95   # Electoral Commission donor ID match
    CONFIDENCE_EXACT = 0.95      # Exact name match
    CONFIDENCE_OTHERNAME_STRONG = 0.90  # Strong alias (abbreviation, trade name)
    CONFIDENCE_STRONG = 0.85     # Strong normalization
    CONFIDENCE_OTHERNAME_WEAK = 0.75    # Weak alias (former name, nickname)
    CONFIDENCE_WEAK = 0.70       # Weak normalization

    # Minimum confidence to auto-link
    MIN_CONFIDENCE_AUTO = 0.85

    def __init__(self, fast_mode: bool = False, skip_scoring: bool = False):
        """
        Initialize the service.

        Args:
            fast_mode: If True, only do identifier + exact name matching (skip slow fuzzy)
            skip_scoring: If True, skip expensive entity scoring (take first match)
        """
        self._cache: Dict[str, 'models.Actor'] = {}
        self._score_cache: Dict[int, int] = {}
        self._name_index: Dict[str, List['models.Actor']] = {}
        self._id_index: Dict[Tuple[str, str], 'models.Actor'] = {}
        self._actor_by_id: Dict[int, 'models.Actor'] = {}  # pk -> Actor for O(1) lookups
        # Phase 3.2 indexes for improved resolution
        self._othername_index: Dict[str, List[Tuple[int, str]]] = {}  # name.lower() -> [(actor_id, alias_type)]
        self._ch_index: Dict[str, int] = {}  # company_number -> canonical_org_id (lowest ID)
        self._ec_actor_index: Dict[str, List[int]] = {}  # ec_ref -> [actor_ids]
        self.fast_mode = fast_mode
        self.skip_scoring = skip_scoring or fast_mode  # fast mode implies skip scoring
        self.stats = {
            'identifier_matches': 0,
            'ec_id_matches': 0,
            'exact_matches': 0,
            'othername_strong_matches': 0,
            'strong_matches': 0,
            'othername_weak_matches': 0,
            'weak_matches': 0,
            'no_match': 0,
            'cache_hits': 0,
        }

    def prefetch_all_actors(self):
        """
        Build an in-memory index of all actors for lightning-fast resolution.

        This avoids thousands of individual database queries during batch processing.
        Builds multiple indexes:
        - _name_index: name.lower() -> [actors]
        - _othername_index: alias.lower() -> [(actor_id, alias_type)]
        - _ch_index: company_number -> canonical_org_id (lowest ID)
        - _ec_actor_index: ec_ref -> [actor_ids]
        """
        from datafetch.models import Actor, Identifier, CompaniesHouseMatch, OtherName, Person, Organization
        from django.contrib.contenttypes.models import ContentType
        from collections import defaultdict

        logger.info("Building in-memory actor indexes...")

        # Get content types for Person and Organization
        person_ct = ContentType.objects.get_for_model(Person)
        org_ct = ContentType.objects.get_for_model(Organization)
        actor_content_types = [person_ct, org_ct]

        # 1. Fetch all actors and build ID lookup
        all_actors = list(Actor.objects.all().only('id', 'name', 'polymorphic_ctype_id'))
        self._actor_by_id = {a.pk: a for a in all_actors}

        # 2. Build name index (for exact name matching)
        self._name_index = defaultdict(list)
        self._normalized_strong_index = defaultdict(list)
        self._normalized_weak_index = defaultdict(list)

        for actor in all_actors:
            self._name_index[actor.name.lower()].append(actor)
            
            # Build normalized indexes
            norm_strong = normalize_actor_name(actor.name, strength='strong')
            if norm_strong:
                self._normalized_strong_index[norm_strong].append(actor)
                
            norm_weak = normalize_actor_name(actor.name, strength='weak')
            if norm_weak:
                self._normalized_weak_index[norm_weak].append(actor)

        logger.info(f"  Name index: {len(all_actors)} actors")
        logger.info(f"  Normalized indexes: {len(self._normalized_strong_index)} strong, {len(self._normalized_weak_index)} weak")

        # 3. Build OtherName index (for alias matching)
        self._othername_index = defaultdict(list)
        othername_count = 0
        for on in OtherName.objects.filter(content_type__in=actor_content_types).values_list('name', 'object_id', 'note'):
            name_lower = on[0].lower() if on[0] else ''
            if name_lower:
                # Determine alias type from note field
                note = (on[2] or '').lower()
                if 'abbreviation' in note or 'trade' in note or 'trading' in note or 'aka' in note:
                    alias_type = 'strong'
                else:
                    alias_type = 'weak'  # former name, nickname, merged name
                self._othername_index[name_lower].append((on[1], alias_type))
                othername_count += 1
        logger.info(f"  OtherName index: {othername_count} aliases")

        # 4. Build Companies House index (canonical = lowest org_id for each CH number)
        self._ch_index = {}
        ch_matches = CompaniesHouseMatch.objects.filter(
            status__in=['approved', 'auto_approved']
        ).values_list('company_number', 'organization_id').order_by('organization_id')
        for company_number, org_id in ch_matches:
            # Keep the lowest org_id (first seen due to order_by) as canonical
            if company_number not in self._ch_index:
                self._ch_index[company_number] = org_id
        logger.info(f"  CH index: {len(self._ch_index)} unique company numbers")

        # 5. Build Electoral Commission actor index (for donor matching)
        self._ec_actor_index = defaultdict(list)
        ec_idents = Identifier.objects.filter(
            scheme='electoralcommission',
            content_type__in=actor_content_types
        ).values_list('identifier', 'object_id')
        for ec_ref, actor_id in ec_idents:
            self._ec_actor_index[ec_ref].append(actor_id)
        logger.info(f"  EC index: {len(self._ec_actor_index)} unique EC refs")

        logger.info("In-memory indexes built successfully.")

    def _get_actor_by_id(self, actor_id: int) -> Optional['models.Actor']:
        """Get actor by ID, using cache if available."""
        if self._actor_by_id:
            return self._actor_by_id.get(actor_id)
        from datafetch.models import Actor
        return Actor.objects.filter(pk=actor_id).first()

    def resolve(self, actor: 'models.Actor') -> Optional['models.Actor']:
        """
        Find the canonical actor for a given actor.

        Multi-pass resolution with confidence levels:
        1. By identifier (CH number, EC ID, ParlParse ID)
        2. By exact name match
        3. By normalized name match

        Args:
            actor: Actor to resolve

        Returns:
            Canonical actor if found, None otherwise
        """
        result = self.resolve_with_confidence(actor)
        return result.canonical if result.is_resolved else None

    def resolve_with_confidence(self, actor: 'models.Actor') -> ResolutionResult:
        """
        Resolve an actor with full confidence information.

        Args:
            actor: Actor to resolve

        Returns:
            ResolutionResult with canonical actor and confidence score
        """
        from datafetch.models import Actor, Identifier

        if not actor:
            return ResolutionResult(None, 0.0, 'no_actor', 'Actor is None')

        # Check cache first
        cache_key = f"{actor.pk}:{actor.name}"
        if cache_key in self._cache:
            self.stats['cache_hits'] += 1
            return ResolutionResult(
                self._cache[cache_key],
                self.CONFIDENCE_EXACT,
                'cache_hit'
            )

        # Pass 1: Identifier-based resolution (1.0 confidence)
        result = self._resolve_by_identifier(actor)
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['identifier_matches'] += 1
            return result

        # Pass 2: EC Donor ID resolution (0.95 confidence)
        result = self._resolve_by_ec_id(actor)
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['ec_id_matches'] += 1
            return result

        # Pass 3: Exact name match (0.95 confidence)
        result = self._resolve_by_exact_name(actor)
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['exact_matches'] += 1
            return result

        # Pass 4: Strong OtherName alias match (0.90 confidence)
        result = self._resolve_by_othername(actor, alias_type='strong')
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['othername_strong_matches'] += 1
            return result

        # Fast mode stops here (skip slow fuzzy matching)
        if self.fast_mode:
            self.stats['no_match'] += 1
            return ResolutionResult(None, 0.0, 'no_match_fast', f'No exact match (fast mode): {actor.name}')

        # Pass 5: Strong normalization match (0.85 confidence)
        result = self._resolve_by_normalized_name(actor, strength='strong')
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['strong_matches'] += 1
            return result

        # Pass 6: Weak OtherName alias match (0.75 confidence)
        result = self._resolve_by_othername(actor, alias_type='weak')
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['othername_weak_matches'] += 1
            return result

        # Pass 7: Weak normalization match (0.70 confidence)
        result = self._resolve_by_normalized_name(actor, strength='weak')
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['weak_matches'] += 1
            return result

        # No match found
        self.stats['no_match'] += 1
        return ResolutionResult(None, 0.0, 'no_match', f'No canonical found for: {actor.name}')

    def resolve_and_link(self, record: models.Model, target_field: str,
                         min_confidence: float = None) -> bool:
        """
        Resolve and set canonical field on a record.

        Args:
            record: Record with actor relationship (e.g., MeetingAttendee, Donation)
            target_field: Field name to set (e.g., 'canonical_actor_id')
            min_confidence: Minimum confidence for auto-linking (default: MIN_CONFIDENCE_AUTO)

        Returns:
            True if canonical was set, False otherwise
        """
        if min_confidence is None:
            min_confidence = self.MIN_CONFIDENCE_AUTO

        # Get the actor from the record
        # Try common field names
        actor = None
        for field_name in ['actor', 'donor', 'recipient', 'client', 'agency']:
            if hasattr(record, field_name):
                actor = getattr(record, field_name)
                if actor:
                    break

        if not actor:
            logger.debug(f"No actor found on record {record}")
            return False

        result = self.resolve_with_confidence(actor)

        if result.is_resolved and result.confidence >= min_confidence:
            # Don't link to self
            if result.canonical.pk != actor.pk:
                setattr(record, target_field, result.canonical.pk)
                record.save(update_fields=[target_field])
                logger.debug(f"Linked {actor.name} -> {result.canonical.name}")
                return True

        return False

    def calculate_entity_score(self, actor: 'models.Actor') -> int:
        """
        Score an actor by data richness for canonical selection.

        Higher score = better candidate for canonical status.

        Scoring criteria:
        - Has Companies House identifier: +50
        - Has Electoral Commission ID: +40
        - Has ParlParse ID: +30
        - Has donations: +20 per donation
        - Has meeting attendances: +10 per attendance
        - Has consultancy relationships: +15 per relationship
        - Has Membership records: +10 per membership
        - Organization type bonus: +100 (for org names typed as Org)

        Args:
            actor: Actor to score

        Returns:
            Integer score (higher = richer data)
        """
        if actor.pk in self._score_cache:
            return self._score_cache[actor.pk]

        from datafetch.models import (
            Identifier, Donation, MeetingAttendee, Consultancy, Membership, Organization
        )

        score = 0

        # Quality bonus: If it's correctly typed as an Organization and contains
        # organization keywords, give it a massive boost so it's preferred over
        # misclassified "Person" records with the same name.
        is_org = hasattr(actor, 'organization') or isinstance(actor, Organization)
        if is_org:
            org_keywords = ['party', 'union', 'ltd', 'limited', 'plc', 'llp', 'council', 'group', 'association', 'federation']
            name_lower = actor.name.lower()
            if any(kw in name_lower for kw in org_keywords):
                score += 100

        # Check identifiers
        identifiers = Identifier.objects.filter(
            content_type=ContentType.objects.get_for_model(actor.__class__),
            object_id=actor.pk
        )
        for ident in identifiers:
            if ident.scheme == 'uk.gov.companieshouse':
                score += 50
            elif ident.scheme == 'uk.gov.electoralcommission':
                score += 40
            elif ident.scheme == 'uk.org.publicwhip':
                score += 30
            else:
                score += 10

        # Count relationships
        donations_given = Donation.objects.filter(donor=actor).count()
        donations_received = Donation.objects.filter(recipient=actor).count()
        score += (donations_given + donations_received) * 20

        attendances = MeetingAttendee.objects.filter(actor=actor).count()
        score += attendances * 10

        consultancies = Consultancy.objects.filter(
            Q(client=actor) | Q(agency=actor)
        ).count()
        score += consultancies * 15

        # For Person actors, check memberships
        if hasattr(actor, 'person'):
            memberships = Membership.objects.filter(person=actor.person).count()
            score += memberships * 10

        self._score_cache[actor.pk] = score
        return score

    def merge_actors(self, source: 'models.Actor', target: 'models.Actor',
                     dry_run: bool = False) -> Dict[str, int]:
        """
        Merge source actor into target actor, updating all references.

        This is a DESTRUCTIVE operation that:
        1. Updates all relationships pointing to source to point to target
        2. Copies unique identifiers from source to target
        3. Creates OtherName for source's name on target
        4. Deletes the source actor

        Args:
            source: Actor to merge FROM (will be deleted)
            target: Actor to merge INTO (will be preserved)
            dry_run: If True, return what would happen without changes

        Returns:
            Dictionary of counts by relationship type
        """
        from datafetch.models import (
            Donation, MeetingAttendee, Consultancy, Membership,
            OtherName, Identifier, Note, CompaniesHouseMatch
        )

        counts = {
            'donations_donor': 0,
            'donations_recipient': 0,
            'meeting_attendees': 0,
            'consultancy_client': 0,
            'consultancy_agency': 0,
            'memberships': 0,
            'identifiers': 0,
            'other_names': 0,
        }

        if dry_run:
            # Count what would be updated
            counts['donations_donor'] = Donation.objects.filter(donor=source).count()
            counts['donations_recipient'] = Donation.objects.filter(recipient=source).count()
            counts['meeting_attendees'] = MeetingAttendee.objects.filter(actor=source).count()
            counts['consultancy_client'] = Consultancy.objects.filter(client=source).count()
            counts['consultancy_agency'] = Consultancy.objects.filter(agency=source).count()
            if hasattr(source, 'person'):
                counts['memberships'] = Membership.objects.filter(person=source.person).count()
            return counts

        with transaction.atomic():
            # Update Donations
            updated = Donation.objects.filter(donor=source).update(donor=target)
            counts['donations_donor'] = updated

            updated = Donation.objects.filter(recipient=source).update(recipient=target)
            counts['donations_recipient'] = updated

            # Update MeetingAttendees
            updated = MeetingAttendee.objects.filter(actor=source).update(actor=target)
            counts['meeting_attendees'] = updated

            # Update Consultancies
            updated = Consultancy.objects.filter(client=source).update(client=target)
            counts['consultancy_client'] = updated

            updated = Consultancy.objects.filter(agency=source).update(agency=target)
            counts['consultancy_agency'] = updated

            # Update Memberships (for Person actors)
            if hasattr(source, 'person') and hasattr(target, 'person'):
                updated = Membership.objects.filter(person=source.person).update(
                    person=target.person
                )
                counts['memberships'] = updated

            # Copy identifiers (if not duplicate)
            source_ct = ContentType.objects.get_for_model(source.__class__)
            target_ct = ContentType.objects.get_for_model(target.__class__)

            for ident in Identifier.objects.filter(content_type=source_ct, object_id=source.pk):
                # Check if target already has this identifier
                exists = Identifier.objects.filter(
                    content_type=target_ct,
                    object_id=target.pk,
                    scheme=ident.scheme,
                    identifier=ident.identifier
                ).exists()

                if not exists:
                    Identifier.objects.create(
                        content_type=target_ct,
                        object_id=target.pk,
                        scheme=ident.scheme,
                        identifier=ident.identifier
                    )
                    counts['identifiers'] += 1

            # Add source name as OtherName on target
            if source.name != target.name:
                OtherName.objects.get_or_create(
                    content_type=target_ct,
                    object_id=target.pk,
                    name=source.name,
                    defaults={'note': f'Merged from actor ID {source.pk}'}
                )
                counts['other_names'] = 1

            # Add merge note
            Note.objects.create(
                content_type=target_ct,
                object_id=target.pk,
                content=f'Merged with "{source.name}" (ID: {source.pk})'
            )

            # Delete Companies House matches for source
            if hasattr(source, 'organization'):
                CompaniesHouseMatch.objects.filter(organization=source.organization).delete()

            # Delete source actor
            source.delete()

        logger.info(f"Merged actor '{source.name}' into '{target.name}': {counts}")
        return counts

    def find_duplicates(self, actor: 'models.Actor',
                        min_confidence: float = 0.70) -> List[ResolutionResult]:
        """
        Find potential duplicate actors.

        Args:
            actor: Actor to find duplicates for
            min_confidence: Minimum confidence threshold

        Returns:
            List of potential duplicates with confidence scores
        """
        from datafetch.models import Actor

        results = []
        actor_name = actor.name
        normalized_strong = normalize_actor_name(actor_name, strength='strong')
        normalized_weak = normalize_actor_name(actor_name, strength='weak')

        # Find actors with similar names
        candidates = Actor.objects.exclude(pk=actor.pk).filter(
            Q(name__iexact=actor_name) |
            Q(name__icontains=normalized_strong[:20])  # Prefix match
        )[:100]  # Limit for performance

        for candidate in candidates:
            candidate_normalized_strong = normalize_actor_name(
                candidate.name, strength='strong'
            )
            candidate_normalized_weak = normalize_actor_name(
                candidate.name, strength='weak'
            )

            # Determine confidence
            if candidate.name == actor_name:
                confidence = self.CONFIDENCE_EXACT
                reason = 'exact_match'
            elif candidate_normalized_strong == normalized_strong:
                confidence = self.CONFIDENCE_STRONG
                reason = 'strong_normalization'
            elif candidate_normalized_weak == normalized_weak:
                confidence = self.CONFIDENCE_WEAK
                reason = 'weak_normalization'
            else:
                continue  # Skip if no match

            if confidence >= min_confidence:
                results.append(ResolutionResult(
                    canonical=candidate,
                    confidence=confidence,
                    match_reason=reason,
                    details=f'{actor_name} ~ {candidate.name}'
                ))

        # Sort by confidence descending
        results.sort(key=lambda r: -r.confidence)
        return results

    def _resolve_by_ec_id(self, actor: 'models.Actor') -> ResolutionResult:
        """
        Resolve by Electoral Commission donor ID.

        Uses prefetched _ec_actor_index for O(1) lookup when available.

        Args:
            actor: Actor to resolve

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor, Identifier

        # Get actor's EC identifiers
        actor_ct = ContentType.objects.get_for_model(actor.__class__)
        ec_idents = Identifier.objects.filter(
            content_type=actor_ct,
            object_id=actor.pk,
            scheme='electoralcommission'
        ).values_list('identifier', flat=True)

        for ec_ref in ec_idents:
            # Use index if available (O(1) lookup)
            if self._ec_actor_index:
                other_actor_ids = [
                    aid for aid in self._ec_actor_index.get(ec_ref, [])
                    if aid != actor.pk
                ]
                if other_actor_ids:
                    # Return the canonical (lowest ID)
                    canonical_id = min(other_actor_ids)
                    if canonical_id < actor.pk:
                        canonical = self._get_actor_by_id(canonical_id)
                        if canonical:
                            return ResolutionResult(
                                canonical=canonical,
                                confidence=self.CONFIDENCE_EC_DONOR,
                                match_reason='ec_donor_id_match',
                                details=f'EC: {ec_ref}'
                            )
            else:
                # Fall back to database query
                other_idents = Identifier.objects.filter(
                    scheme='electoralcommission',
                    identifier=ec_ref
                ).exclude(
                    content_type=actor_ct,
                    object_id=actor.pk
                ).values_list('object_id', flat=True)

                for other_id in other_idents:
                    if other_id < actor.pk:
                        canonical = self._get_actor_by_id(other_id)
                        if canonical:
                            return ResolutionResult(
                                canonical=canonical,
                                confidence=self.CONFIDENCE_EC_DONOR,
                                match_reason='ec_donor_id_match',
                                details=f'EC: {ec_ref}'
                            )

        return ResolutionResult(None, 0.0, 'no_ec_id', 'No EC ID match')

    def _resolve_by_othername(self, actor: 'models.Actor', alias_type: str = 'strong') -> ResolutionResult:
        """
        Resolve by OtherName (alias) matching.

        Looks up the actor's name in the OtherName index to find actors
        that have this name as an alias.

        Args:
            actor: Actor to resolve
            alias_type: 'strong' for abbreviations/trade names (0.90),
                       'weak' for former names/nicknames (0.75)

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor

        confidence = (
            self.CONFIDENCE_OTHERNAME_STRONG if alias_type == 'strong'
            else self.CONFIDENCE_OTHERNAME_WEAK
        )

        actor_name_lower = actor.name.lower()

        # Use index if available
        if self._othername_index:
            matches = self._othername_index.get(actor_name_lower, [])
            # Filter by alias type and exclude self
            candidate_ids = [
                aid for aid, atype in matches
                if atype == alias_type and aid != actor.pk
            ]

            if candidate_ids:
                # Return canonical (lowest ID)
                canonical_id = min(candidate_ids)
                if canonical_id < actor.pk:
                    canonical = self._get_actor_by_id(canonical_id)
                    if canonical:
                        return ResolutionResult(
                            canonical=canonical,
                            confidence=confidence,
                            match_reason=f'othername_{alias_type}_match',
                            details=f'Alias: "{actor.name}" -> actor #{canonical_id}'
                        )
        else:
            # Fall back to database query (slow)
            from datafetch.models import OtherName, Person, Organization
            person_ct = ContentType.objects.get_for_model(Person)
            org_ct = ContentType.objects.get_for_model(Organization)

            matches = OtherName.objects.filter(
                name__iexact=actor.name,
                content_type__in=[person_ct, org_ct]
            ).exclude(object_id=actor.pk).values_list('object_id', 'note')

            for obj_id, note in matches:
                note_lower = (note or '').lower()
                if alias_type == 'strong':
                    is_match = any(kw in note_lower for kw in ['abbreviation', 'trade', 'trading', 'aka'])
                else:
                    is_match = not any(kw in note_lower for kw in ['abbreviation', 'trade', 'trading', 'aka'])

                if is_match and obj_id < actor.pk:
                    canonical = self._get_actor_by_id(obj_id)
                    if canonical:
                        return ResolutionResult(
                            canonical=canonical,
                            confidence=confidence,
                            match_reason=f'othername_{alias_type}_match',
                            details=f'Alias: "{actor.name}" -> actor #{obj_id}'
                        )

        return ResolutionResult(None, 0.0, f'no_othername_{alias_type}', f'No OtherName {alias_type} match')

    def _resolve_by_identifier(self, actor: 'models.Actor') -> ResolutionResult:
        """
        Resolve by external identifier (Companies House, Electoral Commission, etc.).

        Uses prefetched _ch_index for O(1) Company House lookups when available.

        Args:
            actor: Actor to resolve

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor, Identifier, CompaniesHouseMatch

        # Check Companies House matches (use index if available)
        if hasattr(actor, 'organization'):
            ch_matches = CompaniesHouseMatch.objects.filter(
                organization=actor.organization,
                status__in=['approved', 'auto_approved']
            ).values_list('company_number', flat=True)

            for company_number in ch_matches:
                # Use index for O(1) lookup
                if self._ch_index:
                    canonical_org_id = self._ch_index.get(company_number)
                    if canonical_org_id and canonical_org_id != actor.pk:
                        canonical = self._get_actor_by_id(canonical_org_id)
                        if canonical:
                            return ResolutionResult(
                                canonical=canonical,
                                confidence=self.CONFIDENCE_IDENTIFIER,
                                match_reason='companies_house_match',
                                details=f'CH: {company_number}'
                            )
                else:
                    # Fall back to database query
                    other_matches = CompaniesHouseMatch.objects.filter(
                        company_number=company_number,
                        status__in=['approved', 'auto_approved']
                    ).exclude(
                        organization=actor.organization
                    ).select_related('organization')

                    for match in other_matches:
                        return ResolutionResult(
                            canonical=match.organization.actor_ptr,
                            confidence=self.CONFIDENCE_IDENTIFIER,
                            match_reason='companies_house_match',
                            details=f'CH: {company_number}'
                        )

        # Check Identifiers
        actor_ct = ContentType.objects.get_for_model(actor.__class__)
        identifiers = Identifier.objects.filter(
            content_type=actor_ct,
            object_id=actor.pk
        )

        for ident in identifiers:
            # Find other actors with same identifier
            other_idents = Identifier.objects.filter(
                scheme=ident.scheme,
                identifier=ident.identifier
            ).exclude(
                content_type=actor_ct,
                object_id=actor.pk
            )

            for other in other_idents:
                other_actor = other.content_object
                if other_actor and other_actor.pk != actor.pk:
                    return ResolutionResult(
                        canonical=other_actor,
                        confidence=self.CONFIDENCE_IDENTIFIER,
                        match_reason='identifier_match',
                        details=f'{ident.scheme}: {ident.identifier}'
                    )

        return ResolutionResult(None, 0.0, 'no_identifier', 'No identifier match')

    def _resolve_by_exact_name(self, actor: 'models.Actor') -> ResolutionResult:
        """
        Resolve by exact name match (case-insensitive).

        Prefers actors with more relationships (richer data), unless skip_scoring is set.

        Args:
            actor: Actor to resolve

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor

        # Use index if available
        if self._name_index:
            candidates = [
                c for c in self._name_index.get(actor.name.lower(), [])
                if c.pk != actor.pk
            ]
            if not candidates:
                return ResolutionResult(None, 0.0, 'no_exact_match', 'No exact name match')
        else:
            # Find actors with same name
            candidates = Actor.objects.filter(
                name__iexact=actor.name
            ).exclude(pk=actor.pk)

            if not candidates.exists():
                return ResolutionResult(None, 0.0, 'no_exact_match', 'No exact name match')

        # Fast path: skip scoring, just take first match with lower ID (older = canonical)
        if self.skip_scoring:
            if isinstance(candidates, list):
                # Sort in-memory list by PK
                sorted_candidates = sorted(candidates, key=lambda x: x.pk)
                best_candidate = sorted_candidates[0] if sorted_candidates else None
            else:
                # Use QuerySet method
                best_candidate = candidates.order_by('pk').first()
                
            if best_candidate and best_candidate.pk < actor.pk:
                return ResolutionResult(
                    canonical=best_candidate,
                    confidence=self.CONFIDENCE_EXACT,
                    match_reason='exact_name_match',
                    details=f'First match (ID: {best_candidate.pk})'
                )
            return ResolutionResult(None, 0.0, 'no_older_match', 'No older exact match')

        # Full scoring path: find the best candidate (highest entity score)
        best_candidate = None
        best_score = -1
        
        from datafetch.models import Organization
        org_keywords = ['party', 'union', 'ltd', 'limited', 'plc', 'llp', 'council', 'group', 'association', 'federation']
        name_lower = actor.name.lower()
        should_be_org = any(kw in name_lower for kw in org_keywords)

        for candidate in candidates:
            score = self.calculate_entity_score(candidate)
            
            # Polymorphic Safety: If name suggests an Organization, prioritize
            # candidates that are actually typed as Organization.
            candidate_is_org = hasattr(candidate, 'organization') or isinstance(candidate, Organization)
            if should_be_org and candidate_is_org:
                score += 1000000  # Massive priority for correctly typed orgs

            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate:
            # Only return if the candidate has more data than the source,
            # OR if scores are equal and candidate has lower ID (older = canonical)
            source_score = self.calculate_entity_score(actor)
            
            # Adjust source score if it's misclassified
            actor_is_org = hasattr(actor, 'organization') or isinstance(actor, Organization)
            if should_be_org and not actor_is_org:
                source_score -= 1000000  # Penalize misclassified source

            if best_score > source_score or (best_score == source_score and best_candidate.pk < actor.pk):
                return ResolutionResult(
                    canonical=best_candidate,
                    confidence=self.CONFIDENCE_EXACT,
                    match_reason='exact_name_match',
                    details=f'Score: {best_score} vs {source_score}'
                )

        return ResolutionResult(None, 0.0, 'no_better_match', 'No higher-scored match')

    def _resolve_by_normalized_name(self, actor: 'models.Actor',
                                    strength: str = 'strong') -> ResolutionResult:
        """
        Resolve by normalized name match.

        Uses prefix filtering to reduce search space before fuzzy matching.

        Args:
            actor: Actor to resolve
            strength: 'strong' or 'weak' normalization

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor

        normalized = normalize_actor_name(actor.name, strength=strength)

        if not normalized or len(normalized) < 3:
            return ResolutionResult(None, 0.0, 'empty_normalized', 'Normalized name too short')

        candidates = []
        
        # Optimization: Use pre-built normalized indexes if available (O(1) lookup)
        if strength == 'strong' and hasattr(self, '_normalized_strong_index') and self._normalized_strong_index:
            candidates = [c for c in self._normalized_strong_index.get(normalized, []) if c.pk != actor.pk]
        elif strength == 'weak' and hasattr(self, '_normalized_weak_index') and self._normalized_weak_index:
            candidates = [c for c in self._normalized_weak_index.get(normalized, []) if c.pk != actor.pk]
        else:
            # Fallback to slower search if indexes not available
            
            # Smart filtering: use first word or prefix to narrow search
            # This reduces 155k actors to typically <1000
            first_word = normalized.split()[0] if ' ' in normalized else normalized[:8]

            if self._name_index:
                # Search the index keys (still faster than DB istartswith in many cases)
                # but even better, if we have a direct match on keys we should use it.
                # For now, let's just use the index to get candidates by prefix
                prefix = first_word[:4].lower()
                candidates_raw = []
                for name_key, actor_list in self._name_index.items():
                    if name_key.startswith(prefix):
                        for a in actor_list:
                            if a.pk != actor.pk:
                                candidates_raw.append(a)
                    if len(candidates_raw) >= 500:
                        break
                
                # Filter candidates manually since we didn't use the exact lookup index
                for candidate in candidates_raw:
                     candidate_normalized = normalize_actor_name(candidate.name, strength=strength)
                     if candidate_normalized == normalized:
                         candidates.append(candidate)
                         
            else:
                # Find candidates with similar starting characters (case-insensitive)
                # Note: This is the slowest path (DB query per record)
                candidates_qs = Actor.objects.exclude(pk=actor.pk).filter(
                    name__istartswith=first_word[:4]  # First 4 chars of first word
                )[:500]  # Limit to 500 candidates max
                
                # If no prefix matches, try contains on first word
                if not candidates_qs.exists() and len(first_word) >= 4:
                    candidates_qs = Actor.objects.exclude(pk=actor.pk).filter(
                        name__icontains=first_word
                    )[:500]

                # Filter DB candidates
                for candidate in candidates_qs:
                    candidate_normalized = normalize_actor_name(candidate.name, strength=strength)
                    if candidate_normalized == normalized:
                        candidates.append(candidate)

        # Common logic: Select best candidate from matches
        best_candidate = None
        best_score = -1
        
        from datafetch.models import Organization
        org_keywords = ['party', 'union', 'ltd', 'limited', 'plc', 'llp', 'council', 'group', 'association', 'federation']
        name_lower = actor.name.lower()
        should_be_org = any(kw in name_lower for kw in org_keywords)

        for candidate in candidates:
            # Candidates are already verified to match normalized name
            
            # Fast path: take first match with lower ID
            if self.skip_scoring:
                # Still prioritize org if needed
                candidate_is_org = hasattr(candidate, 'organization') or isinstance(candidate, Organization)
                actor_is_org = hasattr(actor, 'organization') or isinstance(actor, Organization)
                
                # If we're an org and they aren't, they can't be our canonical
                if should_be_org and actor_is_org and not candidate_is_org:
                    continue
                
                if candidate.pk < actor.pk:
                    confidence = (
                        self.CONFIDENCE_STRONG if strength == 'strong'
                        else self.CONFIDENCE_WEAK
                    )
                    return ResolutionResult(
                        canonical=candidate,
                        confidence=confidence,
                        match_reason=f'{strength}_normalization_match',
                        details=f'Normalized: "{normalized}"'
                    )
            else:
                score = self.calculate_entity_score(candidate)
                
                # Polymorphic Safety
                candidate_is_org = hasattr(candidate, 'organization') or isinstance(candidate, Organization)
                if should_be_org and candidate_is_org:
                    score += 1000000

                if score > best_score:
                    best_score = score
                    best_candidate = candidate

        if best_candidate and not self.skip_scoring:
            source_score = self.calculate_entity_score(actor)
            
            # Adjust source score if it's misclassified
            actor_is_org = hasattr(actor, 'organization') or isinstance(actor, Organization)
            if should_be_org and not actor_is_org:
                source_score -= 1000000

            if best_score > source_score:
                confidence = (
                    self.CONFIDENCE_STRONG if strength == 'strong'
                    else self.CONFIDENCE_WEAK
                )
                return ResolutionResult(
                    canonical=best_candidate,
                    confidence=confidence,
                    match_reason=f'{strength}_normalization_match',
                    details=f'Normalized: "{normalized}"'
                )

        return ResolutionResult(
            None, 0.0, f'no_{strength}_match',
            f'No {strength} normalization match'
        )

    def get_stats(self) -> Dict[str, int]:
        """Get resolution statistics."""
        return self.stats.copy()

    def clear_cache(self):
        """Clear the resolution cache."""
        self._cache.clear()
        self._score_cache.clear()

    def log_stats(self):
        """Log resolution statistics."""
        logger.info("=== Entity Resolution Statistics ===")
        logger.info(f"  Identifier matches: {self.stats['identifier_matches']}")
        logger.info(f"  EC ID matches: {self.stats.get('ec_id_matches', 0)}")
        logger.info(f"  Exact matches: {self.stats['exact_matches']}")
        logger.info(f"  OtherName strong: {self.stats.get('othername_strong_matches', 0)}")
        logger.info(f"  Strong matches: {self.stats['strong_matches']}")
        logger.info(f"  OtherName weak: {self.stats.get('othername_weak_matches', 0)}")
        logger.info(f"  Weak matches: {self.stats['weak_matches']}")
        logger.info(f"  No match: {self.stats['no_match']}")
        logger.info(f"  Cache hits: {self.stats['cache_hits']}")

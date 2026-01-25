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
    CONFIDENCE_EXACT = 0.95      # Exact name match
    CONFIDENCE_STRONG = 0.85     # Strong normalization
    CONFIDENCE_WEAK = 0.70       # Weak normalization

    # Minimum confidence to auto-link
    MIN_CONFIDENCE_AUTO = 0.85

    def __init__(self):
        """Initialize the service."""
        self._cache: Dict[str, 'models.Actor'] = {}
        self.stats = {
            'identifier_matches': 0,
            'exact_matches': 0,
            'strong_matches': 0,
            'weak_matches': 0,
            'no_match': 0,
            'cache_hits': 0,
        }

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

        # Pass 1: Identifier-based resolution
        result = self._resolve_by_identifier(actor)
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['identifier_matches'] += 1
            return result

        # Pass 2: Exact name match
        result = self._resolve_by_exact_name(actor)
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['exact_matches'] += 1
            return result

        # Pass 3: Strong normalization match
        result = self._resolve_by_normalized_name(actor, strength='strong')
        if result.is_resolved:
            self._cache[cache_key] = result.canonical
            self.stats['strong_matches'] += 1
            return result

        # Pass 4: Weak normalization match
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

        Args:
            actor: Actor to score

        Returns:
            Integer score (higher = richer data)
        """
        from datafetch.models import (
            Identifier, Donation, MeetingAttendee, Consultancy, Membership
        )

        score = 0

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

    def _resolve_by_identifier(self, actor: 'models.Actor') -> ResolutionResult:
        """
        Resolve by external identifier (Companies House, Electoral Commission, etc.).

        Args:
            actor: Actor to resolve

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor, Identifier, CompaniesHouseMatch

        # Check Companies House matches
        if hasattr(actor, 'organization'):
            ch_matches = CompaniesHouseMatch.objects.filter(
                organization=actor.organization,
                status__in=['approved', 'auto_approved']
            ).values_list('company_number', flat=True)

            for company_number in ch_matches:
                # Find other orgs with same CH number
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

        Prefers actors with more relationships (richer data).

        Args:
            actor: Actor to resolve

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor

        # Find actors with same name
        candidates = Actor.objects.filter(
            name__iexact=actor.name
        ).exclude(pk=actor.pk)

        if not candidates.exists():
            return ResolutionResult(None, 0.0, 'no_exact_match', 'No exact name match')

        # Find the best candidate (highest entity score)
        best_candidate = None
        best_score = -1

        for candidate in candidates:
            score = self.calculate_entity_score(candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate:
            # Only return if the candidate has more data than the source
            source_score = self.calculate_entity_score(actor)
            if best_score > source_score:
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

        Args:
            actor: Actor to resolve
            strength: 'strong' or 'weak' normalization

        Returns:
            ResolutionResult with canonical if found
        """
        from datafetch.models import Actor

        normalized = normalize_actor_name(actor.name, strength=strength)

        if not normalized:
            return ResolutionResult(None, 0.0, 'empty_normalized', 'Normalized name is empty')

        # Find candidates by scanning (expensive but thorough)
        # In production, this should use a precomputed search index
        best_candidate = None
        best_score = -1

        # Limit search scope for performance
        candidates = Actor.objects.exclude(pk=actor.pk)[:10000]

        for candidate in candidates:
            candidate_normalized = normalize_actor_name(candidate.name, strength=strength)
            if candidate_normalized == normalized:
                score = self.calculate_entity_score(candidate)
                if score > best_score:
                    best_score = score
                    best_candidate = candidate

        if best_candidate:
            source_score = self.calculate_entity_score(actor)
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

    def log_stats(self):
        """Log resolution statistics."""
        logger.info("=== Entity Resolution Statistics ===")
        logger.info(f"  Identifier matches: {self.stats['identifier_matches']}")
        logger.info(f"  Exact matches: {self.stats['exact_matches']}")
        logger.info(f"  Strong matches: {self.stats['strong_matches']}")
        logger.info(f"  Weak matches: {self.stats['weak_matches']}")
        logger.info(f"  No match: {self.stats['no_match']}")
        logger.info(f"  Cache hits: {self.stats['cache_hits']}")

"""
Entity Matcher for Ministerial Meetings Import

Handles entity resolution (matching actors by name) for the ministerial meetings
import process. Follows the same pattern as import_ec.py and import_mpsinterests.py.

Strategy:
1. Check in-memory cache (for performance during single import run)
2. Try exact name match (case-insensitive)
3. Try OtherName match (aliases)
4. Try normalized name match (strong, then weak)
5. Create new actor if create_if_missing=True

Phase 1: Basic matching with create-if-missing
Phase 3: Enhanced with canonical actor resolution
Phase 3.2: Uses ActorClassifier from shared data_cleanup module
"""

from typing import Optional
import logging

from datafetch import models
from datafetch.utils.normalization import normalize_actor_name
from datafetch.utils.data_cleanup import ActorClassifier
from datafetch.helpers import parse_name

logger = logging.getLogger(__name__)


class EntityMatcher:
    """
    Entity resolution for ministerial meetings import.

    Provides in-memory caching and multi-strategy matching for both
    ministers (Person) and external actors (Person or Organization).
    """

    def __init__(self):
        """Initialize with empty caches."""
        self.minister_cache = {}  # name -> Person
        self.actor_cache = {}     # name -> Actor
        self.stats = {
            'minister_cache_hits': 0,
            'minister_exact_matches': 0,
            'minister_other_name_matches': 0,
            'minister_normalized_matches': 0,
            'minister_not_found': 0,
            'actor_cache_hits': 0,
            'actor_exact_matches': 0,
            'actor_other_name_matches': 0,
            'actor_normalized_matches': 0,
            'actor_created': 0,
        }

    def match_minister(self, minister_name: str) -> Optional[models.Person]:
        """
        Match minister by name.

        Strategy (follows import_mpsinterests pattern):
        1. Check cache
        2. Try exact name match (case-insensitive)
        3. Try OtherName match
        4. Try normalized name (strong)
        5. Return None if no match

        Ministers should already exist from import_parlparse, so we don't
        create new records here. If a minister isn't found, it likely means:
        - Name variant not in database (add OtherName)
        - Minister not yet imported (run import_parlparse)
        - Name spelling error in source data

        Args:
            minister_name: Minister name as it appears in GOV.UK data

        Returns:
            Person object if found, None otherwise
        """
        if not minister_name:
            return None

        # Check cache
        if minister_name in self.minister_cache:
            self.stats['minister_cache_hits'] += 1
            return self.minister_cache[minister_name]

        # Normalize for searching
        normalized = normalize_actor_name(minister_name, strength='strong')

        # Strategy 1: Try exact match (case-insensitive)
        minister = models.Person.objects.filter(name__iexact=normalized).first()
        if minister:
            self.minister_cache[minister_name] = minister
            self.stats['minister_exact_matches'] += 1
            logger.debug(f"Minister exact match: '{minister_name}' -> {minister.name}")
            return minister

        # Strategy 2: Try OtherName match
        other_name = models.OtherName.objects.filter(
            name__iexact=normalized,
            content_type__model='person'
        ).select_related('content_type').first()

        if other_name:
            minister = other_name.content_object
            if isinstance(minister, models.Person):
                self.minister_cache[minister_name] = minister
                self.stats['minister_other_name_matches'] += 1
                logger.debug(f"Minister OtherName match: '{minister_name}' -> {minister.name}")
                return minister

        # Strategy 3: Try normalized name (strong normalization only - be conservative)
        # This catches "John Smith" vs "John Smith MP" etc.
        normalized_weak = normalize_actor_name(minister_name, strength='weak')
        for person in models.Person.objects.all():
            person_normalized = normalize_actor_name(person.name, strength='weak')
            if person_normalized == normalized_weak:
                self.minister_cache[minister_name] = person
                self.stats['minister_normalized_matches'] += 1
                logger.debug(f"Minister normalized match: '{minister_name}' -> {person.name}")
                return person

        # No match found
        self.stats['minister_not_found'] += 1
        logger.warning(f"Minister not found: '{minister_name}'")
        return None

    def match_external_actor(self, actor_name: str,
                            create_if_missing: bool = True) -> Optional[models.Actor]:
        """
        Match external actor (Person or Organization).

        Phase 1 Strategy (Fast Import - Entity Resolution Deferred to Phase 3):
        1. Check cache (in-memory for this import run)
        2. Try exact name match (indexed query - fast)
        3. Create new actor if not found

        Note: We intentionally skip expensive fuzzy matching and OtherName searches
        during import. Entity resolution (finding duplicates and setting
        canonical_external_actor) will be done in Phase 3 via the
        resolve_meeting_duplicates management command.

        This approach:
        - Makes imports fast (O(n) instead of O(n²))
        - Preserves original data (external_actor never modified)
        - Enables post-import entity resolution refinement

        Args:
            actor_name: External actor name as it appears in GOV.UK data
            create_if_missing: If True, create new Actor if no match found

        Returns:
            Actor object (Person or Organization) if found/created, None otherwise
        """
        if not actor_name:
            return None

        # Check cache (avoid repeated queries for same name in one import)
        if actor_name in self.actor_cache:
            self.stats['actor_cache_hits'] += 1
            return self.actor_cache[actor_name]

        # Normalize for searching
        normalized = normalize_actor_name(actor_name, strength='strong')

        # Try exact match (case-insensitive) - this is indexed and fast
        actor = models.Actor.objects.filter(name__iexact=normalized).first()
        if actor:
            self.actor_cache[actor_name] = actor
            self.stats['actor_exact_matches'] += 1
            logger.debug(f"Actor exact match: '{actor_name}' -> {actor.name}")
            return actor

        # No exact match found - create new actor if requested
        # Entity resolution will happen later in Phase 3
        if create_if_missing:
            # Check if name is too long for Actor.name field (max 1024)
            # This happens with large roundtable meetings with 20+ attendees
            # In this case, return None - the meeting will be marked as roundtable
            # and individual attendees will be tracked via MeetingAttendee
            if len(normalized) > 1024:
                logger.warning(
                    f"Actor name too long ({len(normalized)} chars), skipping creation. "
                    f"This is likely a roundtable with many attendees."
                )
                return None

            actor = self._create_external_actor(actor_name, normalized)
            self.actor_cache[actor_name] = actor
            self.stats['actor_created'] += 1
            return actor

        return None

    def _create_external_actor(self, original_name: str,
                              normalized_name: str) -> models.Actor:
        """
        Create new Person or Organization based on name heuristics.

        Uses simple heuristics to determine if a name represents an
        organization or a person:
        - Contains org keywords (Ltd, Group, etc.) -> Organization
        - All caps acronym -> Organization
        - Starts with "The " -> Organization
        - Otherwise -> Person

        Args:
            original_name: Original name from source data
            normalized_name: Normalized version of name

        Returns:
            Newly created Actor (Person or Organization)
        """
        if self._is_organization(original_name):
            # Create Organization
            actor = models.Organization.objects.create(
                name=normalized_name,
                classification='External Organization'
            )
            logger.info(f"Created Organization: {normalized_name}")
        else:
            # Create Person
            actor = models.Person.objects.create(name=normalized_name)

            # Try to parse name into given_name, family_name
            try:
                _, person_dict = parse_name(original_name)
                for key, value in person_dict.items():
                    if hasattr(actor, key) and value:
                        setattr(actor, key, value)
                actor.save()
                logger.info(f"Created Person: {normalized_name}")
            except Exception as e:
                logger.warning(f"Could not parse person name '{original_name}': {e}")

        # Add original name as OtherName if different from normalized
        # Skip if original name is too long for the field (max 1024)
        if original_name != normalized_name and len(original_name) <= 1024:
            models.OtherName.objects.create(
                content_object=actor,
                name=original_name,
                note="Original name from ministerial meetings data"
            )

        return actor

    def _is_organization(self, name: str) -> bool:
        """
        Heuristic: is this name an organization vs person?

        Phase 3.2: Uses ActorClassifier from shared data_cleanup module
        for consistent classification across the application.

        Args:
            name: Actor name to classify

        Returns:
            True if likely an organization, False if likely a person
        """
        # Check for person titles first (MP, Lord, Sir, etc.)
        # If it's clearly a person, return False
        if ActorClassifier.has_person_title(name):
            return False

        # Use shared ActorClassifier for consistent classification
        actor_type = ActorClassifier.classify(name)

        # If classified as organization, return True
        if actor_type == 'organization':
            return True

        # If classified as person, return False
        if actor_type == 'person':
            return False

        # For 'unknown', use original heuristics as fallback
        name_lower = name.lower()

        # All caps acronym (e.g., "BBC", "ACME", "GCHQ")
        if name.isupper() and len(name) >= 2 and ' ' not in name.strip():
            return True

        # Starts with "The " (e.g., "The Guardian", "The Cabinet Office")
        if name.startswith('The '):
            return True

        # Contains "&" between words (but be careful with law firms)
        # Only count as org if there are other org indicators
        if ' & ' in name and len(name.split()) >= 3:
            return True

        # Otherwise assume person (safer default for meetings data)
        return False

    def get_stats(self) -> dict:
        """
        Get matching statistics for this import run.

        Returns:
            Dictionary of statistics
        """
        return self.stats.copy()

    def log_stats(self):
        """Log matching statistics."""
        logger.info("=== Entity Matching Statistics ===")
        logger.info(f"Ministers:")
        logger.info(f"  Cache hits: {self.stats['minister_cache_hits']}")
        logger.info(f"  Exact matches: {self.stats['minister_exact_matches']}")
        logger.info(f"  OtherName matches: {self.stats['minister_other_name_matches']}")
        logger.info(f"  Normalized matches: {self.stats['minister_normalized_matches']}")
        logger.info(f"  Not found: {self.stats['minister_not_found']}")
        logger.info(f"External Actors:")
        logger.info(f"  Cache hits: {self.stats['actor_cache_hits']}")
        logger.info(f"  Exact matches: {self.stats['actor_exact_matches']}")
        logger.info(f"  OtherName matches: {self.stats['actor_other_name_matches']}")
        logger.info(f"  Normalized matches: {self.stats['actor_normalized_matches']}")
        logger.info(f"  Created new: {self.stats['actor_created']}")

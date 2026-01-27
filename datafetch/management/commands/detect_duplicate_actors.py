"""
Detect Duplicate Actors in Ministerial Meetings Data

Uses multi-strategy detection to identify potential duplicate external actors:
- Exact match (case-insensitive)
- Known aliases (manual mappings)
- Substring match (with smart filtering)
- Fuzzy string matching

Creates ActorResolution records for manual review and automatic merging.

Phase 3: Entity Resolution
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from datafetch import models
from datafetch.utils.normalization import normalize_actor_name, calculate_name_similarity
import logging

logger = logging.getLogger(__name__)


# Known aliases for common organizations (manually curated)
KNOWN_ALIASES = {
    'Google': {
        'canonical': 'Google LLC',
        'aliases': ['Google', 'Google Inc', 'Alphabet Inc'],
        'confidence': 0.95
    },
    'Meta': {
        'canonical': 'Meta Platforms Inc',
        'aliases': ['Meta', 'META', 'Facebook', 'Facebook Inc', 'Meta Platforms', 'Meta/Home Sec'],
        'confidence': 0.95
    },
    'X': {
        'canonical': 'X Corp',
        'aliases': ['Twitter', 'X', 'X (formerly Twitter)', 'Twitter Inc'],
        'confidence': 0.95
    },
    'Google DeepMind': {
        'canonical': 'Google DeepMind',
        'aliases': ['Deepmind', 'DeepMind', 'Google Deepmind', 'Google DeepMind'],
        'confidence': 0.95,
        'parent': 'Google'
    },
    'techUK': {
        'canonical': 'techUK',
        'aliases': ['techUK', 'TechUK', 'Tech UK', 'Tech Uk Conference'],
        'confidence': 1.0
    },
    'AstraZeneca': {
        'canonical': 'AstraZeneca',
        'aliases': ['AstraZeneca', 'Astrazeneca', 'AstraZeneca plc'],
        'confidence': 1.0
    },
    'GSK': {
        'canonical': 'GSK plc',
        'aliases': ['GSK', 'GlaxoSmithKline', 'GSK plc'],
        'confidence': 1.0
    },
}


class Command(BaseCommand):
    help = 'Detect duplicate external actors and create resolution suggestions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.70,
            help='Minimum similarity threshold (0.0-1.0)'
        )
        parser.add_argument(
            '--auto-approve',
            type=float,
            help='Auto-approve resolutions with confidence >= this value'
        )
        parser.add_argument(
            '--source',
            default='ministerial_meetings',
            help='Data source to analyze (default: ministerial_meetings)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving'
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        auto_approve_threshold = options.get('auto_approve')
        dry_run = options.get('dry_run', False)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Duplicate Actor Detection")
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(f"Similarity threshold: {threshold}")
        if auto_approve_threshold:
            self.stdout.write(f"Auto-approve threshold: {auto_approve_threshold}")
        self.stdout.write("")

        # Get all unique external actors from ministerial meetings
        actors = self._get_external_actors()

        self.stdout.write(f"Analyzing {actors.count()} unique external actors...\n")

        # Detection strategies
        strategies = [
            ('exact', self._detect_exact_matches),
            ('known_alias', self._detect_known_aliases),
            ('substring', self._detect_substring_matches),
            ('fuzzy', self._detect_fuzzy_matches),
        ]

        total_found = 0
        total_created = 0
        total_auto_approved = 0

        for strategy_name, strategy_func in strategies:
            self.stdout.write(f"Running {strategy_name} detection...")

            matches = strategy_func(actors, threshold)

            self.stdout.write(f"  Found {len(matches)} potential duplicates")

            for match in matches:
                # Check if resolution already exists
                existing = models.ActorResolution.objects.filter(
                    Q(actor1=match['actor1'], actor2=match['actor2']) |
                    Q(actor1=match['actor2'], actor2=match['actor1'])
                ).first()

                if existing:
                    continue  # Skip if already exists

                total_found += 1

                # Determine decision based on confidence
                if auto_approve_threshold and match['confidence'] >= auto_approve_threshold:
                    decision = 'auto_merge'
                    review_status = 'approved'
                    total_auto_approved += 1
                elif match['confidence'] >= 0.90:
                    decision = 'review'
                    review_status = 'pending'
                else:
                    decision = 'suggest'
                    review_status = 'pending'

                # Display match
                self.stdout.write(
                    f"    {match['actor1'].name} ↔ {match['actor2'].name} "
                    f"({match['confidence']:.2f}, {strategy_name})"
                )

                if not dry_run:
                    # Create ActorResolution
                    resolution = models.ActorResolution.objects.create(
                        actor1=match['actor1'],
                        actor2=match['actor2'],
                        canonical_actor=match['canonical'],
                        confidence=match['confidence'],
                        match_reason=strategy_name,
                        decision=decision,
                        review_status=review_status,
                    )
                    total_created += 1

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Detection Summary")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✓ Potential duplicates found: {total_found}"))

        if not dry_run:
            self.stdout.write(f"  ActorResolution records created: {total_created}")
            if total_auto_approved > 0:
                self.stdout.write(f"  Auto-approved: {total_auto_approved}")
            self.stdout.write(f"  Pending review: {total_created - total_auto_approved}")
            self.stdout.write("")
            self.stdout.write("Next steps:")
            self.stdout.write("1. Review resolutions in Django admin: /django-admin/datafetch/actorresolution/")
            self.stdout.write("2. Apply approved resolutions: python manage.py apply_entity_resolutions")
        else:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made to database"))

        self.stdout.write("")

    def _get_external_actors(self):
        """Get all unique external actors from ministerial meetings."""
        # Get actors who have meeting attendances
        actor_ids = models.MeetingAttendee.objects.values_list('actor', flat=True).distinct()
        return models.Actor.objects.filter(id__in=actor_ids)

    def _detect_exact_matches(self, actors, threshold):
        """Detect exact matches (case-insensitive)."""
        matches = []

        # Group by normalized name
        from collections import defaultdict
        name_groups = defaultdict(list)

        for actor in actors:
            normalized = actor.name.lower().strip()
            name_groups[normalized].append(actor)

        # Find groups with multiple actors
        for normalized_name, actor_list in name_groups.items():
            if len(actor_list) > 1:
                # Use first actor as canonical
                canonical = actor_list[0]
                for actor in actor_list[1:]:
                    matches.append({
                        'actor1': canonical,
                        'actor2': actor,
                        'canonical': canonical,
                        'confidence': 1.0,
                    })

        return matches

    def _detect_known_aliases(self, actors, threshold):
        """Detect matches using known alias mappings."""
        matches = []

        # Build reverse lookup: alias -> canonical
        alias_to_canonical = {}
        for group_name, config in KNOWN_ALIASES.items():
            for alias in config['aliases']:
                alias_to_canonical[alias.lower()] = config['canonical']

        # Group actors by canonical name
        from collections import defaultdict
        canonical_groups = defaultdict(list)

        for actor in actors:
            canonical_name = alias_to_canonical.get(actor.name.lower())
            if canonical_name:
                canonical_groups[canonical_name].append(actor)

        # Create matches for each group
        for canonical_name, actor_list in canonical_groups.items():
            if len(actor_list) > 1:
                # Find or create canonical actor
                canonical = next((a for a in actor_list if a.name.lower() == canonical_name.lower()), actor_list[0])

                # Get confidence from known aliases
                confidence = 0.95  # Default
                for config in KNOWN_ALIASES.values():
                    if config['canonical'] == canonical_name:
                        confidence = config['confidence']
                        break

                for actor in actor_list:
                    if actor != canonical:
                        matches.append({
                            'actor1': canonical,
                            'actor2': actor,
                            'canonical': canonical,
                            'confidence': confidence,
                        })

        return matches

    def _detect_substring_matches(self, actors, threshold):
        """Detect substring matches with smart filtering."""
        matches = []

        # Convert to list for pairwise comparison
        actor_list = list(actors)

        for i, actor1 in enumerate(actor_list):
            for actor2 in actor_list[i+1:]:
                name1 = actor1.name.lower().strip()
                name2 = actor2.name.lower().strip()

                # Check if one is substring of the other
                if name1 in name2 or name2 in name1:
                    # Validate substring match
                    if self._is_valid_substring_match(name1, name2):
                        # Longer name is usually more specific, make it canonical
                        canonical = actor1 if len(actor1.name) > len(actor2.name) else actor2

                        matches.append({
                            'actor1': canonical,
                            'actor2': actor2 if canonical == actor1 else actor1,
                            'canonical': canonical,
                            'confidence': 0.90,
                        })

        return matches

    def _is_valid_substring_match(self, short_name, long_name):
        """
        Smart substring matching to avoid false positives like "Ford" in "Oxford".
        """
        import re

        # Ensure short is actually shorter
        if len(short_name) > len(long_name):
            short_name, long_name = long_name, short_name

        # Must be substring
        if short_name not in long_name:
            return False

        # Require word boundary match (avoid "ford" in "oxford")
        pattern = r'\b' + re.escape(short_name) + r'\b'
        if not re.search(pattern, long_name):
            return False

        # Reject if short name is too short (high false positive risk)
        if len(short_name) < 3:
            return False

        # Check length ratio
        ratio = len(short_name) / len(long_name)
        if ratio < 0.3:
            return False  # Too much difference

        # Check for common organizational suffixes that indicate same entity
        suffixes = [' ltd', ' limited', ' plc', ' inc', ' llc', ' corp', ' corporation']
        for suffix in suffixes:
            if long_name.endswith(suffix):
                if long_name.replace(suffix, '').strip() == short_name:
                    return True

        # Check for common prefixes
        prefixes = ['the ', 'google ', 'meta ']
        for prefix in prefixes:
            if long_name.startswith(prefix):
                if long_name.replace(prefix, '').strip() == short_name:
                    return True

        return True

    def _detect_fuzzy_matches(self, actors, threshold):
        """Detect fuzzy string matches using Levenshtein distance."""
        matches = []

        # Convert to list for pairwise comparison
        actor_list = list(actors)

        for i, actor1 in enumerate(actor_list):
            for actor2 in actor_list[i+1:]:
                # Calculate similarity
                similarity = calculate_name_similarity(actor1.name, actor2.name)

                if similarity >= threshold:
                    # Use alphabetically first as canonical (consistent)
                    canonical = actor1 if actor1.name < actor2.name else actor2

                    matches.append({
                        'actor1': canonical,
                        'actor2': actor2 if canonical == actor1 else actor1,
                        'canonical': canonical,
                        'confidence': similarity,
                    })

        return matches

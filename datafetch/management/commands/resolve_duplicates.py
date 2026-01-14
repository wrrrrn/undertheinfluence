"""
Entity resolution management command.

Scans Actor objects (Person and Organization) to identify potential duplicates
and creates ActorResolution records for review/merging.

Usage:
    python manage.py resolve_duplicates --dry-run
    python manage.py resolve_duplicates --threshold 0.7
    python manage.py resolve_duplicates --type person
    python manage.py resolve_duplicates --auto-approve  # Auto-approve identifier matches
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from collections import defaultdict

from datafetch.models import Actor, Person, Organization, ActorResolution, Identifier
from datafetch.utils.normalization import (
    normalize_actor_name,
    build_search_key,
    calculate_name_similarity,
    get_confidence_level,
)


class Command(BaseCommand):
    help = 'Identify and resolve duplicate actors using entity resolution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview matches without creating ActorResolution records'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.6,
            help='Minimum similarity threshold (0.0-1.0, default: 0.6)'
        )
        parser.add_argument(
            '--type',
            choices=['person', 'organization', 'both'],
            default='both',
            help='Type of actors to process (default: both)'
        )
        parser.add_argument(
            '--auto-approve',
            action='store_true',
            help='Automatically approve identifier matches (confidence 1.0)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all pending ActorResolution records before running'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.threshold = options['threshold']
        self.actor_type = options['type']
        self.auto_approve = options['auto_approve']
        self.clear = options['clear']

        self.stats = {
            'actors_scanned': 0,
            'comparisons_made': 0,
            'matches_found': 0,
            'auto_merge': 0,
            'review': 0,
            'suggest': 0,
            'ignore': 0,
            'duplicates_skipped': 0,
        }

        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No database changes will be made'))

        if self.clear and not self.dry_run:
            self._clear_pending_resolutions()

        # Process actors by type
        if self.actor_type in ['person', 'both']:
            self.stdout.write('\n📊 Processing Person actors...')
            self._process_actor_type(Person)

        if self.actor_type in ['organization', 'both']:
            self.stdout.write('\n📊 Processing Organization actors...')
            self._process_actor_type(Organization)

        self._print_summary()

    def _clear_pending_resolutions(self):
        """Clear all pending ActorResolution records."""
        count = ActorResolution.objects.filter(review_status='pending').count()
        if count > 0:
            ActorResolution.objects.filter(review_status='pending').delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} pending resolutions'))

    def _process_actor_type(self, model_class):
        """Process all actors of a given type (Person or Organization)."""
        actors = list(model_class.objects.all().prefetch_related('identifiers'))
        self.stats['actors_scanned'] += len(actors)

        self.stdout.write(f'Found {len(actors)} {model_class.__name__} actors')

        # Build index by search key for efficient matching
        search_key_index = defaultdict(list)
        identifier_index = defaultdict(list)

        for actor in actors:
            # Index by search key
            search_key = build_search_key(actor.name)
            if search_key:
                search_key_index[search_key].append(actor)

            # Index by identifiers
            for identifier in actor.identifiers.all():
                key = f"{identifier.scheme}:{identifier.identifier}"
                identifier_index[key].append(actor)

        # Find duplicates
        matches = []

        # 1. Find identifier matches (highest confidence)
        for identifier_key, actors_with_id in identifier_index.items():
            if len(actors_with_id) > 1:
                for i, actor1 in enumerate(actors_with_id):
                    for actor2 in actors_with_id[i+1:]:
                        matches.append({
                            'actor1': actor1,
                            'actor2': actor2,
                            'similarity': 1.0,
                            'has_identifier_match': True,
                            'has_strong_alias': False,
                            'match_type': 'identifier',
                        })

        # 2. Find search key matches (same words, different order)
        for search_key, actors_with_key in search_key_index.items():
            if len(actors_with_key) > 1:
                for i, actor1 in enumerate(actors_with_key):
                    for actor2 in actors_with_key[i+1:]:
                        # Skip if already matched by identifier
                        if self._already_matched(matches, actor1, actor2):
                            continue

                        similarity = calculate_name_similarity(actor1.name, actor2.name)
                        if similarity >= self.threshold:
                            matches.append({
                                'actor1': actor1,
                                'actor2': actor2,
                                'similarity': similarity,
                                'has_identifier_match': False,
                                'has_strong_alias': similarity >= 0.85,
                                'match_type': 'search_key',
                            })

        # 3. Find fuzzy matches (expensive - pairwise comparison)
        # Only do this for small datasets (< 1000 actors) to avoid O(n²) explosion
        if len(actors) < 1000:
            for i, actor1 in enumerate(actors):
                for actor2 in actors[i+1:]:
                    # Skip if already matched
                    if self._already_matched(matches, actor1, actor2):
                        continue

                    # Calculate similarity
                    similarity = calculate_name_similarity(actor1.name, actor2.name)
                    if similarity >= self.threshold:
                        matches.append({
                            'actor1': actor1,
                            'actor2': actor2,
                            'similarity': similarity,
                            'has_identifier_match': False,
                            'has_strong_alias': similarity >= 0.85,
                            'match_type': 'fuzzy',
                        })

        self.stats['comparisons_made'] += len(matches)

        # Process matches
        for match_data in matches:
            self._process_match(match_data)

    def _already_matched(self, matches, actor1, actor2):
        """Check if this pair was already matched."""
        for match in matches:
            if (match['actor1'].id == actor1.id and match['actor2'].id == actor2.id) or \
               (match['actor1'].id == actor2.id and match['actor2'].id == actor1.id):
                return True
        return False

    def _process_match(self, match_data):
        """Process a single match and create ActorResolution if needed."""
        actor1 = match_data['actor1']
        actor2 = match_data['actor2']
        similarity = match_data['similarity']
        has_identifier_match = match_data['has_identifier_match']
        has_strong_alias = match_data['has_strong_alias']

        # Calculate confidence and decision
        confidence, decision = get_confidence_level(
            similarity=similarity,
            has_identifier_match=has_identifier_match,
            has_strong_alias=has_strong_alias,
        )

        # Determine match reason
        if has_identifier_match:
            match_reason = 'identifier'
        elif has_strong_alias:
            match_reason = 'strong_alias'
        elif similarity >= 0.85:
            match_reason = 'strong_alias'
        elif similarity >= 0.70:
            match_reason = 'weak_alias'
        else:
            match_reason = 'fuzzy'

        # Skip if decision is 'ignore' (confidence calculation determined this is too weak)
        if decision == 'ignore':
            self.stats['ignore'] += 1
            return

        self.stats['matches_found'] += 1
        self.stats[decision] += 1

        # Determine canonical actor (prefer the one with more data)
        canonical_actor = self._choose_canonical(actor1, actor2)

        # Print match details
        self._print_match(actor1, actor2, similarity, confidence, decision, match_reason)

        # Create ActorResolution record
        if not self.dry_run:
            # Check if resolution already exists
            existing = ActorResolution.objects.filter(
                Q(actor1=actor1, actor2=actor2) | Q(actor1=actor2, actor2=actor1)
            ).first()

            if existing:
                self.stats['duplicates_skipped'] += 1
                return

            with transaction.atomic():
                resolution = ActorResolution.objects.create(
                    actor1=actor1,
                    actor2=actor2,
                    canonical_actor=canonical_actor,
                    confidence=confidence,
                    decision=decision,
                    match_reason=match_reason,
                )

                # Auto-approve identifier matches if requested
                if self.auto_approve and decision == 'auto_merge':
                    # Note: We don't have a user object in management command
                    # This would need to be set manually in admin or via separate command
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Auto-merge candidate created (manual approval required)')
                    )

    def _choose_canonical(self, actor1, actor2):
        """Choose which actor should be canonical based on data richness."""
        # Prefer actor with more identifiers
        id_count1 = actor1.identifiers.count()
        id_count2 = actor2.identifiers.count()

        if id_count1 > id_count2:
            return actor1
        elif id_count2 > id_count1:
            return actor2

        # Prefer actor with earlier created_at date (assuming older = more established)
        if hasattr(actor1, 'created_at') and hasattr(actor2, 'created_at'):
            if actor1.created_at < actor2.created_at:
                return actor1
            else:
                return actor2

        # Default to actor1
        return actor1

    def _print_match(self, actor1, actor2, similarity, confidence, decision, match_reason):
        """Print formatted match details."""
        decision_symbols = {
            'auto_merge': '🟢',
            'review': '🟡',
            'suggest': '🔵',
            'ignore': '⚪',
        }

        symbol = decision_symbols.get(decision, '❓')

        self.stdout.write(
            f'\n{symbol} {decision.upper()} (confidence: {confidence:.2f}, similarity: {similarity:.2f}, reason: {match_reason})'
        )
        self.stdout.write(f'  Actor 1: [{actor1.id}] {actor1.name} ({actor1.__class__.__name__})')
        self.stdout.write(f'  Actor 2: [{actor2.id}] {actor2.name} ({actor2.__class__.__name__})')

    def _print_summary(self):
        """Print summary statistics."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('📊 Entity Resolution Summary'))
        self.stdout.write('='*80)

        self.stdout.write(f'\nActors scanned:       {self.stats["actors_scanned"]:,}')
        self.stdout.write(f'Comparisons made:     {self.stats["comparisons_made"]:,}')
        self.stdout.write(f'Matches found:        {self.stats["matches_found"]:,}')

        self.stdout.write('\nMatches by decision:')
        self.stdout.write(f'  🟢 Auto-merge:      {self.stats["auto_merge"]:,}')
        self.stdout.write(f'  🟡 Review:          {self.stats["review"]:,}')
        self.stdout.write(f'  🔵 Suggest:         {self.stats["suggest"]:,}')
        self.stdout.write(f'  ⚪ Ignored:         {self.stats["ignore"]:,}')

        if not self.dry_run:
            self.stdout.write(f'\nDuplicates skipped:   {self.stats["duplicates_skipped"]:,}')
            self.stdout.write('\n✅ ActorResolution records created in database')
        else:
            self.stdout.write('\n⚠️  DRY RUN - No database changes made')

        self.stdout.write('\n' + '='*80)

        # Next steps
        if self.stats['matches_found'] > 0 and not self.dry_run:
            self.stdout.write('\n📋 Next steps:')
            self.stdout.write('  1. Review ActorResolution records in Django admin')
            self.stdout.write('  2. Approve/reject merge candidates')
            self.stdout.write('  3. Run merge command to apply approved resolutions')

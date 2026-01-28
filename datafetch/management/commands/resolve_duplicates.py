"""
Entity resolution management command.

Scans Actor objects to identify potential duplicates using EntityResolutionService
and creates ActorResolution records for review/merging.

Usage:
    python manage.py resolve_duplicates --dry-run
    python manage.py resolve_duplicates --threshold 0.85
    python manage.py resolve_duplicates --limit 1000
    python manage.py resolve_duplicates --auto-approve
"""

import time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from datafetch.models import Actor, ActorResolution, Person, Organization
from datafetch.services.entity_resolution import EntityResolutionService


class Command(BaseCommand):
    help = 'Identify and resolve duplicate actors using EntityResolutionService'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview matches without creating ActorResolution records'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.70,
            help='Minimum confidence threshold (0.0-1.0, default: 0.70)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of actors to scan (0 = all)'
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
            help='Automatically mark high-confidence (>=0.95) matches as approved'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all pending ActorResolution records before running'
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume from the last processed actor ID found in resolutions'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Only scan actors whose name contains this string'
        )

    def _format_duration(self, seconds):
        """Format seconds into human-readable duration."""
        if seconds < 60:
            return f'{seconds:.1f}s'
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f'{mins}m {secs}s'
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f'{hours}h {mins}m'

    def _calculate_eta(self, batch_times, current_batch, total_batches):
        """Calculate ETA based on average batch time."""
        if not batch_times:
            return 'calculating...'
        avg_time = sum(batch_times) / len(batch_times)
        remaining_batches = total_batches - current_batch
        eta_seconds = avg_time * remaining_batches
        return self._format_duration(eta_seconds)

    def _print_summary(self, stats, total_elapsed):
        """Print execution summary."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Summary')
        self.stdout.write('='*60)
        self.stdout.write(f"Total Time: {self._format_duration(total_elapsed)}")
        self.stdout.write(f"Scanned: {stats['scanned']}")
        self.stdout.write(f"Matches found: {stats['matches']}")
        self.stdout.write(f"Auto-approved: {stats['auto_approved']}")
        self.stdout.write(f"Pending review: {stats['pending']}")
        self.stdout.write(f"Skipped existing: {stats['skipped_existing']}")

    def handle(self, *args, **options):
        # Track timing
        start_time = time.time()

        dry_run = options['dry_run']
        threshold = options['threshold']
        limit = options['limit']
        actor_type = options['type']
        auto_approve = options['auto_approve']
        clear = options['clear']
        resume = options['resume']
        name_filter = options['name']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No database changes will be made'))

        if clear and not dry_run:
            count = ActorResolution.objects.filter(review_status='pending').count()
            ActorResolution.objects.filter(review_status='pending').delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} pending resolutions'))

        # Initialize service with indexes
        self.stdout.write('Initializing EntityResolutionService (building indexes)...')
        service = EntityResolutionService()
        service.prefetch_all_actors()

        # Determine queryset
        queryset = Actor.objects.all().order_by('id')
        if actor_type == 'person':
            queryset = Person.objects.all().order_by('id')
        elif actor_type == 'organization':
            queryset = Organization.objects.all().order_by('id')

        # Filters
        if name_filter:
            self.stdout.write(f"Filtering actors by name containing: '{name_filter}'")
            queryset = queryset.filter(name__icontains=name_filter)

        # Resume logic
        if resume:
            from django.db.models import Max
            max_1 = ActorResolution.objects.aggregate(m=Max('actor1_id'))['m'] or 0
            max_2 = ActorResolution.objects.aggregate(m=Max('actor2_id'))['m'] or 0
            last_id = max(max_1, max_2)
            
            if last_id > 0:
                self.stdout.write(self.style.SUCCESS(f'Resuming from Actor ID {last_id}...'))
                queryset = queryset.filter(id__gt=last_id)

        if limit > 0:
            queryset = queryset[:limit]

        total_actors = queryset.count()
        self.stdout.write(f'Scanning {total_actors} actors for duplicates (threshold: {threshold})...')

        stats = {
            'scanned': 0,
            'matches': 0,
            'auto_approved': 0,
            'pending': 0,
            'skipped_existing': 0,
        }

        # Targeted mode: Exhaustive pairwise search within the name filter
        if name_filter:
            actors = list(queryset)
            for i, actor in enumerate(actors):
                stats['scanned'] += 1
                
                # Skip if current actor name is a single word
                if ' ' not in actor.name.strip():
                    continue

                for other in actors[i+1:]:
                    # Skip if other actor name is a single word
                    if ' ' not in other.name.strip():
                        continue

                    # Skip if already matched
                    if ActorResolution.objects.filter(
                        Q(actor1=actor, actor2=other) | Q(actor1=other, actor2=actor)
                    ).exists():
                        continue

                    # Calculate actual similarity
                    from datafetch.utils.normalization import calculate_name_similarity, get_confidence_level
                    similarity = calculate_name_similarity(actor.name, other.name)
                    
                    if similarity >= threshold:
                        confidence, decision = get_confidence_level(similarity)
                        stats['matches'] += 1
                        
                        # Use actor with more data as canonical
                        score1 = service.calculate_entity_score(actor)
                        score2 = service.calculate_entity_score(other)
                        
                        if score1 > score2:
                            canon = actor
                        elif score2 > score1:
                            canon = other
                        else:
                            # Tie-break with ID
                            canon = actor if actor.pk < other.pk else other
                        
                        self.stdout.write(
                            f"  Targeted Match: {actor.name} ({actor.pk}) ↔ {other.name} ({other.pk}) "
                            f"[{similarity:.2f}]"
                        )
                        
                        if not dry_run:
                            ActorResolution.objects.create(
                                actor1=actor if actor.pk < other.pk else other,
                                actor2=other if actor.pk < other.pk else actor,
                                canonical_actor=canon,
                                confidence=similarity,
                                match_reason='targeted_fuzzy',
                                decision='review',
                                review_status='pending'
                            )
            
            # Print Summary and Return
            self._print_summary(stats, time.time() - start_time)
            return

        batch_times = []
        batch_size = 1000
        total_batches = (total_actors + batch_size - 1) // batch_size
        batch_num = 0
        batch_start = time.time()

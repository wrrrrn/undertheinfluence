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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['threshold']
        limit = options['limit']
        actor_type = options['type']
        auto_approve = options['auto_approve']
        clear = options['clear']

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

        # Track timing
        start_time = time.time()
        batch_times = []
        batch_size = 1000
        total_batches = (total_actors + batch_size - 1) // batch_size
        batch_num = 0
        batch_start = time.time()

        # Scan actors
        # Use iterator to avoid memory issues
        for actor in queryset.iterator(chunk_size=batch_size):
            stats['scanned'] += 1
            
            # Progress update logic
            if stats['scanned'] % batch_size == 0:
                batch_num += 1
                batch_elapsed = time.time() - batch_start
                batch_times.append(batch_elapsed)
                eta = self._calculate_eta(batch_times, batch_num, total_batches)
                
                pct = (stats['scanned'] / total_actors) * 100
                self.stdout.write(
                    f"  [{pct:5.1f}%] Scanned {stats['scanned']}/{total_actors} | "
                    f"Matches: {stats['matches']} | "
                    f"{self._format_duration(batch_elapsed)}/batch | ETA: {eta}"
                )
                batch_start = time.time()

            # Find duplicates using service
            matches = service.find_duplicates(actor, min_confidence=threshold)

            for match in matches:
                # We only want one record per pair. Convention: actor1.id < actor2.id
                if actor.pk < match.canonical.pk:
                    actor1, actor2 = actor, match.canonical
                else:
                    actor1, actor2 = match.canonical, actor

                # Skip if exists
                if ActorResolution.objects.filter(actor1=actor1, actor2=actor2).exists():
                    stats['skipped_existing'] += 1
                    continue

                stats['matches'] += 1
                decision = 'review'
                review_status = 'pending'

                # Auto-approve logic
                if auto_approve and match.confidence >= 0.95:
                    decision = 'auto_merge'
                    review_status = 'approved'
                    stats['auto_approved'] += 1
                elif match.confidence >= 0.95:
                    decision = 'auto_merge' # Suggestion
                elif match.confidence >= 0.85:
                    decision = 'review'
                else:
                    decision = 'suggest'

                if decision != 'auto_merge':
                    stats['pending'] += 1

                self.stdout.write(
                    f"  Match: {actor1.name} ({actor1.pk}) ↔ {actor2.name} ({actor2.pk}) "
                    f"[{match.confidence:.2f}] {match.match_reason}"
                )

                if not dry_run:
                    ActorResolution.objects.create(
                        actor1=actor1,
                        actor2=actor2,
                        canonical_actor=match.canonical, # Service suggests canonical
                        confidence=match.confidence,
                        match_reason=match.match_reason,
                        decision=decision,
                        review_status=review_status
                    )

        total_elapsed = time.time() - start_time
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Summary')
        self.stdout.write('='*60)
        self.stdout.write(f"Total Time: {self._format_duration(total_elapsed)}")
        self.stdout.write(f"Scanned: {stats['scanned']}")
        self.stdout.write(f"Matches found: {stats['matches']}")
        self.stdout.write(f"Auto-approved: {stats['auto_approved']}")
        self.stdout.write(f"Pending review: {stats['pending']}")
        self.stdout.write(f"Skipped existing: {stats['skipped_existing']}")


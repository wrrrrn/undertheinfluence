"""
Populate Canonical Fields Management Command

Bootstrap entity resolution by populating canonical_* fields
for existing data using EntityResolutionService.

This is a STANDALONE command (not a fix type in clean_data.py) because:
- Processes 300k+ records (vs ~500-700 for typical cleanup fixes)
- Needs batch processing, progress tracking, resumability
- Different options than cleanup (confidence thresholds, dataset targeting)
- Users will run independently of other cleanup

Usage:
    # Dry-run to see impact
    python manage.py populate_canonical --dry-run

    # Bootstrap meetings only
    python manage.py populate_canonical --dataset meetings

    # Bootstrap donations only
    python manage.py populate_canonical --dataset donations

    # Full bootstrap with progress
    python manage.py populate_canonical --dataset all

    # With custom batch size and confidence
    python manage.py populate_canonical --batch-size 500 --min-confidence 0.80

Phase 3.2 Implementation - Entity Resolution Bootstrap
"""

import sys
import time
import logging
from typing import List, Dict, Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from datafetch.models import (
    MeetingAttendee, Donation, Consultancy, Actor
)
from datafetch.services.entity_resolution import EntityResolutionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate canonical_* fields using EntityResolutionService (Optimized)'

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

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--dataset',
            choices=['meetings', 'donations', 'consultancies', 'all'],
            default='all',
            help='Which dataset to process (default: all)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process per batch (default: 1000)'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.85,
            help='Minimum confidence score for auto-linking (default: 0.85)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress for each record'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Skip records that already have canonical set (default: True)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit total records to process (for testing, 0 = unlimited)'
        )
        parser.add_argument(
            '--fast',
            action='store_true',
            help='Fast mode: only identifier + exact name matching (skip slow fuzzy matching)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        dataset = options['dataset']
        batch_size = options['batch_size']
        min_confidence = options['min_confidence']
        verbose = options['verbose']
        skip_existing = options['skip_existing']
        limit = options['limit']
        fast_mode = options['fast']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN MODE] No changes will be made\n'))

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Entity Resolution Bootstrap (Optimized)'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Dataset: {dataset}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write(f'Min confidence: {min_confidence}')
        self.stdout.write(f'Verbose: {verbose}')
        self.stdout.write(f'Skip existing: {skip_existing}')
        self.stdout.write(f'Fast mode: {fast_mode}')
        if fast_mode:
            self.stdout.write(self.style.WARNING('  (identifier + exact name only, skipping slow fuzzy matching)'))
        else:
            self.stdout.write(self.style.HTTP_INFO('  (Full mode with score caching enabled)'))
        self.stdout.write('')

        # Show database counts first
        self._show_database_counts()

        # Track total time
        total_start_time = time.time()

        # Initialize service
        service = EntityResolutionService(fast_mode=fast_mode)
        
        # Prefetch for speed if processing all or large datasets
        if limit == 0 or limit > 1000:
            service.prefetch_all_actors()

        # Track totals
        totals = {
            'processed': 0,
            'resolved': 0,
            'skipped': 0,
            'errors': 0,
            'samples': [],  # Store sample resolutions to show
        }

        # Track remaining limit across datasets
        remaining_limit = limit if limit > 0 else float('inf')

        # Process each dataset
        if dataset in ['meetings', 'all'] and remaining_limit > 0:
            processed = self._process_meeting_attendees(
                service, dry_run, batch_size, min_confidence,
                verbose, skip_existing, totals, int(remaining_limit) if remaining_limit != float('inf') else 0
            )
            remaining_limit -= processed

        if dataset in ['donations', 'all'] and remaining_limit > 0:
            processed = self._process_donations(
                service, dry_run, batch_size, min_confidence,
                verbose, skip_existing, totals, int(remaining_limit) if remaining_limit != float('inf') else 0
            )
            remaining_limit -= processed

        if dataset in ['consultancies', 'all'] and remaining_limit > 0:
            self._process_consultancies(
                service, dry_run, batch_size, min_confidence,
                verbose, skip_existing, totals, int(remaining_limit) if remaining_limit != float('inf') else 0
            )

        # Calculate total elapsed time
        total_elapsed = time.time() - total_start_time

        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total processed: {totals["processed"]:,}')
        self.stdout.write(f'Total resolved: {totals["resolved"]:,}')
        self.stdout.write(f'Total skipped: {totals["skipped"]:,}')
        self.stdout.write(f'Total time: {self._format_duration(total_elapsed)}')

        if totals['errors'] > 0:
            self.stdout.write(self.style.WARNING(f'Errors: {totals["errors"]}'))

        if totals['processed'] > 0:
            resolution_rate = (totals['resolved'] / totals['processed']) * 100
            self.stdout.write(self.style.SUCCESS(f'Resolution rate: {resolution_rate:.1f}%'))

        # Log service stats
        stats = service.get_stats()
        self.stdout.write('')
        self.stdout.write('Entity Resolution Statistics:')
        self.stdout.write(f'  Identifier matches: {stats["identifier_matches"]}')
        self.stdout.write(f'  EC ID matches: {stats.get("ec_id_matches", 0)}')
        self.stdout.write(f'  Exact matches: {stats["exact_matches"]}')
        self.stdout.write(f'  OtherName strong: {stats.get("othername_strong_matches", 0)}')
        self.stdout.write(f'  Strong matches: {stats["strong_matches"]}')
        self.stdout.write(f'  OtherName weak: {stats.get("othername_weak_matches", 0)}')
        self.stdout.write(f'  Weak matches: {stats["weak_matches"]}')
        self.stdout.write(f'  Cache hits: {stats["cache_hits"]}')
        
        # New stats if available
        if hasattr(service, '_score_cache'):
            self.stdout.write(f'  Score cache size: {len(service._score_cache)}')

        # Show sample resolutions
        if totals['samples']:
            self.stdout.write('')
            self.stdout.write(self.style.HTTP_INFO('Sample Resolutions (first 20):'))
            self.stdout.write(self.style.HTTP_INFO('-' * 70))
            for sample in totals['samples'][:20]:
                self.stdout.write(
                    f"  {sample['source'][:40]:<40} -> "
                    f"{sample['target'][:30]:<30} ({sample['confidence']:.2f}, {sample['match_reason']})"
                )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS('\nBootstrap complete!'))

    def _show_database_counts(self):
        """Show current database counts for context."""
        self.stdout.write(self.style.HTTP_INFO('Current Database State:'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Meeting attendees
        total_attendees = MeetingAttendee.objects.count()
        linked_attendees = MeetingAttendee.objects.filter(canonical_actor__isnull=False).count()
        unlinked_attendees = total_attendees - linked_attendees

        # Donations
        total_donations = Donation.objects.count()
        linked_donors = Donation.objects.filter(canonical_donor__isnull=False).count()
        linked_recipients = Donation.objects.filter(canonical_recipient__isnull=False).count()

        # Consultancies
        total_consultancies = Consultancy.objects.count()
        linked_clients = Consultancy.objects.filter(canonical_client__isnull=False).count()
        linked_agencies = Consultancy.objects.filter(canonical_agency__isnull=False).count()

        self.stdout.write(f'  Meeting Attendees: {total_attendees:,} total, {linked_attendees:,} linked, {unlinked_attendees:,} unlinked')
        self.stdout.write(f'  Donations: {total_donations:,} total')
        self.stdout.write(f'    - Donors linked: {linked_donors:,}')
        self.stdout.write(f'    - Recipients linked: {linked_recipients:,}')
        self.stdout.write(f'  Consultancies: {total_consultancies:,} total')
        self.stdout.write(f'    - Clients linked: {linked_clients:,}')
        self.stdout.write(f'    - Agencies linked: {linked_agencies:,}')
        self.stdout.write('')

    def _process_meeting_attendees(self, service, dry_run, batch_size,
                                   min_confidence, verbose, skip_existing, totals, limit=0):
        """Process MeetingAttendee records."""
        self.stdout.write(self.style.HTTP_INFO('\n## Processing MeetingAttendees'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Build queryset ordered by ID for stable cursor-based pagination
        queryset = MeetingAttendee.objects.select_related('actor').order_by('id')

        if skip_existing:
            queryset = queryset.filter(canonical_actor__isnull=True)

        total = queryset.count()
        if limit > 0:
            total = min(total, limit)
        self.stdout.write(f'Found {queryset.count()} records, processing {total}')

        if total == 0:
            return 0

        processed = 0
        resolved = 0
        errors = 0
        batch_times = []
        total_batches = (total + batch_size - 1) // batch_size
        last_id = 0  # Cursor for stable pagination

        # Process in batches using cursor-based pagination (id > last_id)
        batch_num = 0
        while processed < total:
            batch_start = time.time()
            # Cursor-based query: get next batch where id > last_id
            batch = list(queryset.filter(id__gt=last_id)[:batch_size])
            if not batch:
                break
            last_id = batch[-1].id  # Update cursor to last ID in batch
            updates = []
            batch_num += 1

            self.stdout.write(f'  Processing batch {batch_num}... ', ending='')
            self.stdout.flush()

            # Pre-resolve unique actors for this batch to reduce service calls
            unique_actors = {}
            for attendee in batch:
                if attendee.actor_id and attendee.actor_id not in unique_actors:
                    unique_actors[attendee.actor_id] = attendee.actor

            batch_resolutions = {}
            for actor_id, actor in unique_actors.items():
                batch_resolutions[actor_id] = service.resolve_with_confidence(actor)

            for idx, attendee in enumerate(batch):
                if (idx + 1) % 50 == 0:
                    self.stdout.write('.', ending='')
                    self.stdout.flush()
                try:
                    # Use pre-resolved result
                    result = batch_resolutions.get(attendee.actor_id)
                    if not result:
                        result = service.resolve_with_confidence(attendee.actor)

                    if result.is_resolved and result.confidence >= min_confidence:
                        # Don't link to self
                        if result.canonical.pk != attendee.actor_id:
                            if verbose:
                                self.stdout.write(
                                    f'  {attendee.actor.name} -> '
                                    f'{result.canonical.name} ({result.confidence:.2f}, {result.match_reason})'
                                )

                            # Store sample for summary
                            if len(totals['samples']) < 50:
                                totals['samples'].append({
                                    'source': attendee.actor.name,
                                    'target': result.canonical.name,
                                    'confidence': result.confidence,
                                    'match_reason': result.match_reason,
                                })

                            if not dry_run:
                                attendee.canonical_actor_id = result.canonical.pk
                                updates.append(attendee)

                            resolved += 1
                        else:
                            totals['skipped'] += 1
                    else:
                        totals['skipped'] += 1

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing attendee {attendee.pk}: {e}')

            # Bulk update for this batch
            if updates and not dry_run:
                MeetingAttendee.objects.bulk_update(updates, ['canonical_actor'])

            # Calculate timing
            batch_elapsed = time.time() - batch_start
            batch_times.append(batch_elapsed)
            eta = self._calculate_eta(batch_times, batch_num, total_batches)

            # Progress update every batch
            pct = (processed / total) * 100 if total > 0 else 0
            self.stdout.write(
                f'  [{pct:5.1f}%] Batch {batch_num}/{total_batches}: {processed:,}/{total:,} '
                f'| Resolved: {resolved:,} | {self._format_duration(batch_elapsed)}/batch | ETA: {eta}'
            )
            self.stdout.flush()

        self.stdout.write(f'\n  ✓ MeetingAttendees complete: {processed:,} processed, {resolved:,} resolved')
        self.stdout.flush()

        totals['processed'] += processed
        totals['resolved'] += resolved
        totals['errors'] += errors

        return processed

    def _process_donations(self, service, dry_run, batch_size,
                           min_confidence, verbose, skip_existing, totals, limit=0):
        """Process Donation records (donor and recipient fields)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Processing Donations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        processed_count = 0

        # Process donor field
        self.stdout.write('\nProcessing donor field...')
        donor_queryset = Donation.objects.select_related('donor')

        if skip_existing:
            donor_queryset = donor_queryset.filter(
                canonical_donor__isnull=True,
                donor__isnull=False
            )

        donor_total = donor_queryset.count()
        if limit > 0:
            donor_total = min(donor_total, limit)
        self.stdout.write(f'Found {donor_queryset.count()} donor records to process (limit: {donor_total})')

        if donor_total > 0:
            p = self._process_donation_field(
                service, donor_queryset, 'donor', 'canonical_donor',
                dry_run, batch_size, min_confidence, verbose, totals, donor_total
            )
            processed_count += p
            
            # Reduce limit for next pass if needed
            if limit > 0:
                limit -= p
                if limit <= 0:
                    return processed_count

        # Process recipient field
        self.stdout.write('\nProcessing recipient field...')
        recipient_queryset = Donation.objects.select_related('recipient')

        if skip_existing:
            recipient_queryset = recipient_queryset.filter(
                canonical_recipient__isnull=True,
                recipient__isnull=False
            )

        recipient_total = recipient_queryset.count()
        if limit > 0:
            recipient_total = min(recipient_total, limit)
        self.stdout.write(f'Found {recipient_queryset.count()} recipient records to process (limit: {recipient_total})')

        if recipient_total > 0:
            p = self._process_donation_field(
                service, recipient_queryset, 'recipient', 'canonical_recipient',
                dry_run, batch_size, min_confidence, verbose, totals, recipient_total
            )
            processed_count += p

        return processed_count

    def _process_donation_field(self, service, queryset, source_field,
                                target_field, dry_run, batch_size,
                                min_confidence, verbose, totals, limit):
        """Process a single field on Donation records."""
        # Order by ID for stable cursor-based pagination
        queryset = queryset.order_by('id')
        total = min(queryset.count(), limit) if limit > 0 else queryset.count()
        processed = 0
        resolved = 0
        errors = 0
        batch_times = []
        total_batches = (total + batch_size - 1) // batch_size
        last_id = 0  # Cursor for stable pagination

        batch_num = 0
        while processed < total:
            batch_start = time.time()
            remaining = total - processed
            batch_limit = min(batch_size, remaining)
            batch = list(queryset.filter(id__gt=last_id)[:batch_limit])
            if not batch:
                break
            last_id = batch[-1].id
            updates = []
            batch_num += 1

            self.stdout.write(f'  Processing batch {batch_num}... ', ending='')
            self.stdout.flush()

            # Pre-resolve unique actors for this batch to reduce service calls
            unique_actors = {}
            for donation in batch:
                actor = getattr(donation, source_field)
                if actor and actor.pk not in unique_actors:
                    unique_actors[actor.pk] = actor

            batch_resolutions = {}
            for actor_id, actor in unique_actors.items():
                batch_resolutions[actor_id] = service.resolve_with_confidence(actor)

            for idx, donation in enumerate(batch):
                if (idx + 1) % 50 == 0:
                    self.stdout.write('.', ending='')
                    self.stdout.flush()
                try:
                    actor = getattr(donation, source_field)
                    if not actor:
                        totals['skipped'] += 1
                        processed += 1
                        continue

                    # Use pre-resolved result
                    result = batch_resolutions.get(actor.pk)
                    if not result:
                        result = service.resolve_with_confidence(actor)

                    if result.is_resolved and result.confidence >= min_confidence:
                        if result.canonical.pk != actor.pk:
                            if verbose:
                                self.stdout.write(
                                    f'  {actor.name} -> '
                                    f'{result.canonical.name} ({result.confidence:.2f}, {result.match_reason})'
                                )

                            # Store sample for summary
                            if len(totals['samples']) < 50:
                                totals['samples'].append({
                                    'source': actor.name,
                                    'target': result.canonical.name,
                                    'confidence': result.confidence,
                                    'match_reason': result.match_reason,
                                })

                            if not dry_run:
                                setattr(donation, target_field, result.canonical)
                                updates.append(donation)

                            resolved += 1
                        else:
                            totals['skipped'] += 1
                    else:
                        totals['skipped'] += 1

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing donation {donation.pk}: {e}')

            # Bulk update
            if updates and not dry_run:
                Donation.objects.bulk_update(updates, [target_field])

            # Calculate timing
            batch_elapsed = time.time() - batch_start
            batch_times.append(batch_elapsed)
            eta = self._calculate_eta(batch_times, batch_num, total_batches)

            # Progress update every batch
            pct = (processed / total) * 100 if total > 0 else 0
            self.stdout.write(
                f'  [{pct:5.1f}%] Batch {batch_num}/{total_batches}: {processed:,}/{total:,} '
                f'| Resolved: {resolved:,} | {self._format_duration(batch_elapsed)}/batch | ETA: {eta}'
            )
            self.stdout.flush()

        self.stdout.write(f'\n  ✓ Donations field complete: {processed:,} processed, {resolved:,} resolved')
        self.stdout.flush()

        totals['processed'] += processed
        totals['resolved'] += resolved
        totals['errors'] += errors
        
        return processed

    def _process_consultancies(self, service, dry_run, batch_size,
                               min_confidence, verbose, skip_existing, totals, limit=0):
        """Process Consultancy records (client and agency fields)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Processing Consultancies'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        processed_count = 0

        # Process client field
        self.stdout.write('\nProcessing client field...')
        client_queryset = Consultancy.objects.select_related('client')

        if skip_existing:
            client_queryset = client_queryset.filter(
                canonical_client__isnull=True,
                client__isnull=False
            )

        client_total = client_queryset.count()
        if limit > 0:
            client_total = min(client_total, limit)
        self.stdout.write(f'Found {client_queryset.count()} client records to process (limit: {client_total})')

        if client_total > 0:
            p = self._process_consultancy_field(
                service, client_queryset, 'client', 'canonical_client',
                dry_run, batch_size, min_confidence, verbose, totals, client_total
            )
            processed_count += p
            
            if limit > 0:
                limit -= p
                if limit <= 0:
                    return processed_count

        # Process agency field
        self.stdout.write('\nProcessing agency field...')
        agency_queryset = Consultancy.objects.select_related('agency')

        if skip_existing:
            agency_queryset = agency_queryset.filter(
                canonical_agency__isnull=True,
                agency__isnull=False
            )

        agency_total = agency_queryset.count()
        if limit > 0:
            agency_total = min(agency_total, limit)
        self.stdout.write(f'Found {agency_queryset.count()} agency records to process (limit: {agency_total})')

        if agency_total > 0:
            p = self._process_consultancy_field(
                service, agency_queryset, 'agency', 'canonical_agency',
                dry_run, batch_size, min_confidence, verbose, totals, agency_total
            )
            processed_count += p
            
        return processed_count

    def _process_consultancy_field(self, service, queryset, source_field,
                                   target_field, dry_run, batch_size,
                                   min_confidence, verbose, totals, limit):
        """Process a single field on Consultancy records."""
        # Order by ID for stable cursor-based pagination
        queryset = queryset.order_by('id')
        total = min(queryset.count(), limit) if limit > 0 else queryset.count()
        processed = 0
        resolved = 0
        errors = 0
        batch_times = []
        total_batches = (total + batch_size - 1) // batch_size
        last_id = 0  # Cursor for stable pagination

        batch_num = 0
        while processed < total:
            batch_start = time.time()
            remaining = total - processed
            batch_limit = min(batch_size, remaining)
            batch = list(queryset.filter(id__gt=last_id)[:batch_limit])
            if not batch:
                break
            last_id = batch[-1].id
            updates = []
            batch_num += 1

            self.stdout.write(f'  Processing batch {batch_num}... ', ending='')
            self.stdout.flush()

            # Pre-resolve unique actors for this batch to reduce service calls
            unique_actors = {}
            for consultancy in batch:
                actor = getattr(consultancy, source_field)
                if actor and actor.pk not in unique_actors:
                    unique_actors[actor.pk] = actor

            batch_resolutions = {}
            for actor_id, actor in unique_actors.items():
                batch_resolutions[actor_id] = service.resolve_with_confidence(actor)

            for idx, consultancy in enumerate(batch):
                if (idx + 1) % 50 == 0:
                    self.stdout.write('.', ending='')
                    self.stdout.flush()
                try:
                    actor = getattr(consultancy, source_field)
                    if not actor:
                        totals['skipped'] += 1
                        processed += 1
                        continue

                    # Use pre-resolved result
                    result = batch_resolutions.get(actor.pk)
                    if not result:
                        result = service.resolve_with_confidence(actor)

                    if result.is_resolved and result.confidence >= min_confidence:
                        if result.canonical.pk != actor.pk:
                            if verbose:
                                self.stdout.write(
                                    f'  {actor.name} -> '
                                    f'{result.canonical.name} ({result.confidence:.2f}, {result.match_reason})'
                                )

                            # Store sample for summary
                            if len(totals['samples']) < 50:
                                totals['samples'].append({
                                    'source': actor.name,
                                    'target': result.canonical.name,
                                    'confidence': result.confidence,
                                    'match_reason': result.match_reason,
                                })

                            if not dry_run:
                                setattr(consultancy, target_field, result.canonical)
                                updates.append(consultancy)

                            resolved += 1
                        else:
                            totals['skipped'] += 1
                    else:
                        totals['skipped'] += 1

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing consultancy {consultancy.pk}: {e}')

            # Bulk update
            if updates and not dry_run:
                Consultancy.objects.bulk_update(updates, [target_field])

            # Calculate timing
            batch_elapsed = time.time() - batch_start
            batch_times.append(batch_elapsed)
            eta = self._calculate_eta(batch_times, batch_num, total_batches)

            # Progress update every batch
            pct = (processed / total) * 100 if total > 0 else 0
            self.stdout.write(
                f'  [{pct:5.1f}%] Batch {batch_num}/{total_batches}: {processed:,}/{total:,} '
                f'| Resolved: {resolved:,} | {self._format_duration(batch_elapsed)}/batch | ETA: {eta}'
            )
            self.stdout.flush()

        self.stdout.write(f'\n  ✓ Consultancies field complete: {processed:,} processed, {resolved:,} resolved')
        self.stdout.flush()

        totals['processed'] += processed
        totals['resolved'] += resolved
        totals['errors'] += errors
        
        return processed
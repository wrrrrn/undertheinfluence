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
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from datafetch.models import (
    MeetingAttendee, Donation, Consultancy, Actor
)
from datafetch.services.entity_resolution import EntityResolutionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate canonical_* fields using EntityResolutionService'

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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        dataset = options['dataset']
        batch_size = options['batch_size']
        min_confidence = options['min_confidence']
        verbose = options['verbose']
        skip_existing = options['skip_existing']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN MODE] No changes will be made\n'))

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Entity Resolution Bootstrap'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Dataset: {dataset}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write(f'Min confidence: {min_confidence}')
        self.stdout.write('')

        # Initialize service
        service = EntityResolutionService()

        # Track totals
        totals = {
            'processed': 0,
            'resolved': 0,
            'skipped': 0,
            'errors': 0,
        }

        # Process each dataset
        if dataset in ['meetings', 'all']:
            self._process_meeting_attendees(
                service, dry_run, batch_size, min_confidence,
                verbose, skip_existing, totals
            )

        if dataset in ['donations', 'all']:
            self._process_donations(
                service, dry_run, batch_size, min_confidence,
                verbose, skip_existing, totals
            )

        if dataset in ['consultancies', 'all']:
            self._process_consultancies(
                service, dry_run, batch_size, min_confidence,
                verbose, skip_existing, totals
            )

        # Print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Total processed: {totals["processed"]}')
        self.stdout.write(f'Total resolved: {totals["resolved"]}')
        self.stdout.write(f'Total skipped: {totals["skipped"]}')

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
        self.stdout.write(f'  Exact matches: {stats["exact_matches"]}')
        self.stdout.write(f'  Strong matches: {stats["strong_matches"]}')
        self.stdout.write(f'  Weak matches: {stats["weak_matches"]}')
        self.stdout.write(f'  Cache hits: {stats["cache_hits"]}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes were made'))
        else:
            self.stdout.write(self.style.SUCCESS('\nBootstrap complete!'))

    def _process_meeting_attendees(self, service, dry_run, batch_size,
                                   min_confidence, verbose, skip_existing, totals):
        """Process MeetingAttendee records."""
        self.stdout.write(self.style.HTTP_INFO('\n## Processing MeetingAttendees'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Build queryset
        queryset = MeetingAttendee.objects.select_related('actor')

        if skip_existing:
            queryset = queryset.filter(canonical_actor__isnull=True)

        total = queryset.count()
        self.stdout.write(f'Found {total} records to process')

        if total == 0:
            return

        processed = 0
        resolved = 0
        errors = 0

        # Process in batches
        for i in range(0, total, batch_size):
            batch = list(queryset[i:i + batch_size])

            for attendee in batch:
                try:
                    result = service.resolve_with_confidence(attendee.actor)

                    if result.is_resolved and result.confidence >= min_confidence:
                        # Don't link to self
                        if result.canonical.pk != attendee.actor_id:
                            if verbose:
                                self.stdout.write(
                                    f'  {attendee.actor.name} -> '
                                    f'{result.canonical.name} ({result.confidence:.2f})'
                                )

                            if not dry_run:
                                attendee.canonical_actor_id = result.canonical.pk
                                attendee.save(update_fields=['canonical_actor_id'])

                            resolved += 1
                        else:
                            totals['skipped'] += 1
                    else:
                        totals['skipped'] += 1

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing attendee {attendee.pk}: {e}')

            # Progress update
            self.stdout.write(
                f'  Processed {min(i + batch_size, total)}/{total} '
                f'({resolved} resolved)',
                ending='\r'
            )
            sys.stdout.flush()

        self.stdout.write('')  # New line after progress
        self.stdout.write(f'  Completed: {processed} processed, {resolved} resolved')

        totals['processed'] += processed
        totals['resolved'] += resolved
        totals['errors'] += errors

    def _process_donations(self, service, dry_run, batch_size,
                           min_confidence, verbose, skip_existing, totals):
        """Process Donation records (donor and recipient fields)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Processing Donations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Process donor field
        self.stdout.write('\nProcessing donor field...')
        donor_queryset = Donation.objects.select_related('donor')

        if skip_existing:
            donor_queryset = donor_queryset.filter(
                canonical_donor__isnull=True,
                donor__isnull=False
            )

        donor_total = donor_queryset.count()
        self.stdout.write(f'Found {donor_total} donor records to process')

        if donor_total > 0:
            self._process_donation_field(
                service, donor_queryset, 'donor', 'canonical_donor_id',
                dry_run, batch_size, min_confidence, verbose, totals
            )

        # Process recipient field
        self.stdout.write('\nProcessing recipient field...')
        recipient_queryset = Donation.objects.select_related('recipient')

        if skip_existing:
            recipient_queryset = recipient_queryset.filter(
                canonical_recipient__isnull=True,
                recipient__isnull=False
            )

        recipient_total = recipient_queryset.count()
        self.stdout.write(f'Found {recipient_total} recipient records to process')

        if recipient_total > 0:
            self._process_donation_field(
                service, recipient_queryset, 'recipient', 'canonical_recipient_id',
                dry_run, batch_size, min_confidence, verbose, totals
            )

    def _process_donation_field(self, service, queryset, source_field,
                                target_field, dry_run, batch_size,
                                min_confidence, verbose, totals):
        """Process a single field on Donation records."""
        total = queryset.count()
        processed = 0
        resolved = 0
        errors = 0

        for i in range(0, total, batch_size):
            batch = list(queryset[i:i + batch_size])

            for donation in batch:
                try:
                    actor = getattr(donation, source_field)
                    if not actor:
                        totals['skipped'] += 1
                        processed += 1
                        continue

                    result = service.resolve_with_confidence(actor)

                    if result.is_resolved and result.confidence >= min_confidence:
                        if result.canonical.pk != actor.pk:
                            if verbose:
                                self.stdout.write(
                                    f'  {actor.name} -> '
                                    f'{result.canonical.name} ({result.confidence:.2f})'
                                )

                            if not dry_run:
                                setattr(donation, target_field, result.canonical.pk)
                                donation.save(update_fields=[target_field])

                            resolved += 1
                        else:
                            totals['skipped'] += 1
                    else:
                        totals['skipped'] += 1

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing donation {donation.pk}: {e}')

            # Progress update
            self.stdout.write(
                f'  Processed {min(i + batch_size, total)}/{total} '
                f'({resolved} resolved)',
                ending='\r'
            )
            sys.stdout.flush()

        self.stdout.write('')
        self.stdout.write(f'  Completed: {processed} processed, {resolved} resolved')

        totals['processed'] += processed
        totals['resolved'] += resolved
        totals['errors'] += errors

    def _process_consultancies(self, service, dry_run, batch_size,
                               min_confidence, verbose, skip_existing, totals):
        """Process Consultancy records (client and agency fields)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Processing Consultancies'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Process client field
        self.stdout.write('\nProcessing client field...')
        client_queryset = Consultancy.objects.select_related('client')

        if skip_existing:
            client_queryset = client_queryset.filter(
                canonical_client__isnull=True,
                client__isnull=False
            )

        client_total = client_queryset.count()
        self.stdout.write(f'Found {client_total} client records to process')

        if client_total > 0:
            self._process_consultancy_field(
                service, client_queryset, 'client', 'canonical_client_id',
                dry_run, batch_size, min_confidence, verbose, totals
            )

        # Process agency field
        self.stdout.write('\nProcessing agency field...')
        agency_queryset = Consultancy.objects.select_related('agency')

        if skip_existing:
            agency_queryset = agency_queryset.filter(
                canonical_agency__isnull=True,
                agency__isnull=False
            )

        agency_total = agency_queryset.count()
        self.stdout.write(f'Found {agency_total} agency records to process')

        if agency_total > 0:
            self._process_consultancy_field(
                service, agency_queryset, 'agency', 'canonical_agency_id',
                dry_run, batch_size, min_confidence, verbose, totals
            )

    def _process_consultancy_field(self, service, queryset, source_field,
                                   target_field, dry_run, batch_size,
                                   min_confidence, verbose, totals):
        """Process a single field on Consultancy records."""
        total = queryset.count()
        processed = 0
        resolved = 0
        errors = 0

        for i in range(0, total, batch_size):
            batch = list(queryset[i:i + batch_size])

            for consultancy in batch:
                try:
                    actor = getattr(consultancy, source_field)
                    if not actor:
                        totals['skipped'] += 1
                        processed += 1
                        continue

                    result = service.resolve_with_confidence(actor)

                    if result.is_resolved and result.confidence >= min_confidence:
                        if result.canonical.pk != actor.pk:
                            if verbose:
                                self.stdout.write(
                                    f'  {actor.name} -> '
                                    f'{result.canonical.name} ({result.confidence:.2f})'
                                )

                            if not dry_run:
                                setattr(consultancy, target_field, result.canonical.pk)
                                consultancy.save(update_fields=[target_field])

                            resolved += 1
                        else:
                            totals['skipped'] += 1
                    else:
                        totals['skipped'] += 1

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f'Error processing consultancy {consultancy.pk}: {e}')

            # Progress update
            self.stdout.write(
                f'  Processed {min(i + batch_size, total)}/{total} '
                f'({resolved} resolved)',
                ending='\r'
            )
            sys.stdout.flush()

        self.stdout.write('')
        self.stdout.write(f'  Completed: {processed} processed, {resolved} resolved')

        totals['processed'] += processed
        totals['resolved'] += resolved
        totals['errors'] += errors

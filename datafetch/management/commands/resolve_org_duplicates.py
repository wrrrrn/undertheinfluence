"""
Resolve Organisation Duplicates Management Command

Sets Actor.canonical_entry for organisations using deterministic matching:
1. Companies House number grouping (1.0 confidence — zero ambiguity)
2. General backfill using EntityResolutionService 7-pass cascade

Usage:
    # Dry-run to see impact
    python manage.py resolve_org_duplicates --dry-run

    # Phase 1 only: CH-number linking (fast, deterministic)
    python manage.py resolve_org_duplicates --ch-only

    # Full run: CH-number + general backfill
    python manage.py resolve_org_duplicates

    # With custom confidence for general backfill
    python manage.py resolve_org_duplicates --min-confidence 0.80
"""

import time
import logging
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

from datafetch.models import Actor, Organization
from datafetch.models.influence_mapping import CompaniesHouseMatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Resolve organisation duplicates by setting Actor.canonical_entry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--ch-only',
            action='store_true',
            help='Only do Companies House number linking (Phase 1)'
        )
        parser.add_argument(
            '--backfill-only',
            action='store_true',
            help='Only do general backfill (Phase 2), skip CH linking'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.85,
            help='Minimum confidence for general backfill (default: 0.85)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for general backfill (default: 500)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit total orgs to process in backfill (for testing)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        ch_only = options['ch_only']
        backfill_only = options['backfill_only']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made\n'))

        # Phase 1: Companies House number linking
        if not backfill_only:
            self._phase1_ch_linking(dry_run)

        # Phase 2: General backfill
        if not ch_only:
            self._phase2_general_backfill(
                dry_run=dry_run,
                min_confidence=options['min_confidence'],
                batch_size=options['batch_size'],
                limit=options['limit'],
            )

    def _phase1_ch_linking(self, dry_run: bool):
        """
        Phase 1: Group orgs by Companies House number and set canonical_entry.

        For each company number with multiple approved matches:
        - Score each org by data richness (relationships, identifiers)
        - Pick the highest-scoring as canonical
        - Set canonical_entry on all others
        """
        from datafetch.models import Donation
        from datafetch.models.influence_mapping import MeetingAttendee, Consultancy

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 1: Companies House Number Linking ===\n'))

        # Find all CH numbers with multiple approved org matches
        ch_groups = (
            CompaniesHouseMatch.objects
            .filter(
                status__in=['approved', 'auto_approved'],
                company_number__isnull=False,
            )
            .exclude(company_number='')
            .values('company_number')
            .annotate(org_count=Count('organization', distinct=True))
            .filter(org_count__gt=1)
            .order_by('-org_count')
        )

        total_groups = ch_groups.count()
        self.stdout.write(f'Found {total_groups} CH numbers with multiple org matches\n')

        if total_groups == 0:
            self.stdout.write(self.style.SUCCESS('No duplicates to resolve.\n'))
            return

        linked = 0
        skipped_already_linked = 0
        groups_processed = 0

        for group in ch_groups:
            company_number = group['company_number']

            # Get all org IDs for this CH number
            org_ids = list(
                CompaniesHouseMatch.objects
                .filter(
                    company_number=company_number,
                    status__in=['approved', 'auto_approved'],
                )
                .values_list('organization_id', flat=True)
                .distinct()
            )

            if len(org_ids) < 2:
                continue

            # Load actors — use non_polymorphic() to avoid recursion with annotations
            actors = list(Actor.objects.non_polymorphic().filter(id__in=org_ids))

            if not actors:
                continue

            # Score using raw SQL to avoid any ORM/polymorphic recursion issues
            from django.db import connection
            actor_scores = {}
            for a in actors:
                aid = a.id
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                          (SELECT COUNT(*) FROM datafetch_donation WHERE donor_id=%s OR recipient_id=%s) * 20 +
                          (SELECT COUNT(*) FROM datafetch_meetingattendee WHERE actor_id=%s) * 10 +
                          (SELECT COUNT(*) FROM datafetch_consultancy WHERE client_id=%s OR agency_id=%s) * 15
                    """, [aid, aid, aid, aid, aid])
                    s = cursor.fetchone()[0] or 0
                if a.canonical_entry_id is None:
                    s += 1000  # prefer non-duplicates
                actor_scores[a.id] = s

            def score(a):
                return actor_scores.get(a.id, 0)

            actors.sort(key=score, reverse=True)
            canonical = actors[0]

            # Follow existing canonical chain if the winner is already a duplicate
            if canonical.canonical_entry_id is not None:
                # Follow chain manually (avoid recursive property with non_polymorphic)
                seen = {canonical.id}
                target_id = canonical.canonical_entry_id
                while target_id and target_id not in seen:
                    seen.add(target_id)
                    try:
                        canonical = Actor.objects.non_polymorphic().get(id=target_id)
                        target_id = canonical.canonical_entry_id
                    except Actor.DoesNotExist:
                        break

            # Link the rest to canonical
            for actor in actors[1:]:
                if actor.id == canonical.id:
                    continue
                if actor.canonical_entry_id is not None:
                    skipped_already_linked += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  Would link: {actor.name} (#{actor.id}) → {canonical.name} (#{canonical.id}) '
                        f'[CH: {company_number}]'
                    )
                else:
                    actor.canonical_entry_id = canonical.id
                    actor.save(update_fields=['canonical_entry_id'])

                linked += 1

            groups_processed += 1
            if groups_processed % 200 == 0:
                self.stdout.write(f'  Processed {groups_processed}/{total_groups} groups, linked {linked} orgs...')

        self.stdout.write(f'\nPhase 1 complete:')
        self.stdout.write(f'  Groups processed: {groups_processed}')
        self.stdout.write(f'  Orgs linked: {linked}')
        self.stdout.write(f'  Already linked (skipped): {skipped_already_linked}')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'  (DRY RUN — no changes made)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ {linked} organisations linked to canonical entries'))

    def _phase2_general_backfill(self, dry_run: bool, min_confidence: float,
                                  batch_size: int, limit: int = None):
        """
        Phase 2: Use EntityResolutionService to backfill canonical_entry on
        remaining unlinked organisations.
        """
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Phase 2: General Backfill (min_confidence={min_confidence}) ===\n'
        ))

        from datafetch.services.entity_resolution import EntityResolutionService

        queryset = (
            Actor.objects
            .filter(
                canonical_entry__isnull=True,
                organization__isnull=False,  # only orgs
            )
            .order_by('id')
        )

        if limit:
            queryset = queryset[:limit]

        total = queryset.count() if not limit else min(limit, queryset.count())
        self.stdout.write(f'Orgs to process: {total}\n')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No orgs to process.\n'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY RUN — running resolution but not saving. '
                'This still takes time for the 7-pass cascade.\n'
            ))

        # Initialise the service with prefetched indexes
        self.stdout.write('Building in-memory indexes (this may take a minute)...')
        start = time.time()
        service = EntityResolutionService(fast_mode=True)
        service.prefetch_all_actors()
        self.stdout.write(f'Indexes built in {time.time() - start:.1f}s\n')

        linked = 0
        skipped = 0
        processed = 0
        batch_start = time.time()

        for actor in queryset.iterator(chunk_size=batch_size):
            processed += 1

            result = service.resolve_with_confidence(actor)

            if (result.is_resolved
                    and result.confidence >= min_confidence
                    and result.canonical.pk != actor.pk):

                if dry_run:
                    if linked < 20:  # only show first 20
                        self.stdout.write(
                            f'  Would link: {actor.name} (#{actor.id}) → '
                            f'{result.canonical.name} (#{result.canonical.pk}) '
                            f'[{result.match_reason}, conf={result.confidence:.2f}]'
                        )
                else:
                    actor.canonical_entry_id = result.canonical.pk
                    actor.save(update_fields=['canonical_entry_id'])

                linked += 1
            else:
                skipped += 1

            if processed % 1000 == 0:
                elapsed = time.time() - batch_start
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total - processed) / rate if rate > 0 else 0
                self.stdout.write(
                    f'  Processed {processed}/{total} ({rate:.0f}/s), '
                    f'linked {linked}, ETA {eta:.0f}s'
                )

        self.stdout.write(f'\nPhase 2 complete:')
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Linked: {linked}')
        self.stdout.write(f'  Skipped: {skipped}')
        self.stdout.write(f'  Total time: {time.time() - batch_start:.1f}s')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'  (DRY RUN — no changes made)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ {linked} organisations linked to canonical entries'))

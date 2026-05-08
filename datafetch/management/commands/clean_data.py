"""
Data cleaning command to fix critical data quality issues.

See docs/DATA_CLEANUP_GUIDE.md for complete documentation.

Usage:
    python manage.py clean_data --dry-run
    python manage.py clean_data --fix=<fix_type>
    python manage.py clean_data --fix=all  # Runs all fixes in correct order

When --fix=all is used, fixes run in this order:

  PHASE 0: General data quality
    - orphaned_donations, duplicate_donations, invalid_dates

  PHASE 1: Split concatenated entries (MUST happen first)
    - semicolon_actors, split_concatenated_attendees, split_concatenated_orgs
    - split_consultancy_clients, parse_event_descriptions, split_camelcase

  PHASE 2: Fix entity types (after splitting)
    - convert_titled_persons, roundtable_actors

  PHASE 3: Clean up names (after type fixes)
    - normalize_actor_names, merge_split_names

  PHASE 4: Deduplicate (after cleaning)
    - merge_duplicate_types

  PHASE 5: Categorize (after main cleanup)
    - flag_non_ch_orgs

NOT in --fix=all (run explicitly with caution):
    - zero_value: Deletes zero-value donations
    - cleanup_concatenated_orgs: Deletes without migrating relationships

After running clean_data, run entity resolution:
    python manage.py populate_canonical --dataset all

Uses shared utilities from datafetch/utils/data_cleanup.py
"""

import re
import datetime
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import Count, Q
from django.db.models.functions import Length
from datafetch.models import Person, Organization, Donation, Membership, MeetingAttendee, Actor, CompaniesHouseMatch, Consultancy, Identifier, Note, ContactDetail, Link, MinisterialMeeting
from django.contrib.contenttypes.models import ContentType

# Import shared utilities - SINGLE SOURCE OF TRUTH for patterns
from datafetch.utils.data_cleanup import (
    OrganizationPatterns,
    ActorClassifier,
    NameSplitter,
    EventDescriptionParser,
    NameNormalizer,
    CamelCaseSplitter,
)


class Command(BaseCommand):
    help = 'Clean critical data quality issues'

    # Use shared patterns from data_cleanup.py
    ORG_TYPE_PATTERNS = OrganizationPatterns.ORG_TYPE_PATTERNS

    # Constants for split_concatenated_orgs - use NameSplitter patterns
    CONCAT_PATTERN = NameSplitter.CONCAT_PATTERN
    EXCLUDE_PATTERNS = NameSplitter.EXCLUDE_PATTERNS
    TRADING_AS_PATTERN = re.compile(r'\s+[Tt]/?[Aa][Ss]?\s+', re.IGNORECASE)

    # Constants for split_consultancy_clients
    ORG_ENDINGS = {
        'authority', 'society', 'group', 'association', 'foundation',
        'council', 'institute', 'institution', 'commission', 'committee',
        'trust', 'charity', 'fund', 'network', 'alliance', 'coalition',
        'partnership', 'federation', 'union', 'board', 'agency',
        'corporation', 'company', 'limited', 'ltd', 'plc', 'llp', 'inc',
        'taskforce', 'regulator', 'ombudsman', 'exchange',
    }
    TWO_WORD_ENDINGS = {
        'building society', 'pension scheme', 'pension fund',
        'county council', 'city council', 'borough council',
        'district council', 'parish council', 'town council',
    }
    KNOWN_COMPANIES = {
        'british steel', 'tata steel', 'british gas', 'british airways',
        'rolls royce', 'land rover', 'aston martin', 'marks spencer',
        'john lewis', 'lloyds banking', 'hsbc uk', 'barclays bank',
        'royal mail', 'bt group', 'vodafone group', 'virgin media',
        'sky uk', 'itv plc', 'channel four',
        'national grid', 'scottish power', 'sse plc', 'centrica plc',
        'thames water', 'united utilities', 'severn trent', 'anglian water',
        'network rail', 'hs2 ltd', 'crossrail', 'transport london',
        'heathrow airport', 'gatwick airport', 'manchester airport',
        'goldman sachs', 'morgan stanley', 'jp morgan', 'deutsche bank',
        'credit suisse', 'ubs ag', 'bank america', 'wells fargo',
        'coca cola', 'pepsi co', 'procter gamble', 'johnson johnson',
        'general electric', 'general motors', 'ford motor',
        'dow chemical', 'dow europe', 'dupont de', 'basf se', 'bayer ag',
        'glaxosmithkline', 'astrazeneca', 'pfizer inc', 'novartis ag',
        'bristol myers', 'eli lilly', 'merck co', 'abbvie inc',
        'amazon uk', 'google uk', 'microsoft uk', 'apple uk', 'meta uk',
        'facebook uk', 'twitter uk', 'linkedin uk', 'uber uk', 'deliveroo',
        'live nation', 'oxford nanopore', 'teneo financial',
        'serendipity capital', 'spa medica', 'the aa', 'the dow',
        'universities superannuation', 'horseracing authority',
        'british horseracing', 'building society',
    }
    CONTINUATION_WORDS = {
        'of', 'the', 'and', '&', 'for', 'in', 'on', 'at', 'to', 'by',
        'great', 'greater', 'british', 'english', 'scottish', 'welsh', 'irish',
        'royal', 'national', 'international', 'global', 'world', 'european',
        'north', 'south', 'east', 'west', 'central', 'united',
        'new', 'old', 'big', 'small', 'first', 'second',
    }
    SUFFIX_WORDS = {
        'uk', 'europe', 'international', 'global', 'worldwide',
        'limited', 'ltd', 'plc', 'llp', 'inc',
        # UK nations/regions
        'wales', 'cymru', 'scotland', 'england', 'ireland', 'ni',
    }

    # Placeholder client names from APPC import that should be cleaned
    # These are boilerplate text entries, not real organizations
    PLACEHOLDER_CLIENT_NAMES = [
        '(i) Client description available',
        'Pro-Bono Clients for whom consultancy and/or monitoring services have been provided this quarter',
        'N/A',
    ]

    # All available fix types (listed in execution order for --fix=all)
    FIX_TYPES = [
        # Phase 0: General data quality
        'orphaned_donations', 'duplicate_donations', 'invalid_dates', 'zero_value',
        'placeholder_clients',
        # Phase 1: Split concatenated entries
        'semicolon_actors', 'split_concatenated_attendees', 'split_concatenated_orgs',
        'split_consultancy_clients', 'parse_event_descriptions',
        # 'split_camelcase',  # DISABLED - can't distinguish brands from concatenation
        # Phase 2: Fix entity types
        'convert_titled_persons', 'roundtable_actors',
        # Phase 3: Clean up names
        'normalize_actor_names', 'merge_split_names', 'cleanup_concatenated_orgs',
        # Phase 4: Deduplicate
        'merge_duplicate_types',
        # Phase 5: Categorize
        'flag_non_ch_orgs',
        # Run all in order
        'all',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            type=str,
            help=f'What to fix: {", ".join(self.FIX_TYPES)}',
            default='all',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of records to process (for split commands)',
        )
        parser.add_argument(
            '--min-length',
            type=int,
            default=150,
            help='Minimum name length to consider concatenated (for cleanup_concatenated_orgs)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def _get_stats(self):
        """Get current database statistics for before/after comparison."""
        return {
            'persons': Person.objects.count(),
            'organizations': Organization.objects.count(),
            'actors': Actor.objects.count(),
            'donations': Donation.objects.count(),
            'consultancies': Consultancy.objects.count(),
            'meeting_attendees': MeetingAttendee.objects.count(),
            'ch_matches': CompaniesHouseMatch.objects.count(),
        }

    def _print_stats(self, stats, label):
        """Print statistics with a label."""
        self.stdout.write(f'\n{label}:')
        self.stdout.write(f'  Persons:            {stats["persons"]:,}')
        self.stdout.write(f'  Organizations:      {stats["organizations"]:,}')
        self.stdout.write(f'  Actors (total):     {stats["actors"]:,}')
        self.stdout.write(f'  Donations:          {stats["donations"]:,}')
        self.stdout.write(f'  Consultancies:      {stats["consultancies"]:,}')
        self.stdout.write(f'  Meeting Attendees:  {stats["meeting_attendees"]:,}')
        self.stdout.write(f'  CH Matches:         {stats["ch_matches"]:,}')

    def _print_diff(self, before, after, dry_run=False):
        """Print the difference between before and after stats, plus projected changes."""
        self.stdout.write('\nChanges:')

        # Print actual database changes (live run only)
        has_actual_changes = False
        for key in before:
            diff = after[key] - before[key]
            if diff != 0:
                has_actual_changes = True
                sign = '+' if diff > 0 else ''
                label = key.replace('_', ' ').title()
                self.stdout.write(f'  {label}: {sign}{diff:,}')

        # Print projected changes from fix totals (collected during run)
        if self._fix_totals:
            if dry_run:
                self.stdout.write('\n  Projected changes (dry run):')
            else:
                self.stdout.write('\n  Details by fix type:')

            for fix_name, data in self._fix_totals.items():
                count = data.get('count', 0)
                totals = data.get('totals', {})
                if count > 0:
                    prefix = "Would" if dry_run else "Did"
                    self.stdout.write(f'\n  {fix_name} ({prefix} process {count}):')

                    # Calculate and display net changes
                    persons_net = totals.get('persons_created', 0) - totals.get('persons_deleted', 0)
                    orgs_net = totals.get('organizations_created', 0) - totals.get('organizations_deleted', 0)
                    attendances_net = totals.get('attendances_created', 0) - totals.get('attendances_deleted', 0)
                    ch_matches_net = -totals.get('ch_matches_deleted', 0)

                    if persons_net != 0:
                        sign = '+' if persons_net > 0 else ''
                        self.stdout.write(f'    Persons: {sign}{persons_net:,}')
                    if orgs_net != 0:
                        sign = '+' if orgs_net > 0 else ''
                        self.stdout.write(f'    Organizations: {sign}{orgs_net:,}')
                    if attendances_net != 0:
                        sign = '+' if attendances_net > 0 else ''
                        self.stdout.write(f'    Meeting Attendees: {sign}{attendances_net:,}')
                    if ch_matches_net != 0:
                        self.stdout.write(f'    CH Matches: {ch_matches_net:,}')

                    # Show meetings updated if any
                    meetings_updated = totals.get('meetings_updated', 0)
                    if meetings_updated > 0:
                        self.stdout.write(f'    Meetings updated: {meetings_updated:,}')

                    # Fallback for other fix types with different totals structure
                    shown_keys = {'persons_created', 'persons_deleted', 'organizations_created',
                                  'organizations_deleted', 'attendances_created', 'attendances_deleted',
                                  'ch_matches_deleted', 'meetings_updated'}
                    for key, value in totals.items():
                        if key not in shown_keys:
                            # Handle both int values and dict breakdowns
                            if isinstance(value, dict):
                                self.stdout.write(f'    {key.replace("_", " ").title()}:')
                                for subkey, subvalue in value.items():
                                    if subvalue > 0:
                                        self.stdout.write(f'      - {subkey}: {subvalue:,}')
                            elif isinstance(value, (int, float)) and value > 0:
                                label = key.replace('_', ' ')
                                self.stdout.write(f'    - {label}: {value:,}')
        elif not has_actual_changes:
            self.stdout.write('  (none)')

    def handle(self, *args, **options):
        fix_type = options['fix']
        dry_run = options['dry_run']
        limit = options['limit']
        min_length = options['min_length']
        verbose = options['verbose']

        # Initialize storage for fix totals (reported in Changes section)
        self._fix_totals = {}

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Data Cleaning Report'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get before stats
        before_stats = self._get_stats()
        self._print_stats(before_stats, 'BEFORE')
        self.stdout.write('')

        total_fixed = 0

        # =================================================================
        # PHASE 0: General data quality fixes (independent, run first)
        # =================================================================
        if fix_type in ('all', 'orphaned_donations'):
            total_fixed += self.fix_orphaned_donations(dry_run)

        if fix_type in ('all', 'duplicate_donations'):
            total_fixed += self.fix_duplicate_donations(dry_run)

        if fix_type in ('all', 'invalid_dates'):
            total_fixed += self.fix_invalid_membership_dates(dry_run)

        if fix_type in ('all', 'placeholder_clients'):
            total_fixed += self.fix_placeholder_clients(dry_run)

        # NOTE: zero_value NOT in 'all' - run explicitly if needed
        if fix_type == 'zero_value':
            total_fixed += self.fix_zero_value_donations(dry_run)

        # =================================================================
        # PHASE 1: Split concatenated entries (MUST happen first)
        # These break apart "Org A; Org B" into separate actors
        # =================================================================
        if fix_type in ('all', 'semicolon_actors'):
            total_fixed += self.fix_semicolon_actors(dry_run)

        if fix_type in ('all', 'split_concatenated_attendees'):
            total_fixed += self.fix_split_concatenated_attendees(dry_run, limit)

        if fix_type in ('all', 'split_concatenated_orgs'):
            total_fixed += self.fix_split_concatenated_orgs(dry_run, limit, verbose)

        if fix_type in ('all', 'split_consultancy_clients'):
            total_fixed += self.fix_split_consultancy_clients(dry_run, limit, 100, verbose)

        if fix_type in ('all', 'parse_event_descriptions'):
            total_fixed += self.fix_parse_event_descriptions(dry_run, limit)

        # split_camelcase is DISABLED - only runs if explicitly requested
        if fix_type == 'split_camelcase':
            total_fixed += self.fix_split_camelcase(dry_run, limit)

        # =================================================================
        # PHASE 2: Fix entity types (after splitting)
        # Now that entries are split, fix misclassified types
        # =================================================================
        if fix_type in ('all', 'convert_titled_persons'):
            total_fixed += self.fix_convert_titled_persons(dry_run)

        if fix_type in ('all', 'roundtable_actors'):
            total_fixed += self.fix_roundtable_actors(dry_run)

        # =================================================================
        # PHASE 3: Clean up names (after type fixes)
        # Fix name quality issues
        # =================================================================
        if fix_type in ('all', 'normalize_actor_names'):
            total_fixed += self.fix_normalize_actor_names(dry_run, limit)

        if fix_type in ('all', 'merge_split_names'):
            total_fixed += self.fix_merge_split_names(dry_run)

        # NOTE: cleanup_concatenated_orgs NOT in 'all' - DANGEROUS, deletes without migrating
        if fix_type == 'cleanup_concatenated_orgs':
            self.stdout.write(self.style.WARNING('\n⚠️  WARNING: This deletes records without migrating relationships!'))
            total_fixed += self.fix_cleanup_concatenated_orgs(dry_run, min_length)

        # =================================================================
        # PHASE 4: Deduplicate (after cleaning)
        # Merge duplicate records
        # =================================================================
        if fix_type in ('all', 'merge_duplicate_types'):
            total_fixed += self.fix_merge_duplicate_types(dry_run)

        # =================================================================
        # PHASE 5: Categorize (after main cleanup)
        # Flag/categorize records for downstream processing
        # =================================================================
        if fix_type in ('all', 'flag_non_ch_orgs'):
            total_fixed += self.fix_flag_non_ch_orgs(dry_run)

        # Get after stats and show comparison
        after_stats = self._get_stats()
        self._print_stats(after_stats, 'AFTER')
        self._print_diff(before_stats, after_stats, dry_run)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would fix/process {total_fixed} issues (DRY RUN)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Fixed/Processed {total_fixed} issues'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

    # --- General Fixes ---

    def fix_orphaned_donations(self, dry_run):
        """Delete orphaned donations (null donor and zero value)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Orphaned Donations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        orphaned = Donation.objects.filter(
            donor__isnull=True,
            value=0,
            received_date__isnull=True
        )

        count = orphaned.count()
        self.stdout.write(f'Found {count} orphaned donations (null donor, zero value, no date)')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned donations to fix'))
            return 0

        # Always show what we're doing (dry-run or live)
        prefix = "Would delete" if dry_run else "Deleting"
        for d in orphaned[:5]:
            self.stdout.write(f'  {prefix}: Donation #{d.pk} (donor=None, value=0)')
        if count > 5:
            self.stdout.write(f'  ... and {count - 5} more')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would delete {count} orphaned donations'))
        else:
            with transaction.atomic():
                orphaned.delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} orphaned donations'))

        return count

    def fix_duplicate_donations(self, dry_run):
        """Remove duplicate donations, keeping the oldest ID."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Duplicate Donations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        duplicates = (
            Donation.objects
            .values('donor', 'recipient', 'value', 'received_date')
            .annotate(count=Count('id'), min_id=models.Min('id'))
            .filter(count__gt=1)
        )

        total_dupes = duplicates.count()
        self.stdout.write(f'Found {total_dupes} duplicate donation groups')

        if total_dupes == 0:
            self.stdout.write(self.style.SUCCESS('✓ No duplicate donations to fix'))
            return 0

        total_deleted = 0

        if not dry_run:
            with transaction.atomic():
                for dup in duplicates:
                    dupes = Donation.objects.filter(
                        donor_id=dup['donor'],
                        recipient_id=dup['recipient'],
                        value=dup['value'],
                        received_date=dup['received_date']
                    ).exclude(id=dup['min_id'])

                    deleted = dupes.count()
                    total_deleted += deleted
                    dupes.delete()

            self.stdout.write(self.style.SUCCESS(
                f'✓ Deleted {total_deleted} duplicate donations (kept {total_dupes} originals)'
            ))
        else:
            for i, dup in enumerate(duplicates):
                if i < 5:
                    self.stdout.write(f'  Would dedup: donor={dup["donor"]}, value={dup["value"]}, count={dup["count"]} (keep 1)')
                total_deleted += dup['count'] - 1
            if total_dupes > 5:
                self.stdout.write(f'  ... and {total_dupes - 5} more duplicate groups')
            self.stdout.write(self.style.WARNING(
                f'Would delete {total_deleted} duplicate donations (keep {total_dupes} originals)'
            ))

        return total_deleted

    def fix_invalid_membership_dates(self, dry_run):
        """Fix memberships where end_date < start_date by swapping them."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Invalid Membership Dates'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        invalid = []
        for membership in Membership.objects.exclude(
            models.Q(start_date__isnull=True) | models.Q(start_date='') |
            models.Q(end_date__isnull=True) | models.Q(end_date='')
        ):
            try:
                start = datetime.datetime.strptime(membership.start_date, '%Y-%m-%d').date()
                end = datetime.datetime.strptime(membership.end_date, '%Y-%m-%d').date()
                if end < start:
                    invalid.append(membership)
            except ValueError:
                pass

        count = len(invalid)
        self.stdout.write(f'Found {count} memberships with end_date < start_date')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No invalid membership dates to fix'))
            return 0

        if not dry_run:
            with transaction.atomic():
                for m in invalid:
                    old_start = m.start_date
                    old_end = m.end_date
                    m.start_date = old_end
                    m.end_date = old_start
                    m.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Fixed {count} invalid membership dates'))
        else:
            self.stdout.write(self.style.WARNING(f'Would fix {count} invalid membership dates'))

        return count

    def fix_zero_value_donations(self, dry_run):
        """Delete zero-value donations with no dates."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Zero Value Donations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        zero_value = Donation.objects.filter(
            value=0,
            received_date__isnull=True,
            accepted_date__isnull=True
        )

        count = zero_value.count()
        self.stdout.write(f'Found {count} zero-value donations with no dates')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No zero-value donations to fix'))
            return 0

        if not dry_run:
            with transaction.atomic():
                zero_value.delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} zero-value donations'))
        else:
            self.stdout.write(self.style.WARNING(f'Would delete {count} zero-value donations'))

        return count

    def fix_placeholder_clients(self, dry_run):
        """Remove placeholder client records from APPC lobbying data.

        These are boilerplate text entries like "(i) Client description available"
        that got imported as actual Organization records. The fix:
        1. Sets client_id = NULL on affected Consultancy records
        2. Deletes the placeholder Actor records (they have no other relationships)
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Placeholder Clients'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Find placeholder actors
        placeholder_actors = []
        for name in self.PLACEHOLDER_CLIENT_NAMES:
            actors = Actor.objects.filter(name=name)
            for actor in actors:
                consultancy_count = Consultancy.objects.filter(client=actor).count()
                if consultancy_count > 0:
                    placeholder_actors.append((actor, consultancy_count))

        if not placeholder_actors:
            self.stdout.write(self.style.SUCCESS('✓ No placeholder clients to fix'))
            return 0

        total_consultancies = sum(count for _, count in placeholder_actors)
        self.stdout.write(f'Found {len(placeholder_actors)} placeholder actors affecting {total_consultancies} consultancies')

        for actor, count in placeholder_actors:
            prefix = "Would clean" if dry_run else "Cleaning"
            self.stdout.write(f'  {prefix}: "{actor.name[:60]}" ({count} consultancies)')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'Would update {total_consultancies} consultancies (set client=NULL) '
                f'and delete {len(placeholder_actors)} placeholder actors'
            ))
        else:
            with transaction.atomic():
                for actor, _ in placeholder_actors:
                    # Set client to NULL on consultancies
                    Consultancy.objects.filter(client=actor).update(client=None)
                    # Delete the placeholder actor
                    actor.delete()

            self.stdout.write(self.style.SUCCESS(
                f'✓ Updated {total_consultancies} consultancies and deleted {len(placeholder_actors)} placeholder actors'
            ))

        return total_consultancies

    def fix_semicolon_actors(self, dry_run):
        """Split actors with semicolons in their name into separate actors."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Semicolon (Concatenated) Actors'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        bad_actors = list(Actor.objects.filter(name__contains=';'))
        count = len(bad_actors)
        self.stdout.write(f'Found {count} actors with semicolons in name')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No semicolon actors to fix'))
            return 0

        split_count = 0
        totals = {
            'actors_deleted': 0,
            'actors_created': 0,
            'attendances_deleted': 0,
            'attendances_created': 0,
            'donations_updated': 0,
            'consultancies_cloned': 0,
        }
        actor_ct = ContentType.objects.get_for_model(Actor)

        for actor in bad_actors:
            # Split name by semicolon
            parts = [p.strip() for p in actor.name.split(';') if p.strip()]

            if len(parts) <= 1:
                continue  # Nothing to split

            # Skip if any part is too long for actor_name_raw field (512 chars)
            max_part_len = max(len(p) for p in parts)
            if max_part_len > 512:
                self.stdout.write(f'  Skipping (part too long: {max_part_len} chars): "{actor.name[:60]}..."')
                continue

            # Count relationships
            attendances_count = MeetingAttendee.objects.filter(actor=actor).count()
            donations_donor_count = Donation.objects.filter(donor=actor).count()
            donations_recipient_count = Donation.objects.filter(recipient=actor).count()
            consultancies_count = Consultancy.objects.filter(client=actor).count()

            # Count new actors that will be created
            new_actor_count = 0
            for part_name in parts:
                actor_type = ActorClassifier.classify(part_name)
                if actor_type == 'organization':
                    if not Organization.objects.filter(name=part_name).exists():
                        new_actor_count += 1
                else:
                    if not Person.objects.filter(name=part_name).exists():
                        new_actor_count += 1

            # Always show what we're doing (dry-run or live)
            prefix = "Would split" if dry_run else "Splitting"
            self.stdout.write(f'  {prefix}: "{actor.name}" -> {parts}')

            if dry_run:
                split_count += 1
                totals['actors_deleted'] += 1
                totals['actors_created'] += new_actor_count
                totals['attendances_deleted'] += attendances_count
                totals['attendances_created'] += attendances_count * len(parts)
                totals['donations_updated'] += donations_donor_count + donations_recipient_count
                totals['consultancies_cloned'] += consultancies_count * len(parts)
                continue

            with transaction.atomic():
                # Get relationships to clone
                attendances = list(MeetingAttendee.objects.filter(actor=actor))
                donations_as_donor = list(Donation.objects.filter(donor=actor))
                donations_as_recipient = list(Donation.objects.filter(recipient=actor))
                consultancies_as_client = list(Consultancy.objects.filter(client=actor))

                # Create new actors for each part
                new_actors = []
                for part_name in parts:
                    actor_type = ActorClassifier.classify(part_name)
                    if actor_type == 'organization':
                        new_actor = Organization.objects.filter(name=part_name).first()
                        if not new_actor:
                            new_actor = Organization.objects.create(name=part_name, classification='Organization')
                    else:
                        new_actor = Person.objects.filter(name=part_name).first()
                        if not new_actor:
                            new_actor = Person.objects.create(name=part_name)
                    new_actors.append(new_actor)

                # Clone MeetingAttendee relationships
                # Unique constraint is on (meeting, actor_name_raw), not (meeting, actor)
                for attendance in attendances:
                    for new_actor in new_actors:
                        MeetingAttendee.objects.get_or_create(
                            meeting=attendance.meeting,
                            actor_name_raw=new_actor.name,
                            defaults={'actor': new_actor}
                        )

                # Clone Donation relationships (donor)
                for donation in donations_as_donor:
                    for new_actor in new_actors:
                        # Update first actor as donor, skip others (can't have multiple donors)
                        if new_actor == new_actors[0]:
                            donation.donor = new_actor
                            donation.save(update_fields=['donor'])
                        break

                # Clone Donation relationships (recipient)
                for donation in donations_as_recipient:
                    for new_actor in new_actors:
                        if new_actor == new_actors[0]:
                            donation.recipient = new_actor
                            donation.save(update_fields=['recipient'])
                        break

                # Clone Consultancy relationships
                for consultancy in consultancies_as_client:
                    for new_actor in new_actors:
                        Consultancy.objects.get_or_create(
                            client=new_actor,
                            agency=consultancy.agency,
                            defaults={
                                'label': consultancy.label,
                                'source': consultancy.source,
                            }
                        )

                # Add note before deleting
                Note.objects.create(
                    content_type=actor_ct,
                    object_id=actor.pk,
                    content=f'[CLEANUP:semicolon_actors] Split into {len(parts)} actors: {parts}'
                )

                # Delete original relationships and actor
                MeetingAttendee.objects.filter(actor=actor).delete()
                actor.delete()
                split_count += 1

        # Store totals for reporting in Changes section
        self._fix_totals['semicolon_actors'] = {
            'count': split_count,
            'totals': totals,
        }

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would split {split_count} semicolon actors'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Split {split_count} semicolon actors'))

        return split_count

    def fix_roundtable_actors(self, dry_run):
        """Handle actors starting with 'Roundtable'.

        NOTE: This is now handled by parse_event_descriptions which properly
        extracts attendees. This fix just reports remaining cases.
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Roundtable Actors (handled by parse_event_descriptions)'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        bad_actors = Actor.objects.filter(name__istartswith='Roundtable')
        count = bad_actors.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No roundtable actors remaining'))
        else:
            self.stdout.write(f'Found {count} actors starting with "Roundtable"')
            self.stdout.write('  (Run --fix=parse_event_descriptions to handle these)')

        return 0  # Don't delete - let parse_event_descriptions handle

    # --- Specialized Fixes ---

    def _detect_concatenation_pattern(self, name):
        """
        Detect the concatenation pattern type in a name.

        Returns: (pattern_type, suggested_cleaner)
            pattern_type: 'semicolon', 'camelcase', 'corporate_suffix', 'comma_list', 'unknown'
            suggested_cleaner: 'semicolon_actors', 'split_camelcase', 'split_org_name', 'split_attendee_list', None
        """
        if not name:
            return ('empty', None)

        # 1. Semicolon-delimited (highest priority - already formatted for splitting)
        if ';' in name:
            return ('semicolon', 'semicolon_actors')

        # 2. Corporate suffix followed by capital letter (e.g., "Company Ltd Another Company")
        # Pattern: Ltd/Limited/PLC followed by space and capital letter
        if re.search(r'\b(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z]', name, re.IGNORECASE):
            return ('corporate_suffix', 'split_consultancy_clients')

        # 3. CamelCase smashing (e.g., "SocietyHaemophilia")
        # Count lowercase→uppercase transitions
        transitions = len(re.findall(r'[a-z][A-Z]', name))
        if transitions >= 2:
            # Check it's not just normal capitalization (e.g., "McDonald's")
            # by looking for patterns that suggest concatenation
            if CamelCaseSplitter.should_split(name):
                return ('camelcase', 'split_camelcase')

        # 4. Closing parenthesis followed immediately by capital letter
        # E.g., "David Dingle (Maritime UK)Guy Platten (UK Chamber)"
        if re.search(r'\)[A-Z]', name):
            return ('paren_camelcase', 'split_camelcase')

        # 5. Multi-comma list (3+ commas suggests a list)
        if name.count(',') >= 3:
            return ('comma_list', 'split_concatenated_attendees')

        # 6. Long whitespace runs (tabular data) - should have been converted to semicolons
        if re.search(r'\s{6,}', name):
            return ('tabular', 'normalize_actor_names')

        # 7. Double spaces (2-5 spaces) as separator - these are likely tabular too
        # E.g., "Company A  Person B  Company C"
        if re.search(r'\s{2,5}', name) and name.count('  ') >= 2:
            return ('double_space', 'normalize_actor_names')

        # 8. Contains " and " between what look like separate entities
        # E.g., "Company A Ltd and Company B Ltd"
        if re.search(r'\b(Ltd|Limited|PLC)\b.+\band\b.+\b(Ltd|Limited|PLC)\b', name, re.IGNORECASE):
            return ('and_connector', 'split_concatenated_attendees')

        # 9. Slash-separated list (multiple /)
        if name.count('/') >= 2:
            return ('slash_list', 'split_concatenated_attendees')

        # 10. Colon followed by list pattern
        # E.g., "Animals in Science Regulated Sector :Office for Life Sciences"
        if re.search(r':\s*[A-Z]', name):
            return ('colon_list', 'split_concatenated_attendees')

        # 11. Closing paren + space + capital (variant of #4)
        # E.g., "Water Services Regulation Authority (Ofwat) Welcome Break Group"
        if re.search(r'\)\s+[A-Z]', name):
            return ('paren_space_cap', 'split_concatenated_attendees')

        # 12. Period separator
        # E.g., "Wealden. County- Hampshire-"
        if re.search(r'\.\s+[A-Z]', name):
            return ('period_sep', 'split_concatenated_attendees')

        # 13. Dash separator (dash + space + capital letter starting a word)
        # E.g., "County- Hampshire- Councils-"
        if re.search(r'-\s+[A-Z][a-z]', name):
            return ('dash_sep', 'split_concatenated_attendees')

        # 14. Multiple org markers without clear delimiter
        # Detects names with 2+ org keywords (Group, Trust, Foundation, UK, England, Authority)
        # These likely have multiple orgs but no programmatic way to split
        org_markers = ['Group', 'Trust', 'Foundation', 'UK', 'England', 'Authority', 'Association', 'Council']
        marker_count = sum(1 for m in org_markers if re.search(rf'\b{m}\b', name, re.IGNORECASE))
        if marker_count >= 2:
            return ('multi_org_marker', 'manual_review')

        # Unknown pattern - needs manual review
        return ('unknown', None)

    def fix_cleanup_concatenated_orgs(self, dry_run, min_length):
        """
        Cleanup concatenated orgs by routing to appropriate splitters.

        Instead of deleting, this function:
        1. Detects the concatenation pattern type
        2. Routes to the appropriate cleaner
        3. Only flags truly unparseable entries for manual review
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Cleanup Concatenated Organizations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        long_orgs = Organization.objects.annotate(name_len=Length('name')).filter(name_len__gt=min_length)
        total = long_orgs.count()
        self.stdout.write(f'Found {total} organizations with names > {min_length} chars')

        if total == 0:
            return 0

        # Categorize by pattern type
        by_pattern = {
            'semicolon': [],
            'corporate_suffix': [],
            'camelcase': [],
            'paren_camelcase': [],
            'comma_list': [],
            'tabular': [],
            'double_space': [],
            'and_connector': [],
            'slash_list': [],
            'colon_list': [],
            'unknown': [],
        }

        for org in long_orgs:
            pattern_type, cleaner = self._detect_concatenation_pattern(org.name)
            if pattern_type not in by_pattern:
                by_pattern[pattern_type] = []
            by_pattern[pattern_type].append((org, cleaner))

        # Report findings
        self.stdout.write('')
        self.stdout.write('Pattern analysis:')
        for pattern_type, items in by_pattern.items():
            if items:
                self.stdout.write(f'  {pattern_type}: {len(items)} orgs')

        # Show examples and routing
        self.stdout.write('')
        processed = 0

        for pattern_type, items in by_pattern.items():
            if not items:
                continue

            self.stdout.write(f'\n{pattern_type.upper()} ({len(items)} orgs):')

            for org, cleaner in items[:10]:  # Show first 10 examples
                attendees = MeetingAttendee.objects.filter(actor=org).count()
                consult = Consultancy.objects.filter(Q(client=org) | Q(agency=org)).count()

                # Truncate name for display
                display_name = org.name[:100] + '...' if len(org.name) > 100 else org.name

                if cleaner:
                    action = f"Route to: {cleaner}"
                else:
                    action = "SKIP (needs manual review)"

                self.stdout.write(f'  "{display_name}"')
                self.stdout.write(f'    -> {action}')
                if attendees or consult:
                    self.stdout.write(f'    -> Links: {attendees} attendees, {consult} consultancies')

            if len(items) > 10:
                self.stdout.write(f'  ... and {len(items) - 10} more')

        # For patterns that can be auto-processed, convert to semicolon format
        # This allows them to be picked up by semicolon_actors fix
        # Patterns that can be auto-converted to semicolon format
        auto_convert_patterns = [
            'camelcase', 'paren_camelcase', 'corporate_suffix', 'and_connector',
            'double_space', 'slash_list', 'colon_list'
        ]
        auto_convert = []
        for pattern_type in auto_convert_patterns:
            if pattern_type in by_pattern:
                auto_convert.extend(by_pattern[pattern_type])

        if auto_convert:
            self.stdout.write('')
            self.stdout.write(f'Auto-converting {len(auto_convert)} orgs to semicolon-delimited format...')

            converted = 0
            for org, _ in auto_convert:
                # Try to split the name
                parts = []
                pattern_type, _ = self._detect_concatenation_pattern(org.name)

                if pattern_type in ('camelcase', 'paren_camelcase'):
                    # For paren_camelcase, first split on )[A-Z] pattern
                    if pattern_type == 'paren_camelcase':
                        parts = re.split(r'\)(?=[A-Z])', org.name)
                        # Re-add closing parens to all but last
                        parts = [p + ')' if i < len(parts) - 1 else p
                                 for i, p in enumerate(parts)]
                        parts = [p.strip() for p in parts if p.strip()]
                    else:
                        parts = CamelCaseSplitter.split(org.name)
                elif pattern_type == 'corporate_suffix':
                    parts = NameSplitter.split_org_name(org.name)
                elif pattern_type in ('and_connector', 'slash_list'):
                    parts = NameSplitter.split_attendee_list(org.name)
                elif pattern_type == 'double_space':
                    # Convert double spaces to semicolons
                    normalized = re.sub(r'\s{2,}', '; ', org.name)
                    parts = [p.strip() for p in normalized.split(';') if p.strip()]
                elif pattern_type == 'colon_list':
                    # Split on colon
                    parts = [p.strip() for p in org.name.split(':') if p.strip()]

                if len(parts) > 1:
                    new_name = '; '.join(parts)
                    prefix = "Would convert" if dry_run else "Converting"
                    self.stdout.write(f'  {prefix}: "{org.name[:60]}..." -> "{new_name[:60]}..."')

                    if not dry_run:
                        org.name = new_name
                        org.save(update_fields=['name'])

                    converted += 1

            if dry_run:
                self.stdout.write(self.style.WARNING(f'Would convert {converted} orgs to semicolon format'))
                self.stdout.write(self.style.WARNING(f'Then run: python manage.py clean_data semicolon_actors'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Converted {converted} orgs to semicolon format'))
                self.stdout.write(self.style.SUCCESS(f'Now run: python manage.py clean_data semicolon_actors'))

            processed = converted

        # Report unknown patterns for manual review
        unknown = by_pattern['unknown']
        if unknown:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'{len(unknown)} orgs need manual review (unknown pattern):'))
            for org, _ in unknown[:5]:
                self.stdout.write(f'  - {org.name[:80]}...')
            if len(unknown) > 5:
                self.stdout.write(f'  ... and {len(unknown) - 5} more')

        # Store totals for summary reporting
        self._fix_totals['cleanup_concatenated_orgs'] = {
            'count': total,
            'totals': {
                'renamed': processed,  # These are renamed, not deleted
                'manual_review': len(unknown),
                'pattern_breakdown': {k: len(v) for k, v in by_pattern.items() if v},
            }
        }

        return processed

    def fix_flag_non_ch_orgs(self, dry_run):
        """Flag Non-CH Organizations (flag_non_ch_orgs.py logic)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Flag Non-CH Organizations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        not_found = CompaniesHouseMatch.objects.filter(status='not_found').select_related('organization__actor_ptr')
        total = not_found.count()
        self.stdout.write(f'Found {total} organizations with status=not_found')

        updates = []
        by_reason = {}

        for match in not_found:
            org_name = match.organization.name.lower()
            matched_reason = None
            for reason, patterns in self.ORG_TYPE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, org_name, re.IGNORECASE):
                        matched_reason = reason
                        break
                if matched_reason: break

            if matched_reason:
                updates.append((match, matched_reason))
                if matched_reason not in by_reason:
                    by_reason[matched_reason] = []
                by_reason[matched_reason].append(match.organization.name)

        count = len(updates)
        self.stdout.write(f'Found {count} records to flag as not_applicable')

        # Show breakdown by reason
        self.stdout.write('')
        self.stdout.write('Breakdown by reason:')
        for reason, names in sorted(by_reason.items(), key=lambda x: -len(x[1])):
            self.stdout.write(f'  {reason}: {len(names)}')
            # Show a few examples
            for name in names[:3]:
                self.stdout.write(f'    - {name[:70]}{"..." if len(name) > 70 else ""}')
            if len(names) > 3:
                self.stdout.write(f'    ... and {len(names) - 3} more')

        prefix = "Would flag" if dry_run else "Flagging"
        self.stdout.write('')

        if not dry_run:
            with transaction.atomic():
                for match, reason in updates:
                    match.status = 'not_applicable'
                    match.not_applicable_reason = reason
                    match.save(update_fields=['status', 'not_applicable_reason'])
            self.stdout.write(self.style.SUCCESS(f'✓ Updated {count} records'))
        else:
            self.stdout.write(self.style.WARNING(f'Would update {count} records'))

        return count

    def fix_split_concatenated_attendees(self, dry_run, limit):
        """Split concatenated attendees (split_concatenated_attendees.py logic)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Split Concatenated Attendees'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        messy_actors = Actor.objects.filter(
            Q(name__contains=';') | Q(name__contains=': ')
        ).distinct()

        if limit: messy_actors = messy_actors[:limit]

        total = messy_actors.count()
        self.stdout.write(f'Found {total} potentially messy actors')

        split_count = 0
        totals = {
            'actors_deleted': 0,
            'actors_created': 0,
            'meetings_relinked': 0,
        }

        for actor in messy_actors:
            result = self._process_messy_actor(actor, dry_run)
            if result:
                split_count += 1
                if isinstance(result, dict):
                    for key in totals:
                        totals[key] += result.get(key, 0)

        # Store totals for reporting in Changes section
        self._fix_totals['split_concatenated_attendees'] = {
            'count': split_count,
            'totals': totals,
        }

        return split_count

    def _process_messy_actor(self, actor, dry_run):
        name = actor.name

        # Skip if this looks like an event description - let parse_event_descriptions handle it
        if EventDescriptionParser.is_event_description(name):
            return False

        # Skip sentence fragments (contain sentence-like words)
        sentence_indicators = [
            'received from', 'available at', 'details available', 'secretariat from',
            'funded by', 'supported by', 'see all member', 'full details',
            'more information', 'for more', 'click here', 'visit our',
        ]
        name_lower = name.lower()
        if any(ind in name_lower for ind in sentence_indicators):
            return False

        # Skip malformed entries (start with punctuation, contain URLs, excessive length without delimiters)
        if name.startswith((')', '(', ',', ';', '-', '/')):
            return False
        if 'http://' in name or 'https://' in name or 'www.' in name:
            return False

        parts = None

        # Handle "Header: Item1, Item2" colon-list patterns
        # The header is usually descriptive context (like "Representatives:", "Roundtable:", "Denmark:")
        # and should be discarded - we only want to create actors for the listed items
        if ': ' in name:
            header, rest = name.split(': ', 1)

            # Only process if rest contains list delimiters (comma or semicolon)
            if ',' in rest or ';' in rest:
                parts = re.split(r'[,;]', rest)
                parts = [p.strip() for p in parts if p.strip()]
                # Header is discarded - it's descriptive context, not an actor
            else:
                # Single item after colon (like "Org: Subsidiary") - not a list, skip
                return False

        # If no colon split happened, try semicolon splitting
        if parts is None:
            if ';' in name:
                # Semicolons are reliable delimiters
                parts = [p.strip() for p in name.split(';') if p.strip()]
            else:
                # No clear delimiter - skip
                return False

        parts = [p for p in parts if p]

        if len(parts) <= 1:
            return False

        valid_parts = []
        short_allowlist = {'BT', 'BP', 'EY', 'EE', 'O2', 'HP', 'GM', 'GE', 'VW'}
        # Words that indicate this part is an event description (at start), not an org
        event_starters = ['roundtable', 'breakfast', 'lunch', 'dinner', 'meeting with', 'call with', 'stakeholder']

        for p in parts:
            clean = re.sub(r'^[,\s\)\(;]+', '', p)
            clean = re.sub(r'[,\s\)\(;]+$', '', clean).strip()

            # Skip parts that START with event words (but not orgs that contain them)
            clean_lower = clean.lower()
            if any(clean_lower.startswith(word) for word in event_starters):
                continue

            # Skip parts that look like sentences (too many words, common verbs)
            word_count = len(clean.split())
            if word_count > 8:
                continue

            is_valid_short = len(clean) == 2 and (clean.isupper() or clean in short_allowlist)
            if clean and (len(clean) > 2 or is_valid_short):
                valid_parts.append(clean)

        if not valid_parts: return False

        # Count what will be affected
        meeting_count = MeetingAttendee.objects.filter(actor=actor).count()

        # Count how many new actors will be created vs found existing
        new_actor_count = 0
        for clean_part in valid_parts:
            clean_name = re.sub(r'\(.*?\)', '', clean_part).strip().strip(',')
            org_keywords = ['Ltd', 'Limited', 'PLC', 'LLP', 'Council', 'Trust', 'University', 'Foundation', 'Group', 'Services', 'Association', 'Commission', 'BBC', 'ITN', 'Facebook', 'Google', 'BT', 'Amazon', 'The Times', 'The Guardian', 'Sky', 'Netflix', 'Microsoft', 'Apple']
            is_org = any(re.search(rf'\b{k}\b', clean_name, re.I) for k in org_keywords)
            if is_org:
                if not Organization.objects.filter(name=clean_name).exists():
                    new_actor_count += 1
            else:
                if not Person.objects.filter(name=clean_name).exists():
                    new_actor_count += 1

        # Always show what we're doing (dry-run or live)
        prefix = "Would split" if dry_run else "Splitting"
        self.stdout.write(f'  {prefix}: "{actor.name[:80]}..." -> {valid_parts[:5]}{"..." if len(valid_parts) > 5 else ""}')

        if dry_run:
            return {
                'actors_deleted': 1,
                'actors_created': new_actor_count,
                'meetings_relinked': meeting_count,
            }

        attendances = MeetingAttendee.objects.filter(actor=actor)
        meetings = list(attendances.values_list('meeting_id', flat=True))
        if not meetings:
            actor.delete()
            return {'actors_deleted': 1, 'actors_created': 0, 'meetings_relinked': 0}

        with transaction.atomic():
            new_actors = []
            for clean_part in valid_parts:
                role = ""
                role_match = re.search(r'\((.*?)\)', clean_part)
                if role_match:
                    role = role_match.group(1)
                    clean_name = clean_part.replace(f"({role})", "").strip()
                else:
                    clean_name = clean_part
                clean_name = clean_name.strip(',').strip()

                org_keywords = ['Ltd', 'Limited', 'PLC', 'LLP', 'Council', 'Trust', 'University', 'Foundation', 'Group', 'Services', 'Association', 'Commission', 'BBC', 'ITN', 'Facebook', 'Google', 'BT', 'Amazon', 'The Times', 'The Guardian', 'Sky', 'Netflix', 'Microsoft', 'Apple']
                is_org = any(re.search(rf'\b{k}\b', clean_name, re.I) for k in org_keywords)

                # Use filter().first() to handle duplicates, then create if needed
                if is_org:
                    new_act = Organization.objects.filter(name=clean_name).first()
                    if not new_act:
                        new_act = Organization.objects.create(name=clean_name, classification='Organization')
                else:
                    new_act = Person.objects.filter(name=clean_name).first()
                    if not new_act:
                        new_act = Person.objects.create(name=clean_name)
                new_actors.append(new_act)

            for mid in meetings:
                for new_act in new_actors:
                    MeetingAttendee.objects.get_or_create(meeting_id=mid, actor=new_act, defaults={'actor_name_raw': new_act.name})
            actor.delete()
        return {
            'actors_deleted': 1,
            'actors_created': new_actor_count,
            'meetings_relinked': len(meetings),
        }

    def fix_split_concatenated_orgs(self, dry_run, limit, verbose):
        """Split concatenated orgs (split_concatenated_orgs.py logic)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Split Concatenated Organizations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        concat_orgs = Organization.objects.filter(name__regex=r'(Ltd|Limited|PLC|Inc|LLP)\.?\s+[A-Z]').select_related('actor_ptr')
        if limit: concat_orgs = concat_orgs[:limit]

        count = concat_orgs.count()
        self.stdout.write(f'Found {count} potential concatenated organizations (Regex match)')

        split_count = 0
        skipped_count = 0
        skip_reasons = {}
        totals = {
            'ch_matches_deleted': 0,
            'identifiers_deleted': 0,
            'consultancies_cloned': 0,
            'orgs_created': 0,
        }

        for org in concat_orgs:
            parts, skip_reason = self._split_name(org.name, return_reason=True)
            if len(parts) <= 1:
                skipped_count += 1
                skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
                if verbose:
                    self.stdout.write(self.style.WARNING(f'  Skipped: "{org.name[:70]}" - {skip_reason}'))
                continue

            result = self._process_concat_org(org, dry_run, verbose)
            if result:
                split_count += 1
                if isinstance(result, dict):
                    for key in totals:
                        totals[key] += result.get(key, 0)

        # Show skip summary
        if skipped_count > 0:
            self.stdout.write(f'\nSkipped {skipped_count} organizations (passed regex but excluded by rules):')
            for reason, cnt in sorted(skip_reasons.items(), key=lambda x: -x[1]):
                self.stdout.write(f'  - {reason}: {cnt}')

        self.stdout.write(f'\nWill split: {split_count} organizations')

        # Store totals for reporting in Changes section
        self._fix_totals['split_concatenated_orgs'] = {
            'count': split_count,
            'totals': totals,
        }

        return split_count

    def _split_name(self, name, return_reason=False):
        """Split concatenated name. If return_reason=True, returns (parts, skip_reason)."""
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern.search(name):
                if return_reason:
                    return [name], f"matches exclusion pattern"
                return [name]

        match = self.CONCAT_PATTERN.match(name)
        if match:
            first = match.group(1).strip()
            second = match.group(2).strip()
            if len(second) < 3:
                if return_reason:
                    return [name], f"second part too short: '{second}'"
                return [name]
            skip_words = {'Co', 'Company', 'Partnership', 'Group', 'Holdings', 'UK', 'USA',
                          'Europe', 'International', 'Global', 'Worldwide', 'Inc', 'plc', 'Home'}
            if second in skip_words:
                if return_reason:
                    return [name], f"second part is skip word: '{second}'"
                return [name]
            if self.TRADING_AS_PATTERN.match(' ' + second) or second.lower().startswith('t/a'):
                if return_reason:
                    return [name], f"trading-as pattern: '{second}'"
                return [name]
            if first.lower().replace(' ', '') == second.lower().replace(' ', ''):
                if return_reason:
                    return [name], f"duplicate name parts"
                return [name]

            results = [first]
            results.extend(self._split_name(second))
            if return_reason:
                return results, None
            return results
        if return_reason:
            return [name], "no concat pattern match"
        return [name]

    def _process_concat_org(self, org, dry_run, verbose):
        """Process a concatenated org. Returns dict with counts or False if skipped."""
        parts = self._split_name(org.name)
        if len(parts) <= 1:
            return False

        # Count what will be affected
        ch_matches = CompaniesHouseMatch.objects.filter(organization_id=org.actor_ptr_id).count()
        identifiers = Identifier.objects.filter(
            content_type__model='organization',
            object_id=org.actor_ptr_id,
            scheme='uk.gov.companieshouse'
        ).count()
        consultancies = Consultancy.objects.filter(client=org).count()

        # Count new orgs that will be created (vs found existing)
        new_org_count = 0
        for part_name in parts[1:]:
            if not Organization.objects.filter(name=part_name).exists():
                new_org_count += 1

        # Always show what we're doing (dry-run or live)
        prefix = "Would split" if dry_run else "Splitting"
        self.stdout.write(f'  {prefix}: "{org.name[:60]}..." -> {parts}')
        if verbose or dry_run:
            self.stdout.write(f'    -> Will delete: {ch_matches} CH matches, {identifiers} identifiers')
            self.stdout.write(f'    -> Will create: {new_org_count} new orgs, clone {consultancies} consultancies')

        if dry_run:
            return {
                'ch_matches_deleted': ch_matches,
                'identifiers_deleted': identifiers,
                'consultancies_cloned': consultancies,
                'orgs_created': new_org_count,
            }

        consultancy_list = list(Consultancy.objects.filter(client=org))
        with transaction.atomic():
            CompaniesHouseMatch.objects.filter(organization_id=org.actor_ptr_id).delete()
            Identifier.objects.filter(content_type__model='organization', object_id=org.actor_ptr_id, scheme='uk.gov.companieshouse').delete()

            org.name = parts[0]
            org.save()

            new_orgs = []
            for part_name in parts[1:]:
                existing = Organization.objects.filter(name=part_name).first()
                if existing: new_org = existing
                else: new_org = Organization.objects.create(name=part_name, classification=org.classification)
                new_orgs.append(new_org)

            # Clone consultancies to new orgs (the original org keeps its consultancies)
            for consultancy in consultancy_list:
                for new_org in new_orgs:
                    Consultancy.objects.get_or_create(
                        label=consultancy.label, client=new_org, agency=consultancy.agency,
                        source=consultancy.source, start_date=consultancy.start_date, end_date=consultancy.end_date
                    )

            # Note: We do NOT delete consultancies from the original org - it's been renamed
            # to parts[0] and should keep its relationships
            CompaniesHouseMatch.objects.filter(organization=org).delete()

            org_ct = ContentType.objects.get_for_model(Organization)
            if not Note.objects.filter(content_type=org_ct, object_id=org.pk, content__startswith='Split into').exists():
                Note.objects.create(content_type=org_ct, object_id=org.pk, content=f'Split into {len(parts)} separate organizations')
        return {
            'ch_matches_deleted': ch_matches,
            'identifiers_deleted': identifiers,
            'consultancies_cloned': consultancies,
            'orgs_created': new_org_count,
        }

    def fix_split_consultancy_clients(self, dry_run, limit, min_length, verbose):
        """Split concatenated consultancy clients (split_consultancy_clients.py logic)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Split Consultancy Clients'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        orgs = Organization.objects.filter(
            consulting_agencies__isnull=False,
            name__regex=r'.{' + str(min_length) + r',}'
        ).distinct()

        filtered = []
        for org in orgs:
            if self._looks_like_concatenated_list(org.name):
                filtered.append(org)
                if limit and len(filtered) >= limit: break

        count = len(filtered)
        self.stdout.write(f'Found {count} organizations with long names')

        split_count = 0
        totals = {
            'orgs_created': 0,
            'client_relationships_cloned': 0,
            'client_relationships_deleted': 0,
            'ch_matches_deleted': 0,
        }

        for org in filtered:
            result = self._process_consultancy_client(org, dry_run, verbose)
            if result:
                split_count += 1
                if isinstance(result, dict):
                    for key in totals:
                        totals[key] += result.get(key, 0)

        # Store totals for reporting in Changes section
        self._fix_totals['split_consultancy_clients'] = {
            'count': split_count,
            'totals': totals,
        }

        return split_count

    def _looks_like_concatenated_list(self, name):
        words = name.split()
        allcaps_count = sum(1 for w in words if w.isupper() and len(w) >= 2)
        if allcaps_count >= 3: return True
        if ',' in name or ';' in name or '(' in name: return False
        potential_starts = sum(1 for w in words if w and w[0].isupper() and w.lower() not in self.CONTINUATION_WORDS)
        if len(words) >= 5 and potential_starts / len(words) > 0.8: return True
        if len(name) >= 200 and ',' not in name and '(' not in name: return True
        return False

    def _parse_company_names(self, raw_name):
        words = raw_name.split()
        if len(words) <= 1: return [raw_name]
        
        companies = []
        current_company = []
        i = 0
        while i < len(words):
            word = words[i]
            word_lower = word.lower()
            
            # Known company check would go here (abbreviated for space)
            
            if i + 1 < len(words):
                two_word = f"{word_lower} {words[i + 1].lower()}"
                if two_word in self.TWO_WORD_ENDINGS:
                    current_company.extend([word, words[i + 1]])
                    companies.append(' '.join(current_company))
                    current_company = []
                    i += 2
                    continue
            
            if word_lower in self.SUFFIX_WORDS:
                if current_company:
                    current_company.append(word)
                    companies.append(' '.join(current_company))
                    current_company = []
                elif companies:
                    companies[-1] = companies[-1] + ' ' + word
                i += 1
                continue
                
            if word_lower in self.CONTINUATION_WORDS:
                current_company.append(word)
                i += 1
                continue
                
            if word_lower in self.ORG_ENDINGS:
                current_company.append(word)
                companies.append(' '.join(current_company))
                current_company = []
                i += 1
                continue
                
            if word.isupper() and len(word) >= 2:
                if current_company:
                    companies.append(' '.join(current_company))
                    current_company = []
                companies.append(word)
                i += 1
                continue
                
            if word and word[0].isupper():
                if current_company:
                    last_lower = current_company[-1].lower()
                    if last_lower not in self.CONTINUATION_WORDS:
                        companies.append(' '.join(current_company))
                        current_company = []
            
            current_company.append(word)
            i += 1
            
        if current_company: companies.append(' '.join(current_company))
        companies = [c.strip() for c in companies if c.strip() and len(c.strip()) >= 2]
        return companies

    def _process_consultancy_client(self, org, dry_run, verbose):
        """Process a consultancy client. Returns dict with counts or False if skipped."""
        company_names = self._parse_company_names(org.name)
        if len(company_names) <= 1: return False

        # Count what will be affected
        consultancies_count = Consultancy.objects.filter(client=org).count()
        ch_matches_count = CompaniesHouseMatch.objects.filter(organization=org).count()

        # Count new orgs that will be created
        new_org_count = 0
        for company_name in company_names:
            if not Organization.objects.filter(name=company_name).exists():
                new_org_count += 1

        # Always show what we're doing (dry-run or live)
        prefix = "Would split" if dry_run else "Splitting"
        self.stdout.write(f'  {prefix}: "{org.name[:60]}..." -> {company_names[:5]}{"..." if len(company_names) > 5 else ""}')
        if verbose or dry_run:
            self.stdout.write(f'    -> Will create: {new_org_count} new client orgs, clone {consultancies_count} client relationships to each')
            self.stdout.write(f'    -> Will delete: {consultancies_count} original client relationships, {ch_matches_count} CH matches')

        if dry_run:
            return {
                'orgs_created': new_org_count,
                # Each client relationship gets cloned to each new org
                'client_relationships_cloned': consultancies_count * len(company_names),
                'client_relationships_deleted': consultancies_count,
                'ch_matches_deleted': ch_matches_count,
            }

        consultancies = list(Consultancy.objects.filter(client=org))
        with transaction.atomic():
            new_orgs = []
            for company_name in company_names:
                new_org = Organization.objects.filter(name=company_name).first()
                if not new_org:
                    new_org = Organization.objects.create(name=company_name, classification='company')
                new_orgs.append(new_org)

            # Clone consultancies to new orgs
            for consultancy in consultancies:
                for new_org in new_orgs:
                    existing = Consultancy.objects.filter(
                        client=new_org, agency=consultancy.agency,
                        start_date=consultancy.start_date, end_date=consultancy.end_date
                    ).first()
                    if not existing:
                        Consultancy.objects.create(
                            label=consultancy.label, client=new_org, agency=consultancy.agency,
                            source=consultancy.source, start_date=consultancy.start_date, end_date=consultancy.end_date
                        )

            # Delete consultancies from the original garbage org - they've been cloned to proper orgs
            # (Unlike _process_concat_org, this org is NOT renamed - it stays as garbage)
            Consultancy.objects.filter(client=org).delete()
            CompaniesHouseMatch.objects.filter(organization=org).delete()

            org_ct = ContentType.objects.get_for_model(Organization)
            if not Note.objects.filter(content_type=org_ct, object_id=org.pk, content__startswith='Split into').exists():
                Note.objects.create(content_type=org_ct, object_id=org.pk, content=f'Split into {len(company_names)} separate client organizations')
        return {
            'orgs_created': new_org_count,
            'client_relationships_cloned': consultancies_count * len(company_names),
            'client_relationships_deleted': consultancies_count,
            'ch_matches_deleted': ch_matches_count,
        }

    def fix_merge_split_names(self, dry_run):
        """Merge split Irish/Scottish surnames.

        FIXED: No longer relies on consecutive IDs.
        Instead, finds actors ending with Mc/Mac and looks for actors
        in the same import batch that start with lowercase (the suffix).
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Merge Split Irish/Scottish Names'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Find actors ending with Mc or Mac (potential split starts)
        potential_starts = Actor.objects.filter(
            Q(name__endswith=' Mc') | Q(name__endswith=' Mac')
        ).order_by('id')

        count = potential_starts.count()
        self.stdout.write(f"Found {count} potential split name starts")

        merged_count = 0
        totals = {
            'actors_deleted': 0,
            'memberships_migrated': 0,
            'donations_migrated': 0,
            'attendances_migrated': 0,
        }
        processed_ids = set()  # Track what we've already processed

        for actor_a in potential_starts:
            if actor_a.id in processed_ids:
                continue

            # Look for potential suffix actors (start with lowercase, similar created_at)
            # Check actors created around the same time (within 1 second)
            potential_suffixes = Actor.objects.filter(
                created_at__gte=actor_a.created_at,
                created_at__lte=actor_a.created_at + datetime.timedelta(seconds=2),
                id__gt=actor_a.id,  # Created after
            ).exclude(id__in=processed_ids).order_by('id')[:5]  # Look at next few actors

            for actor_b in potential_suffixes:
                if self._is_valid_split_name_pair(actor_a, actor_b):
                    result = self._merge_split_name_pair(actor_a, actor_b, dry_run)
                    if result:
                        merged_count += 1
                        processed_ids.add(actor_b.id)
                        if isinstance(result, dict):
                            for key in totals:
                                totals[key] += result.get(key, 0)
                    break  # Only merge with first valid match

        # Store totals for reporting in Changes section
        self._fix_totals['merge_split_names'] = {
            'count': merged_count,
            'totals': totals,
        }

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"✓ Merged {merged_count} split name pairs"))
        else:
            self.stdout.write(self.style.WARNING(f"Would merge {merged_count} split name pairs"))

        return merged_count

    def _is_valid_split_name_pair(self, a, b):
        """Check if two actors look like a split Irish/Scottish name pair."""
        if not b.name:
            return False
        if 'Ltd' in b.name or 'Limited' in b.name or 'PLC' in b.name:
            return False

        # The suffix should be short and look like a name continuation
        suffix = b.name.strip()

        # Should be relatively short (surname suffix)
        if len(suffix) > 20:
            return False

        # Should look like a name part (capitalized, not all caps)
        if suffix.isupper() or not suffix[0].isupper():
            return False

        # Combined name should look reasonable
        merged = a.name.rstrip() + suffix
        # Should have 2-4 words
        if len(merged.split()) < 2 or len(merged.split()) > 5:
            return False

        return True

    def _merge_split_name_pair(self, a, b, dry_run):
        """Merge a split name pair. Returns dict with counts or False if skipped."""
        base_name = a.name.rstrip()
        suffix = b.name.strip()
        merged_name = base_name + suffix

        # Count what will be affected
        memberships_count = Membership.objects.filter(person_id=b.id).count()
        donations_count = Donation.objects.filter(Q(donor_id=b.id) | Q(recipient_id=b.id)).count()
        attendances_count = MeetingAttendee.objects.filter(actor_id=b.id).count()

        # Always show what we're doing (dry-run or live)
        prefix = "Would merge" if dry_run else "Merging"
        self.stdout.write(f'  {prefix}: "{a.name}" + "{b.name}" -> "{merged_name}"')

        if dry_run:
            return {
                'actors_deleted': 1,
                'memberships_migrated': memberships_count,
                'donations_migrated': donations_count,
                'attendances_migrated': attendances_count,
            }

        with transaction.atomic():
            # Update all references from b to a
            Membership.objects.filter(person_id=b.id).update(person_id=a.id)
            Donation.objects.filter(donor_id=b.id).update(donor_id=a.id)
            Donation.objects.filter(recipient_id=b.id).update(recipient_id=a.id)
            MeetingAttendee.objects.filter(actor_id=b.id).update(actor_id=a.id)

            # Update the name
            a.name = merged_name
            if hasattr(a, 'person'):
                parts = merged_name.split()
                if len(parts) >= 2:
                    a.person.family_name = parts[-1]
                    a.person.given_name = " ".join(parts[:-1])
                    a.person.save()
            a.save()

            # Add cleanup note
            org_ct = ContentType.objects.get_for_model(Actor)
            Note.objects.create(
                content_type=org_ct,
                object_id=a.pk,
                content=f'[CLEANUP:merge_split_names] Merged from "{b.name}" (ID: {b.id})'
            )

            b.delete()

        return {
            'actors_deleted': 1,
            'memberships_migrated': memberships_count,
            'donations_migrated': donations_count,
            'attendances_migrated': attendances_count,
        }

    # --- New Phase 3.2 Fix Types ---

    def fix_convert_titled_persons(self, dry_run):
        """Convert Organization records with person titles to Person records.

        Finds Organizations whose names match person title patterns
        (MP, Lord, Sir, Dame, Dr, Prof, etc.) and converts them to Person.

        Only converts if the name is clearly a person (has title but no org indicators).
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Convert Titled Persons'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Patterns that indicate this is actually an organization, not a person
        ORG_SUFFIXES = [
            r'\bLtd\.?$', r'\bLimited$', r'\bPLC$', r'\bLLP$', r'\bInc\.?$',
            r'\bCorp\.?$', r'\bCorporation$', r'\bGroup$', r'\bHoldings?$',
            r'\bEstates?$', r'\bTrust$', r'\bFund$', r'\bFoundation$',
            r'\bCharity$', r'\bCouncil$', r'\bCommittee$', r'\bPanel$',
            r'\bAssociation$', r'\bSociety$', r'\bInstitute$', r'\bUnion$',
            r'\bClub$', r'\bForum$', r'\bProgramme$', r'\bProject$',
            # Ecclesiastical/institutional positions (not people)
            r'\bDiocese\b', r'\bArchdiocese\b', r'\bChurch\b', r'\bCathedral$',
            r'\bParish\b', r'\bMinistry\b', r'\bCongregation\b',
        ]

        # Known companies that have person-like titles but are organizations
        KNOWN_TITLE_COMPANIES = [
            'sir robert mcalpine',
            'sir richard sutton',
            'lady garden foundation',
            'lord sugar',  # The company, not the person
        ]

        # Find Organizations with person titles but no org indicators
        titled_orgs = []
        for org in Organization.objects.all().iterator():
            # Skip very short names (just titles like "OBE", "CBE", "MP")
            if len(org.name) < 8:
                continue

            if ActorClassifier.has_person_title(org.name):
                # Check if it also has organizational suffixes
                has_org_suffix = any(
                    re.search(pattern, org.name, re.IGNORECASE)
                    for pattern in ORG_SUFFIXES
                )
                # Skip concatenated names - these need splitting first
                has_concat_delimiter = any(d in org.name for d in [' & ', ' + ', '; ', ', ', ' and '])
                # Skip known companies with person-like titles
                is_known_company = any(
                    company in org.name.lower()
                    for company in KNOWN_TITLE_COMPANIES
                )

                if not has_org_suffix and not has_concat_delimiter and not is_known_company:
                    titled_orgs.append(org)

        count = len(titled_orgs)
        self.stdout.write(f'Found {count} organizations with person titles')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No titled person organizations to fix'))
            return 0

        converted_count = 0
        totals = {
            'orgs_deleted': 0,
            'persons_created': 0,
            'ch_matches_deleted': 0,
            'attendances_migrated': 0,
            'donations_migrated': 0,
            'consultancies_migrated': 0,
        }
        org_ct = ContentType.objects.get_for_model(Organization)

        for org in titled_orgs:
            # Check if already processed
            if Note.objects.filter(
                content_type=org_ct,
                object_id=org.pk,
                content__contains='[CLEANUP:convert_titled_persons]'
            ).exists():
                continue

            # Count what will be affected
            attendances_count = MeetingAttendee.objects.filter(actor_id=org.actor_ptr_id).count()
            donations_donor_count = Donation.objects.filter(donor_id=org.actor_ptr_id).count()
            donations_recipient_count = Donation.objects.filter(recipient_id=org.actor_ptr_id).count()
            consultancies_count = Consultancy.objects.filter(client_id=org.actor_ptr_id).count()
            ch_matches_count = CompaniesHouseMatch.objects.filter(organization=org).count()
            person_exists = Person.objects.filter(name=org.name).exists()

            # Always show what we're doing (dry-run or live)
            prefix = "Would convert" if dry_run else "Converting"
            self.stdout.write(f'  {prefix}: {org.name}')

            if dry_run:
                converted_count += 1
                totals['orgs_deleted'] += 1
                totals['persons_created'] += 0 if person_exists else 1
                totals['ch_matches_deleted'] += ch_matches_count
                totals['attendances_migrated'] += attendances_count
                totals['donations_migrated'] += donations_donor_count + donations_recipient_count
                totals['consultancies_migrated'] += consultancies_count
                continue

            with transaction.atomic():
                # Create new Person record (handle duplicates)
                person = Person.objects.filter(name=org.name).first()
                if not person:
                    person = Person.objects.create(
                        name=org.name,
                        family_name=org.name.split()[-1] if ' ' in org.name else org.name,
                        given_name=' '.join(org.name.split()[:-1]) if ' ' in org.name else '',
                    )

                # Migrate MeetingAttendee references
                MeetingAttendee.objects.filter(actor_id=org.actor_ptr_id).update(actor=person)

                # Migrate Donation references
                Donation.objects.filter(recipient_id=org.actor_ptr_id).update(recipient=person)
                Donation.objects.filter(donor_id=org.actor_ptr_id).update(donor=person)

                # Migrate Consultancy references (rare but possible)
                Consultancy.objects.filter(client_id=org.actor_ptr_id).update(client=person)

                # Delete CompaniesHouseMatch (not applicable for persons)
                CompaniesHouseMatch.objects.filter(organization=org).delete()

                # Add note to the new Person
                person_ct = ContentType.objects.get_for_model(Person)
                Note.objects.create(
                    content_type=person_ct,
                    object_id=person.pk,
                    content=f'[CLEANUP:convert_titled_persons] Converted from Organization ID {org.actor_ptr_id}'
                )

                # Delete original Organization
                org.delete()
                converted_count += 1

        # Store totals for reporting in Changes section
        self._fix_totals['convert_titled_persons'] = {
            'count': converted_count,
            'totals': totals,
        }

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Converted {converted_count} organizations to persons'))
        else:
            self.stdout.write(self.style.WARNING(f'Would convert {converted_count} organizations to persons'))

        return converted_count

    def fix_parse_event_descriptions(self, dry_run, limit):
        """Parse attendees from event descriptions, move description to purpose.

        Finds actors that are actually event descriptions (Roundtable, Call, Meeting, etc.)
        and either:
        1. Parses out attendee names and creates proper actors
        2. Moves the event description to meeting.purpose
        3. Deletes the garbage actor
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Parse Event Descriptions'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Find actors that look like event descriptions
        event_actors = []
        for actor in Actor.objects.all().iterator():
            if EventDescriptionParser.is_event_description(actor.name):
                event_actors.append(actor)
                if limit and len(event_actors) >= limit:
                    break

        count = len(event_actors)
        self.stdout.write(f'Found {count} actors that are event descriptions')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No event description actors to fix'))
            return 0

        parsed_count = 0
        totals = {
            'persons_deleted': 0,
            'persons_created': 0,
            'organizations_deleted': 0,
            'organizations_created': 0,
            'attendances_deleted': 0,
            'attendances_created': 0,
            'ch_matches_deleted': 0,
            'meetings_updated': 0,
        }
        actor_ct = ContentType.objects.get_for_model(Actor)

        for actor in event_actors:
            # Check if already processed
            if Note.objects.filter(
                content_type=actor_ct,
                object_id=actor.pk,
                content__contains='[CLEANUP:parse_event_descriptions]'
            ).exists():
                continue

            # Try to extract attendee names
            extracted = EventDescriptionParser.extract_attendees(actor.name)
            event_type = EventDescriptionParser.get_event_type(actor.name)

            # Skip if we can't extract attendees - don't delete data we can't parse
            if not extracted:
                continue

            # Count what will be affected
            attendances_count = MeetingAttendee.objects.filter(actor=actor).count()
            meetings = list(MeetingAttendee.objects.filter(actor=actor).values_list('meeting', flat=True))

            # Count new actors that will be created (by type)
            new_persons = 0
            new_orgs = 0
            for attendee_name in extracted:
                actor_type = ActorClassifier.classify(attendee_name)
                if actor_type == 'organization':
                    if not Organization.objects.filter(name=attendee_name).exists():
                        new_orgs += 1
                else:
                    if not Person.objects.filter(name=attendee_name).exists():
                        new_persons += 1

            # Count CH matches that will be deleted
            ch_matches_count = CompaniesHouseMatch.objects.filter(actor=actor).count()

            # Check if actor being deleted is Person or Organization
            is_person = isinstance(actor, Person)

            # Count meetings that would be updated
            meetings_to_update = 0
            if event_type:
                for meeting_id in meetings:
                    try:
                        meeting = MinisterialMeeting.objects.get(pk=meeting_id)
                        if not meeting.purpose or meeting.purpose == 'Not specified':
                            meetings_to_update += 1
                    except MinisterialMeeting.DoesNotExist:
                        pass

            # Show what we're doing (dry-run or live)
            prefix = "Would parse" if dry_run else "Parsing"
            self.stdout.write(f'  {prefix}: {actor.name[:60]}... -> {extracted[:3]}{"..." if len(extracted) > 3 else ""}')

            if dry_run:
                parsed_count += 1
                if is_person:
                    totals['persons_deleted'] += 1
                else:
                    totals['organizations_deleted'] += 1
                totals['persons_created'] += new_persons
                totals['organizations_created'] += new_orgs
                totals['attendances_deleted'] += attendances_count
                totals['attendances_created'] += len(extracted) * len(meetings)
                totals['ch_matches_deleted'] += ch_matches_count
                totals['meetings_updated'] += meetings_to_update
                continue

            with transaction.atomic():
                # Get all meetings this actor is associated with
                attendances = MeetingAttendee.objects.filter(actor=actor)
                meetings = list(attendances.values_list('meeting', flat=True))

                # Create/find proper actors for extracted attendees
                for attendee_name in extracted:
                    actor_type = ActorClassifier.classify(attendee_name)
                    if actor_type == 'organization':
                        new_actor = Organization.objects.filter(name=attendee_name).first()
                        if not new_actor:
                            new_actor = Organization.objects.create(name=attendee_name, classification='Organization')
                    else:
                        new_actor = Person.objects.filter(name=attendee_name).first()
                        if not new_actor:
                            new_actor = Person.objects.create(name=attendee_name)

                    # Create MeetingAttendee for each meeting
                    for meeting_id in meetings:
                        MeetingAttendee.objects.get_or_create(
                            meeting_id=meeting_id,
                            actor=new_actor,
                            defaults={'actor_name_raw': attendee_name}
                        )

                # Move event description to meeting.purpose if appropriate
                if event_type:
                    for meeting_id in meetings:
                        try:
                            meeting = MinisterialMeeting.objects.get(pk=meeting_id)
                            if not meeting.purpose or meeting.purpose == 'Not specified':
                                meeting.purpose = actor.name
                                meeting.save(update_fields=['purpose'])
                        except MinisterialMeeting.DoesNotExist:
                            pass

                # Delete the original MeetingAttendee links
                attendances.delete()

                # Delete the event description actor if no other links
                remaining_links = (
                    MeetingAttendee.objects.filter(actor=actor).count() +
                    Donation.objects.filter(Q(donor=actor) | Q(recipient=actor)).count() +
                    Consultancy.objects.filter(Q(client=actor) | Q(agency=actor)).count()
                )
                if remaining_links == 0:
                    actor.delete()

                parsed_count += 1

        # Store totals for reporting in Changes section
        self._fix_totals['parse_event_descriptions'] = {
            'count': parsed_count,
            'totals': totals,
        }

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Parsed {parsed_count} event descriptions'))
        else:
            self.stdout.write(self.style.WARNING(f'Would parse {parsed_count} event descriptions'))

        return parsed_count

    def fix_normalize_actor_names(self, dry_run, limit):
        """Fix name quality issues (double spaces, trailing punctuation).

        Note: Does NOT fix lowercase starts - too many valid exceptions
        (eBay, iPhone, iPlayer, etc.)
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Normalize Actor Names'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Find actors with quality issues
        actors_with_issues = []
        for actor in Actor.objects.all().iterator():
            issues = NameNormalizer.has_quality_issues(actor.name)
            # Only process double_spaces, tabular_columns, and trailing/leading punctuation
            fixable = [i for i in issues if i in ['double_spaces', 'tabular_columns', 'trailing_punctuation', 'leading_punctuation', 'leading_trailing_whitespace']]
            if fixable:
                actors_with_issues.append((actor, fixable))
                if limit and len(actors_with_issues) >= limit:
                    break

        count = len(actors_with_issues)
        self.stdout.write(f'Found {count} actors with name quality issues')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No name quality issues to fix'))
            return 0

        fixed_count = 0
        totals = {
            'renamed': 0,
            'merged': 0,
            'actors_deleted': 0,
            'attendances_migrated': 0,
            'donations_migrated': 0,
            'consultancies_migrated': 0,
        }
        actor_ct = ContentType.objects.get_for_model(Actor)

        for actor, issues in actors_with_issues:
            # Check if already processed
            if Note.objects.filter(
                content_type=actor_ct,
                object_id=actor.pk,
                content__contains='[CLEANUP:normalize_actor_names]'
            ).exists():
                continue

            normalized = NameNormalizer.normalize(actor.name)

            # Check if normalized name already exists (will need merge)
            existing = Actor.objects.filter(name=normalized).exclude(pk=actor.pk).first()

            # Count what will be affected if merging
            if existing:
                attendances_count = MeetingAttendee.objects.filter(actor=actor).count()
                donations_count = Donation.objects.filter(Q(donor=actor) | Q(recipient=actor)).count()
                consultancies_count = Consultancy.objects.filter(Q(client=actor) | Q(agency=actor)).count()

            # Always show what we're doing (dry-run or live)
            if existing:
                prefix = "Would merge" if dry_run else "Merging"
                self.stdout.write(f'  {prefix}: "{actor.name}" -> "{normalized}" (exists) ({", ".join(issues)})')
            else:
                prefix = "Would normalize" if dry_run else "Normalizing"
                self.stdout.write(f'  {prefix}: "{actor.name}" -> "{normalized}" ({", ".join(issues)})')

            if dry_run:
                fixed_count += 1
                if existing:
                    totals['merged'] += 1
                    totals['actors_deleted'] += 1
                    totals['attendances_migrated'] += attendances_count
                    totals['donations_migrated'] += donations_count
                    totals['consultancies_migrated'] += consultancies_count
                else:
                    totals['renamed'] += 1
                continue

            with transaction.atomic():
                if existing:
                    # Merge into existing
                    MeetingAttendee.objects.filter(actor=actor).update(actor=existing)
                    Donation.objects.filter(donor=actor).update(donor=existing)
                    Donation.objects.filter(recipient=actor).update(recipient=existing)
                    Consultancy.objects.filter(client=actor).update(client=existing)
                    Consultancy.objects.filter(agency=actor).update(agency=existing)

                    Note.objects.create(
                        content_type=actor_ct,
                        object_id=existing.pk,
                        content=f'[CLEANUP:normalize_actor_names] Merged from "{actor.name}" (ID: {actor.pk})'
                    )
                    actor.delete()
                else:
                    # Just update the name
                    old_name = actor.name
                    actor.name = normalized
                    actor.save()

                    Note.objects.create(
                        content_type=actor_ct,
                        object_id=actor.pk,
                        content=f'[CLEANUP:normalize_actor_names] Normalized from "{old_name}"'
                    )

                fixed_count += 1

        # Store totals for reporting in Changes section
        self._fix_totals['normalize_actor_names'] = {
            'count': fixed_count,
            'totals': totals,
        }

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Fixed {fixed_count} actor names'))
        else:
            self.stdout.write(self.style.WARNING(f'Would fix {fixed_count} actor names'))

        return fixed_count

    def fix_split_camelcase(self, dry_run, limit):
        """Split CamelCase smashed names with no delimiter.

        NOTE: This fix is DISABLED because CamelCase is commonly used for legitimate
        brand names (TikTok, AstraZeneca, FirstGroup, etc.) and cannot be reliably
        distinguished from concatenation errors. Use split_concatenated_orgs instead,
        which handles "Company Ltd Another Company" patterns with clear structural signals.

        Example: "Wildlife and Countryside LinkNorth Yorkshire Moors"
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Split CamelCase Names'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))
        self.stdout.write(self.style.WARNING(
            'DISABLED: CamelCase splitting cannot reliably distinguish brand names '
            '(TikTok, AstraZeneca) from concatenation errors. Use split_concatenated_orgs instead.'
        ))
        return 0

        # Find actors with CamelCase patterns
        camelcase_actors = []
        for actor in Actor.objects.all().iterator():
            if CamelCaseSplitter.should_split(actor.name):
                camelcase_actors.append(actor)
                if limit and len(camelcase_actors) >= limit:
                    break

        count = len(camelcase_actors)
        self.stdout.write(f'Found {count} actors with CamelCase concatenation')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No CamelCase actors to fix'))
            return 0

        split_count = 0
        skipped_count = 0  # Skipped due to low confidence (no existing parts)
        totals = {
            'actors_deleted': 0,
            'actors_created': 0,
            'attendances_deleted': 0,
            'attendances_created': 0,
            'consultancies_deleted': 0,
            'consultancies_cloned': 0,
            'ch_matches_deleted': 0,
        }
        actor_ct = ContentType.objects.get_for_model(Actor)

        for actor in camelcase_actors:
            # Check if already processed
            if Note.objects.filter(
                content_type=actor_ct,
                object_id=actor.pk,
                content__contains='[CLEANUP:split_camelcase]'
            ).exists():
                continue

            parts = CamelCaseSplitter.split(actor.name)

            if len(parts) <= 1:
                continue

            # CONFIDENCE CHECK: Only split if ALL parts already exist as actors
            # This prevents splitting legitimate CamelCase brands like "TikTok"
            # and avoids false positives from common words like "Zoom", "Action", etc.
            all_parts_exist = True
            valid_parts_count = 0
            for part_name in parts:
                part_name = part_name.strip()
                if not part_name or len(part_name) < 3:
                    continue
                valid_parts_count += 1
                # Check if this part exists as an actor (case-insensitive)
                if not Actor.objects.filter(name__iexact=part_name).exists():
                    all_parts_exist = False
                    break

            # HIGH CONFIDENCE: Require ALL parts to already exist
            # This ensures we only split when we have strong evidence
            if not all_parts_exist or valid_parts_count < 2:
                skipped_count += 1
                continue

            # Count what will be affected
            attendances_count = MeetingAttendee.objects.filter(actor=actor).count()
            consultancies_count = Consultancy.objects.filter(client=actor).count()
            ch_matches_count = CompaniesHouseMatch.objects.filter(organization_id=actor.pk).count()

            # Count new actors that will be created
            new_actor_count = 0
            for part_name in parts:
                part_name = part_name.strip()
                if not part_name:
                    continue
                actor_type = ActorClassifier.classify(part_name)
                if actor_type == 'organization':
                    if not Organization.objects.filter(name=part_name).exists():
                        new_actor_count += 1
                else:
                    if not Person.objects.filter(name=part_name).exists():
                        new_actor_count += 1

            # Always show what we're doing (dry-run or live)
            prefix = "Would split" if dry_run else "Splitting"
            self.stdout.write(f'  {prefix}: "{actor.name}" -> {parts} (all {valid_parts_count} parts exist)')

            if dry_run:
                split_count += 1
                totals['actors_deleted'] += 1
                totals['actors_created'] += new_actor_count
                totals['attendances_deleted'] += attendances_count
                totals['attendances_created'] += attendances_count * len(parts)
                totals['consultancies_deleted'] += consultancies_count
                totals['consultancies_cloned'] += consultancies_count * len(parts)
                totals['ch_matches_deleted'] += ch_matches_count
                continue

            with transaction.atomic():
                # Get all meetings/relationships
                attendances = list(MeetingAttendee.objects.filter(actor=actor))
                consultancies = list(Consultancy.objects.filter(client=actor))

                # Create new actors for each part
                new_actors = []
                for part_name in parts:
                    part_name = part_name.strip()
                    if not part_name:
                        continue

                    actor_type = ActorClassifier.classify(part_name)
                    if actor_type == 'organization':
                        new_actor = Organization.objects.filter(name=part_name).first()
                        if not new_actor:
                            new_actor = Organization.objects.create(name=part_name, classification='Organization')
                    else:
                        new_actor = Person.objects.filter(name=part_name).first()
                        if not new_actor:
                            new_actor = Person.objects.create(name=part_name)
                    new_actors.append(new_actor)

                # Clone MeetingAttendee relationships
                # Unique constraint is on (meeting, actor_name_raw), not (meeting, actor)
                for attendance in attendances:
                    for new_actor in new_actors:
                        MeetingAttendee.objects.get_or_create(
                            meeting=attendance.meeting,
                            actor_name_raw=new_actor.name,
                            defaults={'actor': new_actor}
                        )

                # Clone Consultancy relationships
                for consultancy in consultancies:
                    for new_actor in new_actors:
                        Consultancy.objects.get_or_create(
                            client=new_actor,
                            agency=consultancy.agency,
                            defaults={
                                'label': consultancy.label,
                                'source': consultancy.source,
                                'start_date': consultancy.start_date,
                                'end_date': consultancy.end_date,
                            }
                        )

                # Add note and delete original
                Note.objects.create(
                    content_type=actor_ct,
                    object_id=actor.pk,
                    content=f'[CLEANUP:split_camelcase] Split into {len(parts)} actors'
                )

                # Delete original relationships and actor
                MeetingAttendee.objects.filter(actor=actor).delete()
                Consultancy.objects.filter(client=actor).delete()
                CompaniesHouseMatch.objects.filter(organization_id=actor.pk).delete()
                actor.delete()

                split_count += 1

        # Store totals for reporting in Changes section
        totals['skipped_low_confidence'] = skipped_count
        self._fix_totals['split_camelcase'] = {
            'count': split_count,
            'totals': totals,
        }

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Split {split_count} CamelCase actors (skipped {skipped_count} - low confidence)'))
        else:
            self.stdout.write(self.style.WARNING(f'Would split {split_count} CamelCase actors (skipping {skipped_count} - low confidence)'))

        return split_count

    def fix_merge_duplicate_types(self, dry_run):
        """Merge Person/Organization records with the same name.

        For names that appear as both Person AND Organization, determines
        the correct type and sets canonical links.
        """
        self.stdout.write(self.style.HTTP_INFO('\n## Merge Duplicate Types'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Find names that appear in both Person and Organization
        person_names = set(Person.objects.values_list('name', flat=True))
        org_names = set(Organization.objects.values_list('name', flat=True))
        duplicate_names = person_names & org_names

        count = len(duplicate_names)
        self.stdout.write(f'Found {count} names that exist as both Person and Organization')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No duplicate type names to fix'))
            return 0

        merged_count = 0
        totals = {
            'persons_deleted': 0,
            'orgs_deleted': 0,
            'attendances_migrated': 0,
            'donations_migrated': 0,
            'consultancies_migrated': 0,
            'memberships_deleted': 0,
            'ch_matches_deleted': 0,
        }
        actor_ct = ContentType.objects.get_for_model(Actor)

        # Skip list - entities that need manual review due to complex relationships
        skip_names = {
            'APPG',  # All-Party Parliamentary Group - has lobbyist memberships
            'BEIS',  # Department - has lobbyist memberships
        }

        for name in duplicate_names:
            if name in skip_names:
                self.stdout.write(f'  Skipping (manual review needed): "{name}"')
                continue

            person = Person.objects.filter(name=name).first()
            org = Organization.objects.filter(name=name).first()

            if not person or not org:
                continue

            # Check if already processed
            if Note.objects.filter(
                content_type=actor_ct,
                object_id__in=[person.pk, org.pk],
                content__contains='[CLEANUP:merge_duplicate_types]'
            ).exists():
                continue

            # Determine correct type
            correct_type = self._determine_correct_actor_type(name, person, org)

            # Count what will be affected
            if correct_type == 'person':
                to_merge = org
                attendances_count = MeetingAttendee.objects.filter(actor=to_merge).count()
                donations_count = Donation.objects.filter(Q(donor=to_merge) | Q(recipient=to_merge)).count()
                consultancies_count = Consultancy.objects.filter(Q(client=to_merge) | Q(agency=to_merge)).count()
                ch_matches_count = CompaniesHouseMatch.objects.filter(organization=to_merge).count()
                memberships_count = 0
            else:
                to_merge = person
                attendances_count = MeetingAttendee.objects.filter(actor=to_merge).count()
                donations_count = Donation.objects.filter(Q(donor=to_merge) | Q(recipient=to_merge)).count()
                consultancies_count = 0
                ch_matches_count = 0
                memberships_count = Membership.objects.filter(person=to_merge).count()

            # Always show what we're doing (dry-run or live)
            prefix = "Would merge" if dry_run else "Merging"
            self.stdout.write(f'  {prefix}: "{name}" -> {correct_type}')

            if dry_run:
                merged_count += 1
                if correct_type == 'person':
                    totals['orgs_deleted'] += 1
                else:
                    totals['persons_deleted'] += 1
                totals['attendances_migrated'] += attendances_count
                totals['donations_migrated'] += donations_count
                totals['consultancies_migrated'] += consultancies_count
                totals['memberships_deleted'] += memberships_count
                totals['ch_matches_deleted'] += ch_matches_count
                continue

            with transaction.atomic():
                if correct_type == 'person':
                    # Keep Person, merge Org into it
                    canonical = person
                    to_merge = org

                    # Update Org's relationships to point to Person
                    MeetingAttendee.objects.filter(actor=to_merge).update(actor=canonical)
                    Donation.objects.filter(donor=to_merge).update(donor=canonical)
                    Donation.objects.filter(recipient=to_merge).update(recipient=canonical)
                    Consultancy.objects.filter(client=to_merge).update(client=canonical)
                    Consultancy.objects.filter(agency=to_merge).update(agency=canonical)

                    # Delete CH match (not applicable for persons)
                    CompaniesHouseMatch.objects.filter(organization=to_merge).delete()

                    Note.objects.create(
                        content_type=actor_ct,
                        object_id=canonical.pk,
                        content=f'[CLEANUP:merge_duplicate_types] Merged Organization ID {to_merge.pk}'
                    )

                    to_merge.delete()
                else:
                    # Keep Organization, merge Person into it
                    canonical = org
                    to_merge = person

                    # Update Person's relationships to point to Org
                    MeetingAttendee.objects.filter(actor=to_merge).update(actor=canonical)
                    Donation.objects.filter(donor=to_merge).update(donor=canonical)
                    Donation.objects.filter(recipient=to_merge).update(recipient=canonical)
                    Membership.objects.filter(person=to_merge).delete()  # Can't transfer memberships

                    Note.objects.create(
                        content_type=actor_ct,
                        object_id=canonical.pk,
                        content=f'[CLEANUP:merge_duplicate_types] Merged Person ID {to_merge.pk}'
                    )

                    to_merge.delete()

                merged_count += 1

        # Store totals for reporting in Changes section
        self._fix_totals['merge_duplicate_types'] = {
            'count': merged_count,
            'totals': totals,
        }

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'✓ Merged {merged_count} duplicate type records'))
        else:
            self.stdout.write(self.style.WARNING(f'Would merge {merged_count} duplicate type records'))

        return merged_count

    def _determine_correct_actor_type(self, name, person, org):
        """Determine whether a name should be Person or Organization."""

        # If has person title (MP, Lord, Sir, etc.) -> Person
        if ActorClassifier.has_person_title(name):
            return 'person'

        # If has corporate suffix (Ltd, PLC, etc.) -> Organization
        actor_type = ActorClassifier.classify(name)
        if actor_type == 'organization':
            return 'organization'

        # If has Companies House match -> Organization
        if CompaniesHouseMatch.objects.filter(
            organization=org,
            status__in=['approved', 'auto_approved']
        ).exists():
            return 'organization'

        # If has donations as recipient (politicians receive donations) -> Person
        person_donations = Donation.objects.filter(recipient=person).count()
        org_donations = Donation.objects.filter(recipient=org).count()
        if person_donations > org_donations:
            return 'person'

        # If has Membership records -> Person
        if Membership.objects.filter(person=person).exists():
            return 'person'

        # Default to Organization (safer - can be a person acting in org capacity)
        return 'organization'

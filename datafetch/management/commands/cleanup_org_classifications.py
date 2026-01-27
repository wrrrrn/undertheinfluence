"""
Cleanup Organization Classifications Management Command

Rationalizes and standardizes Organization.classification values.

Issues addressed:
1. Case inconsistencies ("Company" vs "company")
2. Duplicate categories ("Political Party" vs "Registered Political Party")
3. Vague placeholders ("External Organization", "Other", None)
4. Typos and inconsistent naming

Usage:
    # Show current state and what would change (dry-run)
    python manage.py cleanup_org_classifications --dry-run

    # Apply the cleanup
    python manage.py cleanup_org_classifications

    # Show detailed stats only
    python manage.py cleanup_org_classifications --stats-only
"""

import time
from collections import Counter
from django.core.management.base import BaseCommand
from django.db import transaction

from datafetch.models import Organization


class Command(BaseCommand):
    help = 'Cleanup and rationalize Organization classification values'

    # Mapping of old values to new standardized values
    # Format: 'old_value': 'New Standardized Value'
    CLASSIFICATION_MAP = {
        # Case fixes
        'company': 'Company',
        'Friendly society': 'Friendly Society',
        'Unincorporated association': 'Unincorporated Association',
        'chamber': 'Legislature',  # Parliamentary chambers (House of Commons, Lords, etc.)
        'metro': 'Legislature',  # Regional legislatures (London Assembly)

        # Casing fixes
        'Uk Establishment': 'UK Establishment',
        'Lobbying agency': 'Lobbying Agency',

        # Merge duplicates - Political
        'Registered Political Party': 'Political Party',
        'Registered Party': 'Political Party',

        # Merge duplicates - Company types
        'Private Unlimited Nsc': 'Private Unlimited Company',
        'Oversea Company': 'Overseas Company',  # Fix typo

        # Merge CIO variants
        'Scottish CIO': 'Charitable Incorporated Organisation',

        # Standardize case for Lobbying
        'Lobbying agency': 'Lobbying Agency',

        # Merge similar society types
        'Industrial and Provident Society': 'Registered Society',
        'Building Society': 'Registered Society',

        # Vague categories -> Unknown
        'Organization': 'Unknown',
        # Note: 'Other' and 'External Organization' are in REVIEW_CATEGORIES
        # They need manual investigation, not auto-mapping

        # None/empty -> Unknown
        None: 'Unknown',
        '': 'Unknown',
    }

    # Categories that should be reviewed (flagged but not changed)
    REVIEW_CATEGORIES = [
        'External Organization',  # 23,923 - needs investigation
        'Other',  # 885 - mixed bag
        'Converted Or Closed',  # 11 - defunct companies
        'Impermissible Donor',  # 1 - EC edge case
    ]

    # The canonical list of valid categories after cleanup
    VALID_CATEGORIES = [
        # Company Types (Companies House legal forms)
        'Private Limited Company',
        'Public Limited Company',
        'Private Limited by Guarantee',
        'Limited Liability Partnership',
        'Limited Partnership',
        'Private Unlimited Company',
        'Unregistered Company',
        'Overseas Company',
        'Registered Overseas Entity',
        'UK Establishment',
        'Company',  # Generic company (legacy)
        'Converted Or Closed',
        'Investment Company With Variable Capital',

        # Non-profit/Charitable
        'Charitable Incorporated Organisation',
        'Registered Society',
        'Friendly Society',
        'Royal Charter Company',
        'Assurance Company',
        'Trust',

        # Associations
        'Unincorporated Association',
        'Trade Union',
        'Members Association',
        'Chamber of Commerce',

        # Political/Government
        'Political Party',
        'Legislature',  # Parliamentary chambers (House of Commons, Lords, etc.)
        'Lobbying Agency',
        'Government Department',

        # Electoral Commission Types
        'Permitted Participant',
        'Third Party',
        'Public Fund',
        'Impermissible Donor',

        # Companies House Roles
        'Corporate Beneficial Owner',
        'Corporate Director',

        # Placeholder/Unknown
        'External Organization',  # To be reviewed
        'Other',
        'Unknown',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Only show current statistics, no changes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for updates (default: 1000)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        stats_only = options['stats_only']
        batch_size = options['batch_size']

        start_time = time.time()

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Organization Classification Cleanup'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # Show current state
        self._show_current_stats()

        if stats_only:
            return

        # Show what will change
        self._show_planned_changes()

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes will be made'))
            return

        # Apply changes
        self._apply_changes(batch_size)

        # Show final state
        self.stdout.write('')
        self._show_current_stats(title='Final State')

        elapsed = time.time() - start_time
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Cleanup complete in {elapsed:.1f}s'))

    def _show_current_stats(self, title='Current State'):
        """Display current classification statistics."""
        self.stdout.write(self.style.HTTP_INFO(f'\n## {title}'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        total = Organization.objects.count()
        cats = Counter(Organization.objects.values_list('classification', flat=True))

        self.stdout.write(f'Total Organizations: {total:,}')
        self.stdout.write(f'Unique Classifications: {len(cats)}')
        self.stdout.write('')

        # Group by category type
        company_types = []
        nonprofit_types = []
        political_types = []
        ec_types = []
        ch_roles = []
        other_types = []
        issues = []

        for cat, count in cats.items():
            cat_display = cat or '(none)'
            entry = (cat_display, count)

            # Categorize
            if cat in [None, '', 'Organization', 'Other', 'External Organization', 'Unknown']:
                issues.append(entry)
            elif cat in ['Political Party', 'Registered Political Party', 'Registered Party',
                        'Legislature', 'chamber',  # Parliamentary chambers
                        'Lobbying Agency', 'Lobbying agency', 'Government Department']:
                political_types.append(entry)
            elif cat in ['Permitted Participant', 'Third Party', 'Public Fund', 'Impermissible Donor']:
                ec_types.append(entry)
            elif cat in ['Corporate Beneficial Owner', 'Corporate Director']:
                ch_roles.append(entry)
            elif 'Company' in str(cat) or 'Limited' in str(cat) or 'LLP' in str(cat) or \
                 cat in ['Company', 'company', 'Overseas Company', 'Oversea Company',
                        'UK Establishment', 'Uk Establishment', 'Registered Overseas Entity',
                        'Converted Or Closed', 'Investment Company With Variable Capital',
                        'Unregistered Company']:
                company_types.append(entry)
            elif cat in ['Charitable Incorporated Organisation', 'Scottish CIO', 'Registered Society',
                        'Industrial and Provident Society', 'Building Society', 'Friendly Society',
                        'Friendly society', 'Royal Charter Company', 'Assurance Company', 'Trust']:
                nonprofit_types.append(entry)
            elif cat in ['Unincorporated Association', 'Unincorporated association', 'Trade Union',
                        'Members Association', 'Chamber of Commerce', 'chamber']:
                other_types.append(entry)
            else:
                other_types.append(entry)

        # Display by group
        self._print_category_group('Company Types', company_types)
        self._print_category_group('Non-profit/Charitable', nonprofit_types)
        self._print_category_group('Associations', other_types)
        self._print_category_group('Political/Government', political_types)
        self._print_category_group('Electoral Commission', ec_types)
        self._print_category_group('Companies House Roles', ch_roles)
        self._print_category_group('Issues/Unknown', issues, style='WARNING')

        # Summary stats
        self.stdout.write('')
        self.stdout.write('Summary:')

        # Count issues
        # Exclude known correct values (prepositions like 'by' should be lowercase in title case)
        correct_lowercase = ['UK Establishment', 'CIO', 'Private Limited by Guarantee']
        case_issues = sum(count for cat, count in cats.items()
                        if cat and cat != cat.title() and cat not in correct_lowercase)
        none_count = cats.get(None, 0) + cats.get('', 0)
        vague_count = cats.get('External Organization', 0) + cats.get('Organization', 0) + cats.get('Other', 0)

        self.stdout.write(f'  Case inconsistencies: ~{case_issues:,} records')
        self.stdout.write(f'  None/empty: {none_count:,} records')
        self.stdout.write(f'  Vague categories: {vague_count:,} records')

    def _print_category_group(self, title, entries, style=None):
        """Print a group of categories."""
        if not entries:
            return

        entries_sorted = sorted(entries, key=lambda x: -x[1])
        total = sum(count for _, count in entries)

        self.stdout.write('')
        if style == 'WARNING':
            self.stdout.write(self.style.WARNING(f'{title}: ({total:,} total)'))
        else:
            self.stdout.write(f'{title}: ({total:,} total)')

        for cat, count in entries_sorted:
            pct = (count / Organization.objects.count()) * 100
            self.stdout.write(f'  {count:>7,} ({pct:>5.1f}%)  {cat}')

    def _show_planned_changes(self):
        """Show what changes will be made."""
        self.stdout.write(self.style.HTTP_INFO('\n## Planned Changes'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        total_affected = 0
        changes = []

        for old_val, new_val in self.CLASSIFICATION_MAP.items():
            if old_val is None:
                count = Organization.objects.filter(classification__isnull=True).count()
            elif old_val == '':
                count = Organization.objects.filter(classification='').count()
            else:
                count = Organization.objects.filter(classification=old_val).count()

            if count > 0:
                changes.append((old_val, new_val, count))
                total_affected += count

        # Sort by count descending
        changes.sort(key=lambda x: -x[2])

        self.stdout.write(f'Total records to update: {total_affected:,}')
        self.stdout.write('')
        self.stdout.write(f'{"Old Value":<40} {"New Value":<35} {"Count":>10}')
        self.stdout.write('-' * 90)

        for old_val, new_val, count in changes:
            old_display = '(none)' if old_val is None else old_val if old_val else '(empty)'
            self.stdout.write(f'{old_display:<40} {new_val:<35} {count:>10,}')

        # Show categories flagged for review
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Categories flagged for manual review (not changed):'))
        for cat in self.REVIEW_CATEGORIES:
            count = Organization.objects.filter(classification=cat).count()
            if count > 0:
                self.stdout.write(f'  {cat}: {count:,}')

    def _apply_changes(self, batch_size):
        """Apply the classification changes."""
        self.stdout.write(self.style.HTTP_INFO('\n## Applying Changes'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        total_updated = 0

        for old_val, new_val in self.CLASSIFICATION_MAP.items():
            if old_val is None:
                queryset = Organization.objects.filter(classification__isnull=True)
            elif old_val == '':
                queryset = Organization.objects.filter(classification='')
            else:
                queryset = Organization.objects.filter(classification=old_val)

            count = queryset.count()
            if count == 0:
                continue

            old_display = '(none)' if old_val is None else old_val if old_val else '(empty)'
            self.stdout.write(f'  {old_display} -> {new_val}: ', ending='')
            self.stdout.flush()

            # Update in batches
            updated = 0
            with transaction.atomic():
                # For large updates, do in batches
                if count > batch_size:
                    while True:
                        # Get batch of IDs
                        batch_ids = list(queryset.values_list('id', flat=True)[:batch_size])
                        if not batch_ids:
                            break
                        Organization.objects.filter(id__in=batch_ids).update(classification=new_val)
                        updated += len(batch_ids)
                        self.stdout.write('.', ending='')
                        self.stdout.flush()
                else:
                    updated = queryset.update(classification=new_val)

            self.stdout.write(f' {updated:,} updated')
            total_updated += updated

        # Fix known legislature organizations by name
        # These are from ParlParse and may have been incorrectly classified before import fix
        legislature_names = [
            'House of Commons',
            'House of Lords',
            'Scottish Parliament',
            'Senedd',
            'Northern Ireland Assembly',
            'Crown',
            'London Assembly',  # metro -> Legislature
        ]
        legislature_qs = Organization.objects.filter(
            name__in=legislature_names
        ).exclude(classification='Legislature')

        legislature_count = legislature_qs.count()
        if legislature_count > 0:
            self.stdout.write(f'  Known legislatures -> Legislature: ', ending='')
            with transaction.atomic():
                updated = legislature_qs.update(classification='Legislature')
            self.stdout.write(f'{updated:,} updated')
            total_updated += updated

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total updated: {total_updated:,}'))

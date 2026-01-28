"""
Cleanup Person Data Management Command

Fixes data quality issues in Person records:
1. Corrupted honorific prefixes ("Lord na" → "Lord")
2. Inconsistent prefixes ("The Rt Hon" → "Rt Hon", "Prof" → "Professor")
3. Empty given_name/family_name fields
4. Identifies potential duplicates

Usage:
    # Show current state and what would change (dry-run)
    python manage.py cleanup_person_data --dry-run

    # Apply the cleanup
    python manage.py cleanup_person_data

    # Show detailed stats only
    python manage.py cleanup_person_data --stats-only

    # Fix only prefix issues
    python manage.py cleanup_person_data --fix prefixes

    # Fix only name parsing
    python manage.py cleanup_person_data --fix names

    # Check for duplicates (doesn't delete, just reports)
    python manage.py cleanup_person_data --check-duplicates
"""

import re
import time
from collections import Counter
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Count

from datafetch.models import Person


class Command(BaseCommand):
    help = 'Cleanup Person data quality issues'

    # Mapping of corrupted/inconsistent prefixes to standardized values
    PREFIX_MAP = {
        # Corrupted "na" prefixes
        'Lord na': 'Lord',
        'Lady na': 'Lady',

        # Standardize variations
        'The Rt Hon': 'Rt Hon',
        'Prof': 'Professor',
        'Hon.': 'Hon',

        # Fix spacing/formatting
        'Earl of': 'Earl',
        'Duchess of': 'Duchess',
        'Master of': 'Master',
    }

    # Valid standardized prefixes (for reference)
    VALID_PREFIXES = [
        # Nobility
        'Lord', 'Lady', 'Baron', 'Baroness', 'Earl', 'Countess',
        'Duke', 'Duchess', 'Viscount', 'Marquess', 'King', 'Queen',

        # Titles
        'Sir', 'Dame', 'Rt Hon', 'Hon',

        # Professional
        'Dr', 'Professor', 'Reverend', 'Bishop', 'Archbishop',

        # Common
        'Mr', 'Mrs', 'Ms', 'Miss',

        # Military
        'General', 'Brigadier', 'Colonel', 'Major', 'Captain',
        'Commander', 'Lieutenant', 'Admiral', 'Air Commodore',

        # Political
        'Cllr',  # Councillor
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
            '--fix',
            choices=['all', 'prefixes', 'names'],
            default='all',
            help='What to fix: all, prefixes only, or names only (default: all)'
        )
        parser.add_argument(
            '--check-duplicates',
            action='store_true',
            help='Check for potential duplicate persons'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for updates (default: 500)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        stats_only = options['stats_only']
        fix_type = options['fix']
        check_duplicates = options['check_duplicates']
        batch_size = options['batch_size']

        start_time = time.time()

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Person Data Cleanup'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # Show current state
        self._show_current_stats()

        if check_duplicates:
            self._check_duplicates()
            return

        if stats_only:
            return

        # Show what will change
        self._show_planned_changes(fix_type)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes will be made'))
            return

        # Apply changes
        if fix_type in ['all', 'prefixes']:
            self._fix_prefixes(batch_size)

        if fix_type in ['all', 'names']:
            self._fix_names(batch_size)

        # Show final state
        self.stdout.write('')
        self._show_current_stats(title='Final State')

        elapsed = time.time() - start_time
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Cleanup complete in {elapsed:.1f}s'))

    def _show_current_stats(self, title='Current State'):
        """Display current Person data statistics."""
        self.stdout.write(self.style.HTTP_INFO(f'\n## {title}'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        total = Person.objects.count()
        self.stdout.write(f'Total Persons: {total:,}')

        # Honorific prefix stats
        self.stdout.write('')
        self.stdout.write('Honorific Prefixes:')
        prefixes = Counter(Person.objects.values_list('honorific_prefix', flat=True))

        with_prefix = sum(c for p, c in prefixes.items() if p)
        without_prefix = prefixes.get(None, 0) + prefixes.get('', 0)
        self.stdout.write(f'  With prefix: {with_prefix:,}')
        self.stdout.write(f'  Without prefix: {without_prefix:,}')

        # Show prefix breakdown
        self.stdout.write('')
        self.stdout.write('  Prefix breakdown (top 25):')
        for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1])[:25]:
            if prefix:
                issues = []
                if 'na' in prefix:
                    issues.append('CORRUPTED')
                if prefix in self.PREFIX_MAP:
                    issues.append(f'→ {self.PREFIX_MAP[prefix]}')
                issue_str = f' [{", ".join(issues)}]' if issues else ''
                self.stdout.write(f'    {count:>6,}  {prefix}{issue_str}')

        # Name quality stats
        self.stdout.write('')
        self.stdout.write('Name Quality:')

        empty_given = Person.objects.filter(
            Q(given_name__isnull=True) | Q(given_name='')
        ).count()
        empty_family = Person.objects.filter(
            Q(family_name__isnull=True) | Q(family_name='')
        ).count()
        both_empty = Person.objects.filter(
            (Q(given_name__isnull=True) | Q(given_name='')) &
            (Q(family_name__isnull=True) | Q(family_name=''))
        ).count()

        self.stdout.write(f'  Empty given_name: {empty_given:,}')
        self.stdout.write(f'  Empty family_name: {empty_family:,}')
        self.stdout.write(f'  Both empty: {both_empty:,}')

        # Gender stats
        self.stdout.write('')
        self.stdout.write('Gender:')
        genders = Counter(Person.objects.values_list('gender', flat=True))
        for gender, count in genders.most_common():
            self.stdout.write(f'  {count:>6,}  {gender or "(none)"}')

        # Corrupted records summary
        self.stdout.write('')
        self.stdout.write('Data Issues Summary:')

        corrupted_prefix = Person.objects.filter(
            Q(honorific_prefix__contains=' na')
        ).count()
        self.stdout.write(f'  Corrupted prefixes ("na"): {corrupted_prefix}')

        inconsistent_prefix = sum(
            Person.objects.filter(honorific_prefix=old).count()
            for old in self.PREFIX_MAP.keys()
            if 'na' not in old
        )
        self.stdout.write(f'  Inconsistent prefixes: {inconsistent_prefix}')

    def _show_planned_changes(self, fix_type):
        """Show what changes will be made."""
        self.stdout.write(self.style.HTTP_INFO('\n## Planned Changes'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        total_affected = 0

        if fix_type in ['all', 'prefixes']:
            self.stdout.write('\nPrefix fixes:')
            self.stdout.write(f'{"Old Value":<20} {"New Value":<20} {"Count":>10}')
            self.stdout.write('-' * 55)

            for old_val, new_val in self.PREFIX_MAP.items():
                count = Person.objects.filter(honorific_prefix=old_val).count()
                if count > 0:
                    self.stdout.write(f'{old_val:<20} {new_val:<20} {count:>10,}')
                    total_affected += count

        if fix_type in ['all', 'names']:
            # Count records needing name parsing
            needs_parsing = Person.objects.filter(
                (Q(given_name__isnull=True) | Q(given_name='')) &
                (Q(family_name__isnull=True) | Q(family_name=''))
            ).exclude(
                Q(name__isnull=True) | Q(name='')
            ).count()

            self.stdout.write(f'\nName parsing needed: {needs_parsing:,} records')
            total_affected += needs_parsing

        self.stdout.write('')
        self.stdout.write(f'Total records to update: {total_affected:,}')

    def _fix_prefixes(self, batch_size):
        """Fix corrupted and inconsistent prefixes."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Prefixes'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        total_updated = 0

        for old_val, new_val in self.PREFIX_MAP.items():
            queryset = Person.objects.filter(honorific_prefix=old_val)
            count = queryset.count()

            if count == 0:
                continue

            self.stdout.write(f'  "{old_val}" → "{new_val}": ', ending='')
            self.stdout.flush()

            # For "Lord na" and "Lady na", we also need to fix the name
            if ' na' in old_val:
                updated = self._fix_na_records(queryset, new_val, batch_size)
            else:
                # Simple prefix replacement
                updated = queryset.update(honorific_prefix=new_val)

            self.stdout.write(f'{updated:,} updated')
            total_updated += updated

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total prefix fixes: {total_updated:,}'))

    def _fix_na_records(self, queryset, new_prefix, batch_size):
        """Fix records with corrupted 'na' in prefix."""
        updated = 0

        for person in queryset.iterator():
            # Extract the actual name part
            # "Lord na Clement-Jones" → family_name: "Clement-Jones"
            name = person.name
            old_prefix = person.honorific_prefix

            # Remove the corrupted prefix from the name
            clean_name = name.replace(f'{old_prefix} ', '').strip()

            # Parse the clean name
            # For Lords/Ladies, the name after the prefix is usually the family name or title
            family_name = clean_name

            # Update the record
            person.honorific_prefix = new_prefix
            person.name = f'{new_prefix} {clean_name}'
            person.family_name = family_name
            person.save(update_fields=['honorific_prefix', 'name', 'family_name'])

            updated += 1
            if updated % 50 == 0:
                self.stdout.write('.', ending='')
                self.stdout.flush()

        return updated

    def _fix_names(self, batch_size):
        """Parse names to fill in empty given_name/family_name."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Names'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Find records with empty given_name AND family_name but have a name
        queryset = Person.objects.filter(
            (Q(given_name__isnull=True) | Q(given_name='')) &
            (Q(family_name__isnull=True) | Q(family_name=''))
        ).exclude(
            Q(name__isnull=True) | Q(name='')
        )

        total = queryset.count()
        self.stdout.write(f'Found {total:,} records needing name parsing')

        if total == 0:
            return

        updated = 0
        errors = 0

        for person in queryset.iterator():
            try:
                given, family = self._parse_name(person.name, person.honorific_prefix)

                if given or family:
                    if given:
                        person.given_name = given
                    if family:
                        person.family_name = family
                    person.save(update_fields=['given_name', 'family_name'])
                    updated += 1

                if updated % 100 == 0:
                    self.stdout.write('.', ending='')
                    self.stdout.flush()

            except Exception as e:
                errors += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Names parsed: {updated:,}'))
        if errors:
            self.stdout.write(self.style.WARNING(f'Errors: {errors}'))

    def _parse_name(self, name, prefix=None):
        """
        Parse a full name into given_name and family_name.

        Handles patterns like:
        - "John Smith" → given: John, family: Smith
        - "Lord Smith" → given: None, family: Smith
        - "Sir John Smith" → given: John, family: Smith
        - "John David Smith" → given: John David, family: Smith

        Returns (given_name, family_name) tuple.
        """
        if not name:
            return None, None

        # Remove prefix from name if present
        if prefix and name.startswith(prefix):
            name = name[len(prefix):].strip()

        # Remove common prefixes that might be in the name
        for p in ['Lord', 'Lady', 'Sir', 'Dame', 'Dr', 'Mr', 'Mrs', 'Ms', 'Miss']:
            if name.startswith(p + ' '):
                name = name[len(p):].strip()
                break

        parts = name.split()

        if not parts:
            return None, None

        if len(parts) == 1:
            # Single name - assume it's the family name
            return None, parts[0]

        # Last part is family name, rest is given name
        family_name = parts[-1]
        given_name = ' '.join(parts[:-1])

        return given_name, family_name

    def _check_duplicates(self):
        """Check for potential duplicate Person records."""
        self.stdout.write(self.style.HTTP_INFO('\n## Checking for Duplicates'))
        self.stdout.write(self.style.HTTP_INFO('-' * 70))

        # Check for exact name duplicates
        self.stdout.write('\nExact name duplicates:')
        dupes = (
            Person.objects
            .values('name')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )[:20]

        for d in dupes:
            self.stdout.write(f'  {d["count"]:>3}x  "{d["name"]}"')

        # Check for "Lord na" records that have matching proper Lords
        self.stdout.write('\n"Lord na" records with potential matches:')
        lord_na = Person.objects.filter(honorific_prefix='Lord na')

        matches_found = 0
        for person in lord_na[:20]:
            # Extract family name from corrupted name
            family = person.name.replace('Lord na ', '').strip()
            # Look for matching Lord with proper prefix
            matches = Person.objects.filter(
                honorific_prefix='Lord',
                family_name__iexact=family
            ).exclude(pk=person.pk)

            if matches.exists():
                match = matches.first()
                self.stdout.write(
                    f'  "{person.name}" (ID:{person.pk}) ← duplicate of → '
                    f'"{match.name}" (ID:{match.pk})'
                )
                matches_found += 1

        if matches_found == 0:
            self.stdout.write('  No obvious matches found')

        # Summary
        total_dupes = Person.objects.values('name').annotate(
            count=Count('id')
        ).filter(count__gt=1).count()

        self.stdout.write('')
        self.stdout.write(f'Total names appearing more than once: {total_dupes:,}')

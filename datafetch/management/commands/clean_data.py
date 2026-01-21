"""
Data cleaning command to fix critical data quality issues.

Usage:
    python manage.py clean_data --dry-run
    python manage.py clean_data --fix=orphaned_donations
    python manage.py clean_data --fix=duplicate_donations
    python manage.py clean_data --fix=all
"""

from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import Count
from datafetch.models import Person, Organization, Donation, Membership
import datetime


class Command(BaseCommand):
    help = 'Clean critical data quality issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            type=str,
            help='What to fix: orphaned_donations, duplicate_donations, invalid_dates, all',
            default='all',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        fix_type = options['fix']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Data Cleaning Report'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        total_fixed = 0

        if fix_type in ('all', 'orphaned_donations'):
            total_fixed += self.fix_orphaned_donations(dry_run)

        if fix_type in ('all', 'duplicate_donations'):
            total_fixed += self.fix_duplicate_donations(dry_run)

        if fix_type in ('all', 'invalid_dates'):
            total_fixed += self.fix_invalid_membership_dates(dry_run)

        if fix_type in ('all', 'zero_value'):
            total_fixed += self.fix_zero_value_donations(dry_run)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would fix {total_fixed} issues (DRY RUN)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Fixed {total_fixed} issues'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

    def fix_orphaned_donations(self, dry_run):
        """Delete orphaned donations (null donor and zero value)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Fixing Orphaned Donations'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        # Orphaned donations with zero value and no dates - these are junk
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

        if not dry_run:
            with transaction.atomic():
                orphaned.delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} orphaned donations'))
        else:
            self.stdout.write(self.style.WARNING(f'Would delete {count} orphaned donations'))

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
                    # Keep the donation with minimum ID, delete the rest
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
            # Calculate what would be deleted
            for dup in duplicates:
                total_deleted += dup['count'] - 1

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
                # Partial dates
                pass

        count = len(invalid)
        self.stdout.write(f'Found {count} memberships with end_date < start_date')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No invalid membership dates to fix'))
            return 0

        if not dry_run:
            with transaction.atomic():
                for m in invalid:
                    # Swap start_date and end_date
                    old_start = m.start_date
                    old_end = m.end_date
                    m.start_date = old_end
                    m.end_date = old_start
                    m.save()

                    self.stdout.write(
                        f'  Fixed membership {m.id}: {m.person.name} @ {m.organization.name}'
                    )
                    self.stdout.write(f'    Before: start={old_start}, end={old_end}')
                    self.stdout.write(f'    After:  start={m.start_date}, end={m.end_date}')

            self.stdout.write(self.style.SUCCESS(f'✓ Fixed {count} invalid membership dates'))
        else:
            for m in invalid:
                self.stdout.write(
                    f'  Would fix membership {m.id}: swap {m.start_date} ↔ {m.end_date}'
                )
            self.stdout.write(self.style.WARNING(f'Would fix {count} invalid membership dates'))

        return count

    def fix_zero_value_donations(self, dry_run):
        """Delete zero-value donations with no dates (likely import placeholders)."""
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

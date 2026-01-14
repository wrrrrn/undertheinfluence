"""
Management command to check data quality and report issues.

Usage:
    python manage.py check_data_quality
    python manage.py check_data_quality --verbose
    python manage.py check_data_quality --check=duplicates
"""

from django.core.management.base import BaseCommand
from django.db import models
from decimal import Decimal
import datetime

from datafetch.models import Person, Organization, Donation, Consultancy, Membership, Post
from datafetch.models.influence_mapping import PartyMembership


class Command(BaseCommand):
    help = 'Check data quality and report potential issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            type=str,
            help='Specific check to run: duplicates, orphans, validation, completeness, all (default: all)',
            default='all',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each issue',
        )

    def handle(self, *args, **options):
        check_type = options['check']
        verbose = options['verbose']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Data Quality Check Report'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        total_issues = 0

        if check_type in ('all', 'orphans'):
            total_issues += self.check_orphaned_records(verbose)

        if check_type in ('all', 'duplicates'):
            total_issues += self.check_duplicates(verbose)

        if check_type in ('all', 'validation'):
            total_issues += self.check_validation(verbose)

        if check_type in ('all', 'completeness'):
            total_issues += self.check_completeness(verbose)

        if check_type in ('all', 'temporal'):
            total_issues += self.check_temporal_consistency(verbose)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS('✓ No data quality issues found!'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Total issues found: {total_issues}'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

    def check_orphaned_records(self, verbose):
        """Check for orphaned relationships (null foreign keys)."""
        self.stdout.write(self.style.HTTP_INFO('\n## Orphaned Records Check'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        issues = 0

        # Orphaned donations (donor or recipient deleted)
        orphaned_donations_donor = Donation.objects.filter(donor__isnull=True).count()
        orphaned_donations_recipient = Donation.objects.filter(recipient__isnull=True).count()

        if orphaned_donations_donor > 0:
            issues += orphaned_donations_donor
            self.stdout.write(self.style.WARNING(
                f'⚠ {orphaned_donations_donor} donations with null donor'
            ))
            if verbose:
                for donation in Donation.objects.filter(donor__isnull=True)[:5]:
                    self.stdout.write(f'  - Donation #{donation.id}: recipient={donation.recipient}, value=£{donation.value}')

        if orphaned_donations_recipient > 0:
            issues += orphaned_donations_recipient
            self.stdout.write(self.style.WARNING(
                f'⚠ {orphaned_donations_recipient} donations with null recipient'
            ))
            if verbose:
                for donation in Donation.objects.filter(recipient__isnull=True)[:5]:
                    self.stdout.write(f'  - Donation #{donation.id}: donor={donation.donor}, value=£{donation.value}')

        # Orphaned consultancies
        orphaned_consultancies_client = Consultancy.objects.filter(client__isnull=True).count()
        orphaned_consultancies_agency = Consultancy.objects.filter(agency__isnull=True).count()

        if orphaned_consultancies_client > 0:
            issues += orphaned_consultancies_client
            self.stdout.write(self.style.WARNING(
                f'⚠ {orphaned_consultancies_client} consultancies with null client'
            ))

        if orphaned_consultancies_agency > 0:
            issues += orphaned_consultancies_agency
            self.stdout.write(self.style.WARNING(
                f'⚠ {orphaned_consultancies_agency} consultancies with null agency'
            ))

        if issues == 0:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned records found'))

        return issues

    def check_duplicates(self, verbose):
        """Check for duplicate records."""
        self.stdout.write(self.style.HTTP_INFO('\n## Duplicate Records Check'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        issues = 0

        # Duplicate persons (same name)
        duplicate_persons = (
            Person.objects
            .values('name')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )

        if duplicate_persons.count() > 0:
            issues += duplicate_persons.count()
            self.stdout.write(self.style.WARNING(
                f'⚠ {duplicate_persons.count()} person names with duplicates'
            ))
            if verbose:
                for dup in duplicate_persons[:5]:
                    self.stdout.write(f'  - "{dup["name"]}" appears {dup["count"]} times')

        # Duplicate organizations (same name)
        duplicate_orgs = (
            Organization.objects
            .values('name')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )

        if duplicate_orgs.count() > 0:
            issues += duplicate_orgs.count()
            self.stdout.write(self.style.WARNING(
                f'⚠ {duplicate_orgs.count()} organization names with duplicates'
            ))
            if verbose:
                for dup in duplicate_orgs[:5]:
                    self.stdout.write(f'  - "{dup["name"]}" appears {dup["count"]} times')

        # Duplicate donations (same donor, recipient, value, date)
        duplicate_donations = (
            Donation.objects
            .values('donor', 'recipient', 'value', 'received_date')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
            .order_by('-count')
        )

        if duplicate_donations.count() > 0:
            issues += duplicate_donations.count()
            self.stdout.write(self.style.WARNING(
                f'⚠ {duplicate_donations.count()} potentially duplicate donations'
            ))
            if verbose:
                for dup in duplicate_donations[:5]:
                    self.stdout.write(f'  - {dup["count"]} donations: £{dup["value"]} on {dup["received_date"]}')

        if issues == 0:
            self.stdout.write(self.style.SUCCESS('✓ No duplicate records found'))

        return issues

    def check_validation(self, verbose):
        """Check for invalid data values."""
        self.stdout.write(self.style.HTTP_INFO('\n## Data Validation Check'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        issues = 0

        # Negative donation values
        negative_donations = Donation.objects.filter(value__lt=0).count()
        if negative_donations > 0:
            issues += negative_donations
            self.stdout.write(self.style.WARNING(f'⚠ {negative_donations} donations with negative value'))

        # Zero donation values
        zero_donations = Donation.objects.filter(value=0).count()
        if zero_donations > 0:
            issues += zero_donations
            self.stdout.write(self.style.WARNING(f'⚠ {zero_donations} donations with zero value'))

        # Donation date logic (accepted_date < received_date)
        invalid_donation_dates = 0
        for donation in Donation.objects.filter(
            received_date__isnull=False,
            accepted_date__isnull=False
        ).iterator():
            if donation.accepted_date < donation.received_date:
                invalid_donation_dates += 1
                if verbose and invalid_donation_dates <= 5:
                    self.stdout.write(
                        f'  - Donation #{donation.id}: accepted {donation.accepted_date} '
                        f'before received {donation.received_date}'
                    )

        if invalid_donation_dates > 0:
            issues += invalid_donation_dates
            self.stdout.write(self.style.WARNING(
                f'⚠ {invalid_donation_dates} donations with accepted_date < received_date'
            ))

        # Empty person names
        empty_person_names = Person.objects.filter(
            models.Q(name='') | models.Q(family_name='') | models.Q(given_name='')
        ).count()

        if empty_person_names > 0:
            issues += empty_person_names
            self.stdout.write(self.style.WARNING(f'⚠ {empty_person_names} persons with empty names'))

        # Empty organization names
        empty_org_names = Organization.objects.filter(name='').count()
        if empty_org_names > 0:
            issues += empty_org_names
            self.stdout.write(self.style.WARNING(f'⚠ {empty_org_names} organizations with empty names'))

        if issues == 0:
            self.stdout.write(self.style.SUCCESS('✓ No validation issues found'))

        return issues

    def check_completeness(self, verbose):
        """Check for missing required fields."""
        self.stdout.write(self.style.HTTP_INFO('\n## Data Completeness Check'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        issues = 0

        # Donations missing required fields
        donations_missing_type = Donation.objects.filter(donation_type='').count()
        if donations_missing_type > 0:
            issues += donations_missing_type
            self.stdout.write(self.style.WARNING(
                f'⚠ {donations_missing_type} donations missing donation_type'
            ))

        # Memberships missing start_date
        memberships_missing_start = Membership.objects.filter(
            models.Q(start_date__isnull=True) | models.Q(start_date='')
        ).count()
        if memberships_missing_start > 0:
            issues += memberships_missing_start
            self.stdout.write(self.style.WARNING(
                f'⚠ {memberships_missing_start} memberships missing start_date'
            ))

        # Posts without organization
        posts_without_org = Post.objects.filter(organization__isnull=True).count()
        if posts_without_org > 0:
            issues += posts_without_org
            self.stdout.write(self.style.WARNING(
                f'⚠ {posts_without_org} posts without organization'
            ))

        if issues == 0:
            self.stdout.write(self.style.SUCCESS('✓ No completeness issues found'))

        return issues

    def check_temporal_consistency(self, verbose):
        """Check for temporal/date consistency issues."""
        self.stdout.write(self.style.HTTP_INFO('\n## Temporal Consistency Check'))
        self.stdout.write(self.style.HTTP_INFO('-' * 80))

        issues = 0

        # Memberships with end_date < start_date
        invalid_membership_dates = 0
        for membership in Membership.objects.exclude(
            models.Q(start_date__isnull=True) | models.Q(start_date='') |
            models.Q(end_date__isnull=True) | models.Q(end_date='')
        ).iterator():
            try:
                start = datetime.datetime.strptime(membership.start_date, '%Y-%m-%d').date()
                end = datetime.datetime.strptime(membership.end_date, '%Y-%m-%d').date()
                if end < start:
                    invalid_membership_dates += 1
                    if verbose and invalid_membership_dates <= 5:
                        self.stdout.write(
                            f'  - Membership #{membership.id}: '
                            f'end {membership.end_date} < start {membership.start_date}'
                        )
            except ValueError:
                # Invalid date format (partial dates are ok)
                pass

        if invalid_membership_dates > 0:
            issues += invalid_membership_dates
            self.stdout.write(self.style.WARNING(
                f'⚠ {invalid_membership_dates} memberships with end_date < start_date'
            ))

        # Consultancies with end_date < start_date
        invalid_consultancy_dates = 0
        for consultancy in Consultancy.objects.exclude(
            models.Q(start_date__isnull=True) | models.Q(start_date='') |
            models.Q(end_date__isnull=True) | models.Q(end_date='')
        ).iterator():
            try:
                start = datetime.datetime.strptime(consultancy.start_date, '%Y-%m-%d').date()
                end = datetime.datetime.strptime(consultancy.end_date, '%Y-%m-%d').date()
                if end < start:
                    invalid_consultancy_dates += 1
                    if verbose and invalid_consultancy_dates <= 5:
                        self.stdout.write(
                            f'  - Consultancy #{consultancy.id}: '
                            f'end {consultancy.end_date} < start {consultancy.start_date}'
                        )
            except ValueError:
                pass

        if invalid_consultancy_dates > 0:
            issues += invalid_consultancy_dates
            self.stdout.write(self.style.WARNING(
                f'⚠ {invalid_consultancy_dates} consultancies with end_date < start_date'
            ))

        # Overlapping party memberships (same person, different parties, overlapping dates)
        overlapping_party_memberships = 0
        for person in Person.objects.filter(party_memberships__isnull=False).distinct():
            memberships = list(person.party_memberships.order_by('start_date'))
            for i, m1 in enumerate(memberships):
                for m2 in memberships[i+1:]:
                    try:
                        m1_start = datetime.datetime.strptime(m1.start_date, '%Y-%m-%d').date()
                        m1_end = datetime.datetime.strptime(m1.end_date, '%Y-%m-%d').date() if m1.end_date else datetime.date.max
                        m2_start = datetime.datetime.strptime(m2.start_date, '%Y-%m-%d').date()
                        m2_end = datetime.datetime.strptime(m2.end_date, '%Y-%m-%d').date() if m2.end_date else datetime.date.max

                        if m1_start <= m2_end and m2_start <= m1_end and m1.party_id != m2.party_id:
                            overlapping_party_memberships += 1
                            if verbose and overlapping_party_memberships <= 5:
                                self.stdout.write(
                                    f'  - {person.name}: {m1.party.name} ({m1.start_date}–{m1.end_date or "present"}) '
                                    f'overlaps {m2.party.name} ({m2.start_date}–{m2.end_date or "present"})'
                                )
                    except (ValueError, AttributeError):
                        pass

        if overlapping_party_memberships > 0:
            issues += overlapping_party_memberships
            self.stdout.write(self.style.WARNING(
                f'⚠ {overlapping_party_memberships} overlapping party memberships'
            ))

        if issues == 0:
            self.stdout.write(self.style.SUCCESS('✓ No temporal consistency issues found'))

        return issues

"""
Management command to clean up lobby employee data quality issues.

Issues addressed:
1. Duplicate membership records (same person-org pairs)
2. Garbage person names (roles parsed as names)
3. Agency name variations (optional merge)

Usage:
    python manage.py cleanup_lobby_employees --dry-run  # Preview changes
    python manage.py cleanup_lobby_employees            # Execute cleanup
    python manage.py cleanup_lobby_employees --merge-agencies  # Also merge duplicate agencies
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count, Min
from datafetch import models


# Known garbage names that are roles/placeholders, not actual people
GARBAGE_NAMES = [
    'Client',
    'Pro',
    'Relevant Roles',
    'Bono Clients',
    'Councillor',
    'Party Officer',
    'Cllr',
    'Director',
    'Partner',
    'Chair',
    'Chairman',
    'Board',
    'Member',
    'Treasurer',
    'Audit',
    'None',
    'Appointment',
    'Candidate',
    'Conservatives',
    'Department',
    'Founder',
    'Freelancer',
    'Media',
    'Political',
    'Trade',
    'Women',
]

# Agency name mappings: variant -> canonical name
# NOTE: Only include TRUE duplicates here (identical records in overlapping time periods)
# Do NOT include company name changes over time - those preserve historical timeline
AGENCY_CANONICAL_MAPPING = {
    # Exact duplicates (punctuation differences, same time periods)
    'Atlas Communications Partners Ltd.': 'Atlas Communications Partners Ltd',  # Both 2019-03 to 2022-08
    'JFG Communications Ltd.': 'JFG Communications Ltd',
    'do Different.': 'do Different',

    # NOTE: The following look like duplicates but are actually COMPANY NAME CHANGES:
    # - becg (2019-03 to 2020-02) -> BECG (2020-03 to 2023-05) - case change with time boundary
    # - 3x1 Group (2019-2025) -> 3x1 (2025+) - rebrand
    # - Public First (2020-2024) -> Public First Limited (2024+) - legal entity change
    # - Stratagem (NI) Ltd (2019-2022) -> Stratagem NI (2023+) - rebrand
    # - Portland (2019-2024) -> Portland Communications (2024+)
    # - MHP Communications -> MHP Group -> MHP Group Limited
    # - Incisive Health -> Evoke Incisive Health (acquisition)
    # - H+K Strategies / Hill and Knowlton (rebrand chain)
    # - Cicero Group -> H/ Advisors Cicero (rebrand chain)
    # - Dentons / DGA / Interel (merger chain)
    # - Hume Brophy -> Penta (rebrand)
}


class Command(BaseCommand):
    help = 'Clean up lobby employee data quality issues (duplicates, garbage names, agency variations)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without modifying database'
        )
        parser.add_argument(
            '--merge-agencies',
            action='store_true',
            help='Also merge duplicate agency names (updates Consultancy records)'
        )
        parser.add_argument(
            '--skip-dedup',
            action='store_true',
            help='Skip membership deduplication'
        )
        parser.add_argument(
            '--skip-garbage',
            action='store_true',
            help='Skip garbage name removal'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.merge_agencies = options['merge_agencies']
        self.skip_dedup = options['skip_dedup']
        self.skip_garbage = options['skip_garbage']

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))

        stats = {
            'memberships_deleted': 0,
            'garbage_memberships_deleted': 0,
            'garbage_persons_deleted': 0,
            'agencies_merged': 0,
            'consultancies_updated': 0,
        }

        # Step 1: Deduplicate memberships
        if not self.skip_dedup:
            stats['memberships_deleted'] = self._deduplicate_memberships()

        # Step 2: Remove garbage names
        if not self.skip_garbage:
            garbage_stats = self._remove_garbage_names()
            stats['garbage_memberships_deleted'] = garbage_stats['memberships']
            stats['garbage_persons_deleted'] = garbage_stats['persons']

        # Step 3: Merge agency duplicates (optional)
        if self.merge_agencies:
            agency_stats = self._merge_agency_duplicates()
            stats['agencies_merged'] = agency_stats['agencies']
            stats['consultancies_updated'] = agency_stats['consultancies']

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('CLEANUP SUMMARY'))
        self.stdout.write('=' * 60)
        self.stdout.write(f"Duplicate memberships removed: {stats['memberships_deleted']}")
        self.stdout.write(f"Garbage memberships removed: {stats['garbage_memberships_deleted']}")
        self.stdout.write(f"Garbage person records removed: {stats['garbage_persons_deleted']}")
        if self.merge_agencies:
            self.stdout.write(f"Agency duplicates merged: {stats['agencies_merged']}")
            self.stdout.write(f"Consultancy records updated: {stats['consultancies_updated']}")

        if self.dry_run:
            self.stdout.write(self.style.WARNING('\nNo changes made (dry run)'))
        else:
            self.stdout.write(self.style.SUCCESS('\nCleanup complete!'))

    def _deduplicate_memberships(self):
        """Remove duplicate membership records, keeping the oldest one per person-org pair."""
        self.stdout.write('\n--- Step 1: Deduplicating Memberships ---')

        # Find lobbying agency IDs
        agency_ids = list(
            models.Consultancy.objects
            .filter(agency_id__isnull=False)
            .values_list('agency_id', flat=True)
            .distinct()
        )

        # Find duplicate person-org pairs
        duplicates = (
            models.Membership.objects
            .filter(organization_id__in=agency_ids)
            .values('person_id', 'organization_id')
            .annotate(
                count=Count('id'),
                min_id=Min('id')
            )
            .filter(count__gt=1)
        )

        dup_count = duplicates.count()
        self.stdout.write(f"Found {dup_count} person-org pairs with duplicates")

        if dup_count == 0:
            return 0

        # Calculate total records to delete
        total_excess = sum(d['count'] - 1 for d in duplicates)
        self.stdout.write(f"Total excess records to delete: {total_excess}")

        if self.dry_run:
            # Show sample
            self.stdout.write("\nSample duplicates:")
            for dup in duplicates[:5]:
                person = models.Actor.objects.filter(id=dup['person_id']).first()
                org = models.Actor.objects.filter(id=dup['organization_id']).first()
                self.stdout.write(
                    f"  - {person.name if person else 'Unknown'} @ "
                    f"{org.name if org else 'Unknown'}: {dup['count']} records"
                )
            return total_excess

        # Delete duplicates (keep min_id)
        deleted_count = 0
        with transaction.atomic():
            for dup in duplicates:
                deleted, _ = (
                    models.Membership.objects
                    .filter(
                        person_id=dup['person_id'],
                        organization_id=dup['organization_id']
                    )
                    .exclude(id=dup['min_id'])
                    .delete()
                )
                deleted_count += deleted

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} duplicate memberships"))
        return deleted_count

    def _remove_garbage_names(self):
        """Remove memberships and person records for garbage names."""
        self.stdout.write('\n--- Step 2: Removing Garbage Names ---')

        # Find person IDs with garbage names
        garbage_persons = models.Person.objects.filter(
            actor_ptr__name__in=GARBAGE_NAMES
        ).values_list('actor_ptr_id', flat=True)

        garbage_count = len(garbage_persons)
        self.stdout.write(f"Found {garbage_count} garbage person records")

        if garbage_count == 0:
            return {'memberships': 0, 'persons': 0}

        # Count affected memberships
        membership_count = models.Membership.objects.filter(
            person_id__in=garbage_persons
        ).count()
        self.stdout.write(f"Affected memberships: {membership_count}")

        if self.dry_run:
            # Show which names
            names = models.Actor.objects.filter(id__in=garbage_persons).values_list('name', flat=True)
            self.stdout.write(f"Garbage names found: {', '.join(names)}")
            return {'memberships': membership_count, 'persons': garbage_count}

        # Delete memberships first (foreign key constraint)
        with transaction.atomic():
            mem_deleted, _ = models.Membership.objects.filter(
                person_id__in=garbage_persons
            ).delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {mem_deleted} garbage memberships"))

            # Delete person records
            person_deleted = 0
            for person_id in garbage_persons:
                try:
                    person = models.Person.objects.get(actor_ptr_id=person_id)
                    person.delete()
                    person_deleted += 1
                except models.Person.DoesNotExist:
                    pass

            self.stdout.write(self.style.SUCCESS(f"Deleted {person_deleted} garbage person records"))

        return {'memberships': mem_deleted, 'persons': person_deleted}

    def _merge_agency_duplicates(self):
        """Update Consultancy records to use canonical agency names."""
        self.stdout.write('\n--- Step 3: Merging Agency Duplicates ---')

        merged_count = 0
        consultancy_count = 0

        for variant_name, canonical_name in AGENCY_CANONICAL_MAPPING.items():
            # Find the variant agency
            variant = models.Organization.objects.filter(
                actor_ptr__name=variant_name
            ).first()

            if not variant:
                continue

            # Find or create canonical agency
            canonical = models.Organization.objects.filter(
                actor_ptr__name=canonical_name
            ).first()

            if not canonical:
                self.stdout.write(f"  Warning: Canonical agency '{canonical_name}' not found, skipping")
                continue

            # Count consultancies to update
            consultancies_to_update = models.Consultancy.objects.filter(
                agency_id=variant.actor_ptr_id
            ).count()

            if consultancies_to_update == 0:
                continue

            self.stdout.write(
                f"  {variant_name} -> {canonical_name}: "
                f"{consultancies_to_update} consultancies"
            )

            if self.dry_run:
                merged_count += 1
                consultancy_count += consultancies_to_update
                continue

            # Update consultancies to use canonical agency
            with transaction.atomic():
                updated = models.Consultancy.objects.filter(
                    agency_id=variant.actor_ptr_id
                ).update(canonical_agency_id=canonical.actor_ptr_id)

                consultancy_count += updated
                merged_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Merged {merged_count} agency variants, updated {consultancy_count} consultancies"
        ))
        return {'agencies': merged_count, 'consultancies': consultancy_count}

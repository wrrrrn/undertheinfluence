#!/usr/bin/env python
"""
Detailed investigation of data quality issues.

This script provides in-depth analysis of each data quality issue category
to help understand root causes and inform remediation strategies.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'undertheinfluence.settings')
django.setup()

from django.db import models
from django.db.models import Count, Q
from datafetch.models import Person, Organization, Donation, Membership
from collections import Counter


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def investigate_orphaned_donations():
    print_header("1. ORPHANED DONATIONS (637 with null donor)")

    orphaned = Donation.objects.filter(donor__isnull=True)
    total = orphaned.count()

    print(f"\nTotal orphaned donations: {total}")

    # Sample some examples
    print("\nSample orphaned donations:")
    for donation in orphaned[:10]:
        print(f"  ID {donation.id}: recipient={donation.recipient}, "
              f"value=£{donation.value}, date={donation.received_date}")

    # Check if they have canonical_donor set (entity resolution)
    with_canonical = orphaned.filter(canonical_donor__isnull=False).count()
    print(f"\nOrphaned with canonical_donor set: {with_canonical}")

    if with_canonical > 0:
        print("Sample with canonical_donor:")
        for donation in orphaned.filter(canonical_donor__isnull=False)[:5]:
            print(f"  ID {donation.id}: canonical_donor={donation.canonical_donor.name}")

    # Value distribution
    zero_value = orphaned.filter(value=0).count()
    print(f"\nOrphaned with zero value: {zero_value}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - If canonical_donor is set, consider restoring donor = canonical_donor")
    print("   - Otherwise, these should likely be deleted as incomplete records")


def investigate_duplicate_persons():
    print_header("2. DUPLICATE PERSON NAMES (134 names)")

    duplicates = (
        Person.objects
        .values('name')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .order_by('-count')
    )

    print(f"\nTotal duplicate names: {duplicates.count()}")
    print("\nTop 10 most duplicated names:")

    for i, dup in enumerate(duplicates[:10], 1):
        name = dup['name']
        count = dup['count']
        persons = Person.objects.filter(name=name)

        print(f"\n{i}. '{name}' ({count} instances)")

        # Check if they have different identifiers
        identifiers = set()
        for p in persons:
            ids = p.identifiers.values_list('identifier', flat=True)
            identifiers.update(ids)

        print(f"   Identifiers: {len(identifiers)} unique")

        # Check birth dates
        birth_dates = persons.exclude(birth_date='').values_list('birth_date', flat=True).distinct()
        print(f"   Birth dates: {list(birth_dates)[:3]}")

        # Check if they have different IDs/sources
        sample_persons = persons[:3]
        for p in sample_persons:
            print(f"   - ID {p.id}: identifiers={p.identifiers.count()}, "
                  f"memberships={p.memberships.count()}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - Use entity resolution (Phase 3.1) to merge duplicates")
    print("   - Check identifiers to determine if truly duplicates or distinct persons")
    print("   - Run: python manage.py resolve_duplicates")


def investigate_duplicate_donations():
    print_header("3. DUPLICATE DONATIONS (25,539 potentially duplicate)")

    duplicates = (
        Donation.objects
        .values('donor', 'recipient', 'value', 'received_date')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .order_by('-count')
    )

    print(f"\nTotal duplicate donation groups: {duplicates.count()}")

    # Analyze duplication patterns
    duplication_counts = Counter([d['count'] for d in duplicates])
    print("\nDuplication frequency:")
    for count, freq in sorted(duplication_counts.items(), reverse=True)[:5]:
        print(f"   {count} duplicates: {freq} donation groups")

    print("\nSample duplicate groups:")
    for i, dup in enumerate(duplicates[:5], 1):
        donations = Donation.objects.filter(
            donor_id=dup['donor'],
            recipient_id=dup['recipient'],
            value=dup['value'],
            received_date=dup['received_date']
        )

        print(f"\n{i}. {dup['count']} identical donations: £{dup['value']} on {dup['received_date']}")

        # Check if they have different sources
        sources = set()
        for d in donations:
            if d.source:
                sources.add(d.source)

        print(f"   Sources: {len(sources)} unique")
        print(f"   IDs: {list(donations.values_list('id', flat=True)[:5])}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - These may be from re-running import commands")
    print("   - Implement deduplication in import commands (Phase 3.4 Task #2)")
    print("   - For now, can keep the oldest ID and delete duplicates")


def investigate_zero_value_donations():
    print_header("4. ZERO VALUE DONATIONS (427)")

    zero_donations = Donation.objects.filter(value=0)
    total = zero_donations.count()

    print(f"\nTotal zero-value donations: {total}")

    # Check donation types
    types = zero_donations.values('donation_type').annotate(count=Count('id')).order_by('-count')
    print("\nBy donation type:")
    for t in types[:10]:
        print(f"   {t['donation_type']}: {t['count']}")

    # Check if they have received_date
    with_date = zero_donations.exclude(received_date__isnull=True).count()
    print(f"\nWith received_date: {with_date}/{total}")

    # Sample
    print("\nSample zero-value donations:")
    for d in zero_donations[:5]:
        print(f"   ID {d.id}: {d.donor} → {d.recipient}, type={d.donation_type}, date={d.received_date}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - Check if these are placeholders or data errors")
    print("   - May need to check source data (Electoral Commission)")
    print("   - Consider filtering out zero-value donations from import")


def investigate_invalid_donation_dates():
    print_header("5. INVALID DONATION DATES (76 with accepted < received)")

    invalid = []
    for donation in Donation.objects.filter(
        received_date__isnull=False,
        accepted_date__isnull=False
    ):
        if donation.accepted_date < donation.received_date:
            invalid.append(donation)

    print(f"\nTotal with accepted_date < received_date: {len(invalid)}")

    print("\nSample invalid dates:")
    for d in invalid[:10]:
        diff = (d.received_date - d.accepted_date).days
        print(f"   ID {d.id}: accepted={d.accepted_date}, received={d.received_date} "
              f"(diff: {diff} days)")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - Check source data for these specific donations")
    print("   - May need to swap accepted_date and received_date")
    print("   - Add validation in import commands to prevent this")


def investigate_empty_names():
    print_header("6. EMPTY PERSON NAMES (24,586)")

    empty_names = Person.objects.filter(
        Q(name='') | Q(family_name='') | Q(given_name='')
    )
    total = empty_names.count()

    print(f"\nTotal persons with empty names: {total}")

    # Break down by which field is empty
    empty_name = Person.objects.filter(name='').count()
    empty_family = Person.objects.filter(family_name='').count()
    empty_given = Person.objects.filter(given_name='').count()

    print(f"\nBreakdown:")
    print(f"   Empty name: {empty_name}")
    print(f"   Empty family_name: {empty_family}")
    print(f"   Empty given_name: {empty_given}")

    # Check if they have identifiers (might be imported from systems that don't require names)
    with_identifiers = empty_names.filter(identifiers__isnull=False).distinct().count()
    print(f"\nWith identifiers: {with_identifiers}")

    # Check if they have any relationships
    with_memberships = empty_names.filter(memberships__isnull=False).distinct().count()
    with_donations = empty_names.filter(
        Q(donated_to__isnull=False) | Q(received_donations_from__isnull=False)
    ).distinct().count()

    print(f"With memberships: {with_memberships}")
    print(f"With donations: {with_donations}")

    # Sample
    print("\nSample persons with empty names:")
    for p in empty_names[:5]:
        print(f"   ID {p.id}: name='{p.name}', family='{p.family_name}', given='{p.given_name}'")
        print(f"      identifiers={p.identifiers.count()}, memberships={p.memberships.count()}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - These are likely Organizations misclassified as Person")
    print("   - Check if they should be Organization records instead")
    print("   - Add validation in import to prevent Person records without names")
    print("   - Can delete if no relationships, or convert to Organization type")


def investigate_missing_membership_dates():
    print_header("7. MEMBERSHIPS MISSING START_DATE (116,542)")

    missing = Membership.objects.filter(Q(start_date__isnull=True) | Q(start_date=''))
    total = missing.count()

    print(f"\nTotal memberships missing start_date: {total}")
    print(f"Total memberships: {Membership.objects.count()}")
    print(f"Percentage missing: {total / Membership.objects.count() * 100:.1f}%")

    # Check if they have other date fields
    with_end_date = missing.exclude(Q(end_date__isnull=True) | Q(end_date='')).count()
    print(f"\nWith end_date but no start_date: {with_end_date} (unusual)")

    # Check organization types
    org_types = (
        missing
        .values('organization__classification')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    print("\nBy organization type:")
    for org_type in org_types[:10]:
        print(f"   {org_type['organization__classification']}: {org_type['count']}")

    # Sample
    print("\nSample memberships without start_date:")
    for m in missing[:5]:
        print(f"   ID {m.id}: {m.person} @ {m.organization}, role={m.role}, "
              f"end_date={m.end_date}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - This is the biggest data quality issue")
    print("   - Check which import command created these (likely ParlParse)")
    print("   - Add start_date inference logic based on context")
    print("   - For existing data, could use organization founding_date or first recorded activity")


def investigate_invalid_membership_dates():
    print_header("8. INVALID MEMBERSHIP DATES (26 with end < start)")

    import datetime

    invalid = []
    for membership in Membership.objects.exclude(
        Q(start_date__isnull=True) | Q(start_date='') |
        Q(end_date__isnull=True) | Q(end_date='')
    ):
        try:
            start = datetime.datetime.strptime(membership.start_date, '%Y-%m-%d').date()
            end = datetime.datetime.strptime(membership.end_date, '%Y-%m-%d').date()
            if end < start:
                invalid.append(membership)
        except ValueError:
            # Partial dates
            pass

    print(f"\nTotal memberships with end_date < start_date: {len(invalid)}")

    print("\nAll invalid memberships:")
    for m in invalid:
        print(f"   ID {m.id}: {m.person.name} @ {m.organization.name}")
        print(f"      start={m.start_date}, end={m.end_date}, role={m.role}")
        if m.post:
            print(f"      post={m.post.label}")

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   - Manually review and correct these 26 memberships")
    print("   - Check source data to determine correct dates")
    print("   - May need to swap start_date and end_date")


def main():
    print("\n" + "=" * 80)
    print("  DATA QUALITY INVESTIGATION REPORT")
    print("=" * 80)
    print("\nThis report provides detailed analysis of each data quality issue")
    print("category to inform remediation strategies.")

    investigate_orphaned_donations()
    investigate_duplicate_persons()
    investigate_duplicate_donations()
    investigate_zero_value_donations()
    investigate_invalid_donation_dates()
    investigate_empty_names()
    investigate_missing_membership_dates()
    investigate_invalid_membership_dates()

    print("\n" + "=" * 80)
    print("  SUMMARY OF RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. ORPHANED DONATIONS (637):
   → Restore donor from canonical_donor or delete incomplete records

2. DUPLICATE PERSONS (134):
   → Use entity resolution system (resolve_duplicates command)

3. DUPLICATE DONATIONS (25,539):
   → Implement deduplication in import commands
   → Delete duplicates keeping oldest record

4. ZERO VALUE DONATIONS (427):
   → Review source data, consider filtering from imports

5. INVALID DONATION DATES (76):
   → Manual review and correction, add import validation

6. EMPTY PERSON NAMES (24,586):
   → Convert to Organization records or delete if no relationships

7. MISSING MEMBERSHIP START_DATE (116,542):
   → Infer from context, fix import commands

8. INVALID MEMBERSHIP DATES (26):
   → Manual review and correction
    """)


if __name__ == '__main__':
    main()

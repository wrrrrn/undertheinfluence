"""
Integration tests for populate_canonical management command.

Tests the bootstrap command that backfills canonical_* fields
using EntityResolutionService.
"""

import pytest
from decimal import Decimal
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

from datafetch.models import (
    Person, Organization, Donation, MeetingAttendee,
    MinisterialMeeting, Consultancy,
)


@pytest.mark.django_db
class TestPopulateCanonicalCommand:
    """Tests for populate_canonical management command."""

    @pytest.fixture
    def minister(self, db):
        """Create a minister for meetings."""
        return Person.objects.create(
            name="John Smith MP",
            family_name="Smith",
            given_name="John"
        )

    @pytest.fixture
    def department(self, db):
        """Create a department for meetings."""
        return Organization.objects.create(
            name="Department for Testing",
            classification="Government Department"
        )

    @pytest.fixture
    def canonical_org(self, db):
        """Create a canonical organization with relationships."""
        org = Organization.objects.create(
            name="Tech Corp",
            classification="Company"
        )
        # Add donation to make it canonical
        recipient = Organization.objects.create(
            name="Political Party",
            classification="Political Party"
        )
        Donation.objects.create(
            donor=org,
            recipient=recipient,
            value=Decimal("10000.00"),
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False
        )
        return org

    @pytest.fixture
    def meeting_with_attendee(self, db, minister, department, canonical_org):
        """Create a meeting with an attendee that matches canonical org."""
        # Create a duplicate org for the meeting
        duplicate_org = Organization.objects.create(
            name="Tech Corp",  # Same name as canonical
            classification="Company"
        )

        meeting = MinisterialMeeting.objects.create(
            minister=minister,
            department=department,
            meeting_date="2024-01-15",
            purpose="Discuss policy",
            organisation_met_raw="Tech Corp"
        )

        attendee = MeetingAttendee.objects.create(
            meeting=meeting,
            actor=duplicate_org,
            actor_name_raw="Tech Corp"
        )

        return meeting, attendee, duplicate_org

    def test_dry_run_no_changes(self, db, meeting_with_attendee):
        """Dry run should not modify database."""
        meeting, attendee, _ = meeting_with_attendee

        out = StringIO()
        call_command('populate_canonical', '--dry-run', stdout=out)

        # Refresh from DB
        attendee.refresh_from_db()
        assert attendee.canonical_actor_id is None

    def test_resolves_meeting_attendees(self, db, meeting_with_attendee, canonical_org):
        """Command should link meeting attendees to canonical actors."""
        meeting, attendee, _ = meeting_with_attendee

        out = StringIO()
        call_command('populate_canonical', '--dataset', 'meetings', stdout=out)

        # Refresh from DB
        attendee.refresh_from_db()
        # Should be linked to canonical org (has more data)
        assert attendee.canonical_actor_id == canonical_org.pk

    def test_dataset_filter_meetings(self, db, meeting_with_attendee):
        """--dataset meetings should only process meeting attendees."""
        meeting, attendee, _ = meeting_with_attendee

        # Create a donation that shouldn't be touched
        donor = Organization.objects.create(
            name="Donor Corp",
            classification="Company"
        )
        recipient = Organization.objects.create(
            name="Recipient Party",
            classification="Political Party"
        )
        donation = Donation.objects.create(
            donor=donor,
            recipient=recipient,
            value=Decimal("5000.00"),
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False
        )

        out = StringIO()
        call_command('populate_canonical', '--dataset', 'meetings', stdout=out)

        # Donation should not be touched
        donation.refresh_from_db()
        assert donation.canonical_donor_id is None

    def test_batch_size_option(self, db, minister, department):
        """--batch-size should control processing batch size."""
        # Create multiple meetings
        for i in range(10):
            org = Organization.objects.create(
                name=f"Org {i}",
                classification="Company"
            )
            meeting = MinisterialMeeting.objects.create(
                minister=minister,
                department=department,
                meeting_date="2024-01-15",
                purpose=f"Meeting {i}",
                organisation_met_raw=f"Org {i}"
            )
            MeetingAttendee.objects.create(
                meeting=meeting,
                actor=org,
                actor_name_raw=f"Org {i}"
            )

        out = StringIO()
        # Should complete without error with small batch size
        call_command(
            'populate_canonical',
            '--dataset', 'meetings',
            '--batch-size', '2',
            stdout=out
        )

        output = out.getvalue()
        assert 'complete' in output.lower() or 'processed' in output.lower()

    def test_output_shows_progress(self, db, meeting_with_attendee):
        """Command output should show progress information."""
        meeting, attendee, _ = meeting_with_attendee

        out = StringIO()
        call_command('populate_canonical', '--dry-run', stdout=out)

        output = out.getvalue()
        # Should show some progress or summary
        assert len(output) > 0


@pytest.mark.django_db
class TestPopulateCanonicalDonations:
    """Tests for donation canonical population."""

    @pytest.fixture
    def canonical_donor(self, db):
        """Create a canonical donor with rich data."""
        donor = Organization.objects.create(
            name="Major Donor Corp",
            classification="Company"
        )
        recipient = Organization.objects.create(
            name="Labour Party",
            classification="Political Party"
        )
        # Add multiple donations to establish as canonical
        for i in range(5):
            Donation.objects.create(
                donor=donor,
                recipient=recipient,
                value=Decimal(f"{(i+1) * 10000}.00"),
                donation_type="Cash",
                accounting_units_as_central_party=False,
                is_bequest=False,
                is_aggregation=False,
                is_sponsorship=False
            )
        return donor

    @pytest.fixture
    def duplicate_donor_donations(self, db, canonical_donor):
        """Create donations from a duplicate donor."""
        duplicate = Organization.objects.create(
            name="Major Donor Corp",  # Same name
            classification="Company"
        )
        recipient = Organization.objects.create(
            name="Conservative Party",
            classification="Political Party"
        )
        donation = Donation.objects.create(
            donor=duplicate,
            recipient=recipient,
            value=Decimal("5000.00"),
            donation_type="Cash",
            accounting_units_as_central_party=False,
            is_bequest=False,
            is_aggregation=False,
            is_sponsorship=False
        )
        return donation, duplicate

    def test_resolves_donation_donors(self, db, canonical_donor, duplicate_donor_donations):
        """Command should link duplicate donors to canonical."""
        donation, duplicate = duplicate_donor_donations

        out = StringIO()
        call_command('populate_canonical', '--dataset', 'donations', stdout=out)

        # Refresh from DB
        donation.refresh_from_db()
        # Should be linked to canonical donor (has more data)
        assert donation.canonical_donor_id == canonical_donor.pk

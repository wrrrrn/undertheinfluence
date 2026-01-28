"""
Apply Approved Entity Resolutions

Applies approved ActorResolution records by setting canonical_actor
fields on MeetingAttendee records.

Never modifies original data - only sets the canonical pointer.

Phase 3: Entity Resolution
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from datafetch import models
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Apply approved entity resolutions to meeting attendee records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto-approve-threshold',
            type=float,
            help='Auto-approve resolutions with confidence >= this value before applying'
        )
        parser.add_argument(
            '--resolution-id',
            type=int,
            help='Apply specific resolution by ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        auto_approve_threshold = options.get('auto_approve_threshold')
        resolution_id = options.get('resolution_id')
        dry_run = options.get('dry_run', False)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Apply Entity Resolutions")
        self.stdout.write(f"{'='*60}\n")

        # Get approved resolutions
        if resolution_id:
            resolutions = models.ActorResolution.objects.filter(id=resolution_id)
            if not resolutions.exists():
                self.stderr.write(f"Resolution {resolution_id} not found")
                return
        else:
            # Auto-approve if threshold provided
            if auto_approve_threshold:
                pending = models.ActorResolution.objects.filter(
                    review_status='pending',
                    confidence__gte=auto_approve_threshold
                )

                if pending.exists():
                    self.stdout.write(f"Auto-approving {pending.count()} resolutions >= {auto_approve_threshold} confidence...")

                    if not dry_run:
                        pending.update(
                            review_status='approved',
                            decision='auto_merge'
                        )

            # Get all approved resolutions
            resolutions = models.ActorResolution.objects.filter(
                review_status='approved'
            ).exclude(
                decision='ignore'
            )

        total_resolutions = resolutions.count()

        if total_resolutions == 0:
            self.stdout.write(self.style.WARNING("No approved resolutions to apply"))
            return

        self.stdout.write(f"Applying {total_resolutions} approved resolutions...\n")

        # Statistics
        stats = {
            'resolutions_applied': 0,
            'attendees_updated': 0,
            'meetings_affected': 0,
        }

        for resolution in resolutions:
            self.stdout.write(
                f"  Applying: {resolution.actor1.name} ← {resolution.actor2.name} "
                f"(confidence: {resolution.confidence:.2f}, {resolution.match_reason})"
            )

            # Find all meeting attendees with either actor
            attendees = models.MeetingAttendee.objects.filter(
                Q(actor=resolution.actor1) | Q(actor=resolution.actor2)
            )

            attendee_count = attendees.count()

            if not dry_run:
                with transaction.atomic():
                    # Update all attendees to point to canonical actor
                    updated = attendees.update(canonical_actor=resolution.canonical_actor)

                    stats['attendees_updated'] += updated
                    stats['resolutions_applied'] += 1

                    # Count affected meetings
                    meetings = models.MinisterialMeeting.objects.filter(
                        attendees__in=attendees
                    ).distinct()
                    stats['meetings_affected'] += meetings.count()

            else:
                self.stdout.write(f"    [DRY RUN] Would update {attendee_count} attendees")
                stats['attendees_updated'] += attendee_count
                stats['resolutions_applied'] += 1

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Application Summary")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✓ Resolutions applied: {stats['resolutions_applied']}"))
        self.stdout.write(f"  Attendee records updated: {stats['attendees_updated']}")

        if not dry_run:
            self.stdout.write(f"  Meetings affected: {stats['meetings_affected']}")
            self.stdout.write("")
            self.stdout.write("Entity resolution complete!")
            self.stdout.write("")
            self.stdout.write("Verify results:")
            self.stdout.write("  python manage.py shell")
            self.stdout.write("  >>> from datafetch.models import MeetingAttendee")
            self.stdout.write("  >>> MeetingAttendee.objects.filter(canonical_actor__isnull=False).count()")
        else:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made to database"))

        self.stdout.write("")

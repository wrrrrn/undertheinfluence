from django.core.management.base import BaseCommand
from django.db import transaction
from datafetch import models
from datafetch.utils.entity_matcher import EntityMatcher


class Command(BaseCommand):
    help = 'Populate MeetingAttendee records from existing MinisterialMeeting data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Delete existing attendees and recreate from scratch'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        refresh = options.get('refresh', False)

        if refresh and not dry_run:
            count = models.MeetingAttendee.objects.count()
            models.MeetingAttendee.objects.all().delete()
            self.stdout.write(f"Deleted {count} existing attendees")

        # Get all meetings
        meetings = models.MinisterialMeeting.objects.all()
        total_meetings = meetings.count()

        self.stdout.write(f"Processing {total_meetings} meetings...")

        # Statistics
        stats = {
            'one_on_one': 0,
            'roundtable': 0,
            'attendees_created': 0,
            'attendees_skipped': 0,
            'errors': 0,
        }

        matcher = EntityMatcher()

        for meeting in meetings:
            try:
                with transaction.atomic():
                    # Check if external_actor_name_raw contains comma (roundtable)
                    if ',' in meeting.external_actor_name_raw:
                        # Roundtable meeting
                        stats['roundtable'] += 1

                        if not dry_run:
                            meeting.is_roundtable = True
                            meeting.save(update_fields=['is_roundtable'])

                        # Split by comma and create attendee for each
                        attendee_names = [
                            name.strip()
                            for name in meeting.external_actor_name_raw.split(',')
                            if name.strip()
                        ]

                        if dry_run:
                            self.stdout.write(
                                f"[DRY RUN] Would split '{meeting.external_actor_name_raw}' "
                                f"into {len(attendee_names)} attendees"
                            )
                        else:
                            for attendee_name in attendee_names:
                                # Match or create actor
                                actor = matcher.match_external_actor(
                                    attendee_name,
                                    create_if_missing=True
                                )

                                # Create MeetingAttendee
                                attendee, created = models.MeetingAttendee.objects.get_or_create(
                                    meeting=meeting,
                                    actor_name_raw=attendee_name,
                                    defaults={
                                        'actor': actor,
                                        'canonical_actor': None,  # Phase 3
                                    }
                                )

                                if created:
                                    stats['attendees_created'] += 1
                                else:
                                    stats['attendees_skipped'] += 1

                    else:
                        # One-on-one meeting
                        stats['one_on_one'] += 1

                        if not dry_run:
                            meeting.is_roundtable = False
                            meeting.save(update_fields=['is_roundtable'])

                        # Create single attendee matching external_actor
                        if dry_run:
                            self.stdout.write(
                                f"[DRY RUN] Would create 1 attendee for '{meeting.external_actor_name_raw}'"
                            )
                        else:
                            # Use existing external_actor if available
                            actor = meeting.external_actor
                            if not actor:
                                actor = matcher.match_external_actor(
                                    meeting.external_actor_name_raw,
                                    create_if_missing=True
                                )

                            attendee, created = models.MeetingAttendee.objects.get_or_create(
                                meeting=meeting,
                                actor_name_raw=meeting.external_actor_name_raw,
                                defaults={
                                    'actor': actor,
                                    'canonical_actor': None,  # Phase 3
                                }
                            )

                            if created:
                                stats['attendees_created'] += 1
                            else:
                                stats['attendees_skipped'] += 1

            except Exception as e:
                stats['errors'] += 1
                self.stderr.write(
                    f"Error processing meeting {meeting.id} "
                    f"({meeting.minister.name} on {meeting.meeting_date}): {e}"
                )

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total meetings processed: {total_meetings}")
        self.stdout.write(f"  One-on-one meetings: {stats['one_on_one']}")
        self.stdout.write(f"  Roundtable meetings: {stats['roundtable']}")
        self.stdout.write(f"\nAttendees created: {stats['attendees_created']}")
        self.stdout.write(f"Attendees skipped (already exist): {stats['attendees_skipped']}")
        self.stdout.write(f"Errors: {stats['errors']}")

        if not dry_run:
            # Verify counts
            total_attendees = models.MeetingAttendee.objects.count()
            self.stdout.write(f"\nTotal attendees in database: {total_attendees}")

            # Show roundtable statistics
            avg_attendees = models.MeetingAttendee.objects.filter(
                meeting__is_roundtable=True
            ).values('meeting').distinct().count()

            if stats['roundtable'] > 0:
                roundtable_attendees = models.MeetingAttendee.objects.filter(
                    meeting__is_roundtable=True
                ).count()
                avg = roundtable_attendees / stats['roundtable']
                self.stdout.write(
                    f"Average attendees per roundtable: {avg:.1f}"
                )
        else:
            self.stdout.write("\n[DRY RUN] No changes made to database")

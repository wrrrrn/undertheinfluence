from django.core.management.base import BaseCommand
from django.db import transaction
from datafetch import models
from datafetch.utils.entity_matcher import EntityMatcher
from datafetch.services.entity_resolution import EntityResolutionService
from datafetch.utils.data_cleanup import (
    NameSplitter,
    ActorClassifier,
    EventDescriptionParser,
)
import logging

logger = logging.getLogger(__name__)


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

        # Initialize entity resolution service
        entity_resolver = EntityResolutionService()

        for meeting in meetings:
            try:
                with transaction.atomic():
                    raw_org = meeting.organisation_met_raw

                    # Check if this is an event description, not an organization
                    if EventDescriptionParser.is_event_description(raw_org):
                        # Try to extract actual attendees
                        extracted = EventDescriptionParser.extract_attendees(raw_org)
                        if extracted:
                            attendee_names = extracted
                        else:
                            # Move description to purpose if empty
                            if not dry_run:
                                if not meeting.purpose or meeting.purpose == 'Not specified':
                                    meeting.purpose = raw_org
                                    meeting.save(update_fields=['purpose'])
                            stats['one_on_one'] += 1  # Count as processed
                            continue  # Skip creating garbage actor
                    else:
                        # Use NameSplitter for robust delimiter detection
                        # Handles: semicolons, " and ", " / ", commas
                        attendee_names = NameSplitter.split_attendee_list(raw_org)

                    # Determine if roundtable
                    is_roundtable = len(attendee_names) > 1
                    if is_roundtable:
                        stats['roundtable'] += 1
                    else:
                        stats['one_on_one'] += 1

                    if not dry_run:
                        meeting.is_roundtable = is_roundtable
                        meeting.save(update_fields=['is_roundtable'])

                    if dry_run:
                        if is_roundtable:
                            self.stdout.write(
                                f"[DRY RUN] Would split '{raw_org}' "
                                f"into {len(attendee_names)} attendees"
                            )
                        else:
                            self.stdout.write(
                                f"[DRY RUN] Would create 1 attendee for '{raw_org}'"
                            )
                    else:
                        for attendee_name in attendee_names:
                            attendee_name = attendee_name.strip()
                            if not attendee_name:
                                continue

                            # Skip event descriptions that slipped through
                            if EventDescriptionParser.is_event_description(attendee_name):
                                logger.debug(f"Skipping event description: {attendee_name}")
                                continue

                            # Determine Person vs Organization
                            actor_type = ActorClassifier.classify(attendee_name)

                            if actor_type == 'person' or ActorClassifier.has_person_title(attendee_name):
                                # Create/match as Person
                                actor = self._get_or_create_person(attendee_name, matcher)
                            else:
                                # Create/match as Organization
                                actor = matcher.match_external_actor(
                                    attendee_name,
                                    create_if_missing=True
                                )

                            if not actor:
                                logger.warning(f"Could not create actor: {attendee_name}")
                                continue

                            # Create MeetingAttendee
                            attendee, created = models.MeetingAttendee.objects.get_or_create(
                                meeting=meeting,
                                actor_name_raw=attendee_name,
                                defaults={
                                    'actor': actor,
                                    'canonical_actor': None,
                                }
                            )

                            if created:
                                stats['attendees_created'] += 1
                                # Run entity resolution
                                entity_resolver.resolve_and_link(attendee, 'canonical_actor_id')
                            else:
                                stats['attendees_skipped'] += 1

            except Exception as e:
                stats['errors'] += 1
                self.stderr.write(
                    f"Error processing meeting {meeting.id} "
                    f"({meeting.minister.name} on {meeting.meeting_date}): {e}"
                )

    def _get_or_create_person(self, name, matcher):
        """Get or create a Person actor."""
        from datafetch.helpers import parse_name

        # Try to find existing
        existing = models.Person.objects.filter(name__iexact=name).first()
        if existing:
            return existing

        # Try via matcher
        existing_actor = matcher.match_external_actor(name, create_if_missing=False)
        if existing_actor and hasattr(existing_actor, 'person'):
            return existing_actor

        # Create new Person
        person = models.Person.objects.create(name=name)

        try:
            _, person_dict = parse_name(name)
            for key, value in person_dict.items():
                if hasattr(person, key) and value:
                    setattr(person, key, value)
            person.save()
        except Exception as e:
            logger.warning(f"Could not parse person name '{name}': {e}")

        return person

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

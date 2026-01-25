"""
Import UK Ministerial Meetings Data

Phase 2: CSV/XLSX parsing + Auto-discovery and bulk import (web scraping)

Data source: GOV.UK ministerial transparency publications
Format: CSV and XLSX files
Coverage: 2010-present across 32+ government departments

Usage:
    # Manual: Import from local file
    python manage.py import_ministerial_meetings --file data/sample.csv --department DSIT --quarter 2024-Q1

    # Manual: Import from URL
    python manage.py import_ministerial_meetings --url https://... --department DSIT --quarter 2024-Q1

    # Bulk: Auto-discover and import all publications for one department
    python manage.py import_ministerial_meetings --department DSIT --auto --since 2020

    # Bulk: Auto-discover and import ALL departments
    python manage.py import_ministerial_meetings --auto --since 2020

    # Dry run (preview without saving)
    python manage.py import_ministerial_meetings --file data/sample.csv --department DSIT --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import logging

from datafetch import models, helpers
from datafetch.services.ministerial_meetings_parser import MinisterialMeetingsParser
from datafetch.services.gov_uk_scraper import GovUkScraper
from datafetch.services.entity_resolution import EntityResolutionService
from datafetch.utils.entity_matcher import EntityMatcher
from datafetch.utils.data_cleanup import (
    NameSplitter,
    ActorClassifier,
    EventDescriptionParser,
)
from datafetch.utils.normalization import normalize_actor_name
from datafetch.management.commands.department_config import DEPARTMENTS, get_department_by_name

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import ministerial meetings from GOV.UK transparency publications'

    def add_arguments(self, parser):
        # Manual mode arguments
        parser.add_argument(
            '--file',
            help='Local CSV/XLSX file path'
        )
        parser.add_argument(
            '--url',
            help='CSV/XLSX URL to fetch'
        )
        parser.add_argument(
            '--department',
            help='Department short name (DSIT, DfT, HO, etc.). Required unless using --auto for all departments.'
        )
        parser.add_argument(
            '--quarter',
            help='Quarter label (e.g., 2024-Q1) for source tracking'
        )

        # Bulk mode arguments
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Auto-discover and import all publications (uses web scraping)'
        )
        parser.add_argument(
            '--since',
            type=int,
            help='Only import publications from this year onwards (e.g., 2020)'
        )

        # Common arguments
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Refresh cached files'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate without saving to database'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )

    def handle(self, *args, **options):
        # Configure logging
        if options.get('verbose'):
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Check if auto mode or manual mode
        if options.get('auto'):
            self._bulk_import(options)
        else:
            self._manual_import(options)

    def _extract_year_from_quarter(self, quarter: str) -> int:
        """
        Extract year from quarter string.

        Args:
            quarter: Quarter string like "2016-Q2", "Q1 2024", "2024-Q1", etc.

        Returns:
            Year as integer, or None if not found
        """
        import re
        if not quarter:
            return None

        # Try to find a 4-digit year
        match = re.search(r'(20\d{2})', quarter)
        if match:
            return int(match.group(1))

        return None

    def _manual_import(self, options):
        """Manual import mode: single file or URL"""

        dept_code = options.get('department')
        if not dept_code:
            raise CommandError("--department is required for manual import mode")

        dry_run = options.get('dry_run', False)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Importing Ministerial Meetings: {dept_code}")
        self.stdout.write(f"{'='*60}\n")

        # Get department config
        dept_config = get_department_by_name(dept_code)
        if not dept_config:
            raise CommandError(
                f"Unknown department: {dept_code}\n"
                f"Available departments: {', '.join(sorted(DEPARTMENTS.keys()))}"
            )

        self.stdout.write(f"Department: {dept_config.name}")

        # Get or create department Organization
        department, created = models.Organization.objects.get_or_create(
            name=dept_config.name,
            defaults={
                'classification': 'Government Department',
                'founding_date': dept_config.start_date or '',
                'dissolution_date': dept_config.end_date or '',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created department organization: {department.name}"))

        # Get file
        if options.get('file'):
            filepath = options['file']
            self.stdout.write(f"Reading from local file: {filepath}")
        elif options.get('url'):
            url = options['url']
            filename = url.split('/')[-1]

            # Ensure data directory exists
            helpers.create_data_folder(f'ministerial_meetings/{dept_code}')

            self.stdout.write(f"Fetching from URL: {url}")
            filepath = helpers.fetch_file(
                url,
                filename,
                path=f'ministerial_meetings/{dept_code}',
                refresh=options.get('refresh', False)
            )
            self.stdout.write(f"Cached to: {filepath}")
        else:
            raise CommandError("Must provide either --file or --url")

        # Parse file (auto-detects CSV or XLSX)
        file_ext = filepath.split('.')[-1].upper()
        self.stdout.write(f"\nParsing {file_ext} file...")
        parser = MinisterialMeetingsParser()

        # Extract year from quarter if provided (e.g., "2016-Q2" or "Q1 2024")
        quarter = options.get('quarter', '')
        year = self._extract_year_from_quarter(quarter)

        meetings = parser.parse_file(filepath, year=year)
        self.stdout.write(self.style.SUCCESS(f"✓ Found {len(meetings)} meetings in file"))

        if len(meetings) == 0:
            self.stdout.write(self.style.WARNING("No valid meetings found. Exiting."))
            return

        # Preview first few meetings
        self.stdout.write(f"\nPreview (first 3 meetings):")
        for i, meeting in enumerate(meetings[:3], 1):
            self.stdout.write(
                f"  {i}. {meeting['minister']} met {meeting['external_actor']} "
                f"on {meeting['date']}"
            )
        if len(meetings) > 3:
            self.stdout.write(f"  ... and {len(meetings) - 3} more")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN MODE] Skipping database import"))
            return

        # Import meetings
        self.stdout.write(f"\nImporting to database...")
        self._import_meetings(meetings, department, options)

    def _import_meetings(self, meetings, department, options):
        """Import meetings to database with entity matching."""

        matcher = EntityMatcher()

        created_count = 0
        skipped_count = 0
        duplicate_count = 0
        unmatched_ministers = set()

        source_url = options.get('url', '')
        source_quarter = options.get('quarter', '')

        # Use transaction for atomicity
        with transaction.atomic():
            for meeting_data in meetings:
                # Match minister
                minister = matcher.match_minister(meeting_data['minister'])
                if not minister:
                    unmatched_ministers.add(meeting_data['minister'])
                    skipped_count += 1
                    continue

                # Create meeting record
                # Note: organisation_met_raw preserves the exact text from the CSV
                # MeetingAttendee records (created below) handle entity resolution
                meeting_dict = {
                    'minister': minister,
                    'department': department,
                    'meeting_date': meeting_data['date'],
                    'purpose': meeting_data['purpose'],
                    'organisation_met_raw': meeting_data['external_actor'],
                    'source_url': source_url,
                    'source_quarter': source_quarter,
                }

                try:
                    meeting, created = models.MinisterialMeeting.objects.get_or_create(
                        minister=minister,
                        organisation_met_raw=meeting_data['external_actor'],
                        meeting_date=meeting_data['date'],
                        department=department,
                        defaults=meeting_dict
                    )

                    if created:
                        created_count += 1
                        if created_count % 100 == 0:
                            self.stdout.write(f"  Imported {created_count} meetings...")

                        # Automatically create MeetingAttendee records (Phase 2+)
                        # This makes imports idempotent - attendees are created automatically
                        self._create_meeting_attendees(meeting, matcher)

                    else:
                        duplicate_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error creating meeting for {minister.name} + "
                            f"{meeting_data['external_actor']}: {e}"
                        )
                    )
                    skipped_count += 1

        # Print summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Import Summary")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✓ Created: {created_count} new meetings"))

        if duplicate_count > 0:
            self.stdout.write(f"  Duplicates skipped: {duplicate_count}")

        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠ Skipped: {skipped_count} meetings (minister not found)")
            )

        # Entity matching stats
        self.stdout.write(f"\nEntity Matching Statistics:")
        stats = matcher.get_stats()
        self.stdout.write(f"  Ministers:")
        self.stdout.write(f"    Exact matches: {stats['minister_exact_matches']}")
        self.stdout.write(f"    OtherName matches: {stats['minister_other_name_matches']}")
        self.stdout.write(f"    Normalized matches: {stats['minister_normalized_matches']}")
        self.stdout.write(f"    Not found: {stats['minister_not_found']}")
        self.stdout.write(f"  External Actors:")
        self.stdout.write(f"    Exact matches: {stats['actor_exact_matches']}")
        self.stdout.write(f"    OtherName matches: {stats['actor_other_name_matches']}")
        self.stdout.write(f"    Normalized matches: {stats['actor_normalized_matches']}")
        self.stdout.write(f"    Created new: {stats['actor_created']}")

        # Unmatched ministers
        if unmatched_ministers:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.WARNING(
                f"Unmatched Ministers ({len(unmatched_ministers)})"
            ))
            self.stdout.write(f"{'='*60}")
            self.stdout.write(
                "These ministers were not found in the database. "
                "Run import_parlparse to import MPs/Lords:"
            )
            self.stdout.write(self.style.SUCCESS(
                "  python manage.py import_parlparse --since 2010"
            ))
            self.stdout.write("")
            for name in sorted(unmatched_ministers):
                self.stdout.write(f"  - {name}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✓ Import complete!"))

    def _bulk_import(self, options):
        """
        Bulk import mode: Auto-discover publications via web scraping.

        Scrapes GOV.UK collection pages to find all quarterly publications,
        then imports them automatically.
        """
        dept_code = options.get('department')
        since_year = options.get('since')
        dry_run = options.get('dry_run', False)
        refresh = options.get('refresh', False)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"BULK IMPORT MODE - Auto-Discovery")
        self.stdout.write(f"{'='*60}\n")

        # Determine which departments to process
        if dept_code:
            # Single department
            dept_config = get_department_by_name(dept_code)
            if not dept_config:
                raise CommandError(f"Unknown department: {dept_code}")
            departments_to_process = [(dept_code, dept_config)]
            self.stdout.write(f"Department: {dept_config.name}")
        else:
            # All departments
            departments_to_process = list(DEPARTMENTS.items())
            self.stdout.write(f"Processing ALL {len(departments_to_process)} departments")

        if since_year:
            self.stdout.write(f"Since: {since_year}")

        self.stdout.write("")

        # Initialize scraper
        scraper = GovUkScraper()

        # Track overall statistics
        total_publications_found = 0
        total_meetings_imported = 0
        total_errors = 0

        # Process each department
        for dept_code, dept_config in departments_to_process:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing: {dept_config.name} ({dept_code})")
            self.stdout.write(f"{'='*60}")

            # Get or create department Organization
            department, created = models.Organization.objects.get_or_create(
                name=dept_config.name,
                defaults={
                    'classification': 'Government Department',
                    'founding_date': dept_config.start_date or '',
                    'dissolution_date': dept_config.end_date or '',
                }
            )

            # Discover publications
            try:
                self.stdout.write(f"Discovering publications from: {dept_config.collection_url}")
                publications = scraper.discover_publications(
                    dept_config.collection_url,
                    since_year=since_year
                )

                if not publications:
                    self.stdout.write(self.style.WARNING("  No publications found"))
                    continue

                self.stdout.write(self.style.SUCCESS(f"  ✓ Found {len(publications)} publications"))
                total_publications_found += len(publications)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error discovering publications: {e}"))
                total_errors += 1
                continue

            # Import each publication
            for pub in publications:
                self.stdout.write(f"\n  Importing: {pub['title']} ({pub['quarter']})")
                self.stdout.write(f"    Format: {pub['format'].upper()}")
                self.stdout.write(f"    URL: {pub['url']}")

                try:
                    # Download file
                    filename = pub['url'].split('/')[-1]
                    helpers.create_data_folder(f'ministerial_meetings/{dept_code}')

                    filepath = helpers.fetch_file(
                        pub['url'],
                        filename,
                        path=f'ministerial_meetings/{dept_code}',
                        refresh=refresh
                    )

                    # Parse file
                    parser = MinisterialMeetingsParser()
                    year = self._extract_year_from_quarter(pub['quarter'])
                    meetings = parser.parse_file(filepath, year=year)

                    self.stdout.write(f"    Parsed: {len(meetings)} meetings")

                    if len(meetings) == 0:
                        self.stdout.write(self.style.WARNING("    No valid meetings found, skipping"))
                        continue

                    if dry_run:
                        self.stdout.write(self.style.WARNING("    [DRY RUN] Skipping import"))
                        total_meetings_imported += len(meetings)
                        continue

                    # Import meetings
                    before_count = models.MinisterialMeeting.objects.count()

                    # Temporarily override options for import
                    import_options = {
                        'url': pub['url'],
                        'quarter': pub['quarter'],
                        'dry_run': False,
                    }

                    self._import_meetings(meetings, department, import_options)

                    after_count = models.MinisterialMeeting.objects.count()
                    imported = after_count - before_count

                    self.stdout.write(self.style.SUCCESS(f"    ✓ Imported {imported} new meetings"))
                    total_meetings_imported += imported

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ Error: {e}"))
                    logger.exception(f"Error importing {pub['title']}")
                    total_errors += 1
                    continue

        # Final summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"BULK IMPORT SUMMARY")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Departments processed: {len(departments_to_process)}")
        self.stdout.write(f"Publications found: {total_publications_found}")
        self.stdout.write(self.style.SUCCESS(f"✓ Meetings imported: {total_meetings_imported}"))

        if total_errors > 0:
            self.stdout.write(self.style.WARNING(f"⚠ Errors: {total_errors}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN MODE] No changes saved to database"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✓ Bulk import complete!"))

    def _create_meeting_attendees(self, meeting, matcher):
        """
        Automatically create MeetingAttendee records for a meeting (Phase 2+).

        Phase 3.2 Enhancement:
        - Uses NameSplitter for robust delimiter detection (semicolons, "and", "/", commas)
        - Uses ActorClassifier to determine Person vs Organization
        - Filters out event descriptions using EventDescriptionParser
        - Integrates EntityResolutionService for canonical linking

        Splits roundtable meetings into individual attendees.
        Creates single attendee for one-on-one meetings.
        """
        raw_org = meeting.organisation_met_raw

        # Check if this is an event description, not an organization list
        if EventDescriptionParser.is_event_description(raw_org):
            # Try to extract actual attendees from the description
            extracted = EventDescriptionParser.extract_attendees(raw_org)
            if extracted:
                attendee_names = extracted
                meeting.is_roundtable = len(attendee_names) > 1
            else:
                # No parseable attendees - move description to purpose
                if not meeting.purpose or meeting.purpose == 'Not specified':
                    meeting.purpose = raw_org
                    meeting.save(update_fields=['purpose'])
                # Don't create garbage actor for event descriptions
                return
        else:
            # Use NameSplitter for robust delimiter detection
            # Handles: semicolons, " and ", " / ", commas
            attendee_names = NameSplitter.split_attendee_list(raw_org)
            meeting.is_roundtable = len(attendee_names) > 1

        meeting.save(update_fields=['is_roundtable'])

        # Initialize entity resolution service
        entity_resolver = EntityResolutionService()

        for attendee_name in attendee_names:
            attendee_name = attendee_name.strip()
            if not attendee_name:
                continue

            # Skip if this looks like an event description that slipped through
            if EventDescriptionParser.is_event_description(attendee_name):
                logger.debug(f"Skipping event description: {attendee_name}")
                continue

            # Determine if this is a Person or Organization using ActorClassifier
            actor_type = ActorClassifier.classify(attendee_name)

            if actor_type == 'person' or ActorClassifier.has_person_title(attendee_name):
                # Create/match as Person
                actor = self._get_or_create_person(attendee_name, matcher)
            else:
                # Create/match as Organization (default for unknown)
                actor = matcher.match_external_actor(
                    attendee_name,
                    create_if_missing=True
                )

            if not actor:
                logger.warning(f"Could not create actor for: {attendee_name}")
                continue

            # Create MeetingAttendee (idempotent)
            attendee, created = models.MeetingAttendee.objects.get_or_create(
                meeting=meeting,
                actor_name_raw=attendee_name,
                defaults={
                    'actor': actor,
                    'canonical_actor': None,
                }
            )

            # Run entity resolution to set canonical_actor
            if created:
                entity_resolver.resolve_and_link(attendee, 'canonical_actor_id')

    def _get_or_create_person(self, name, matcher):
        """
        Get or create a Person actor for a meeting attendee.

        Uses EntityMatcher for existing person lookup, creates new if needed.
        Normalizes name before creation to fix data quality issues at import time.
        """
        from datafetch.helpers import parse_name

        # Normalize name first (fixes tabular columns, trailing punctuation, etc.)
        normalized_name = normalize_actor_name(name, strength='strong')

        # Try to find existing Person (check both original and normalized)
        existing = models.Person.objects.filter(name__iexact=normalized_name).first()
        if not existing:
            existing = models.Person.objects.filter(name__iexact=name).first()
        if existing:
            return existing

        # Try normalized match via matcher
        existing_actor = matcher.match_external_actor(normalized_name, create_if_missing=False)
        if existing_actor and hasattr(existing_actor, 'person'):
            return existing_actor

        # Create new Person with normalized name
        person = models.Person.objects.create(name=normalized_name)

        # Try to parse name into given_name, family_name
        try:
            _, person_dict = parse_name(name)
            for key, value in person_dict.items():
                if hasattr(person, key) and value:
                    setattr(person, key, value)
            person.save()
        except Exception as e:
            logger.warning(f"Could not parse person name '{name}': {e}")

        return person

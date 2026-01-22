"""
Enrich Organizations with Companies House Data

Searches the Companies House API to find and link company data to Organization records.
Uses confidence-based matching with auto-approve/review workflow.

Usage:
    # Dry run preview
    python manage.py enrich_companies_house --dry-run

    # Process by category with batching (recommended for large datasets)
    python manage.py enrich_companies_house --category donor --batch-size 100
    python manage.py enrich_companies_house --category lobbying_client --batch-size 200

    # Process without prompts (for scripts/cron)
    python manage.py enrich_companies_house --category donor --batch-size 500 --no-input

    # Single org or refresh
    python manage.py enrich_companies_house --org-id 12345 --refresh

Confidence Workflow:
    - >= 0.85: Auto-approved and enriched immediately
    - 0.75-0.94: Queued for review in CompaniesHouseMatch table
    - < 0.75: Skipped (no match)

Data Storage:
    - Company number: Identifier (scheme='uk.gov.companieshouse')
    - Company type: Organization.classification
    - Formation date: Organization.founding_date
    - Dissolution date: Organization.dissolution_date
    - Address: ContactDetail (contact_type='address')
    - SIC codes: Note (content='SIC: 62020 - Computer consultancy')
    - Previous names: OtherName (alias_type='strong', note='Former company name (CH)')
"""

import logging
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from datafetch import models
from datafetch.services.companies_house_client import (
    CompaniesHouseClient,
    CompanyOfficer,
    PersonWithSignificantControl,
)
from datafetch.utils.companies_house_matcher import (
    CompaniesHouseMatcher,
    calculate_ch_similarity,
    get_company_type_classification,
    normalize_company_number,
)
from datafetch.utils.director_matcher import DirectorMatcher

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Enrich Organization records with Companies House data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without modifying database'
        )
        parser.add_argument(
            '--category',
            nargs='+',
            choices=[
                'lobbying_agency',   # PRCA lobbying agencies (~217)
                'donor',             # All donation donors (~7,830)
                'meeting_attendee',  # Ministerial meeting attendees (~17,037)
                'lobbying_client',   # PRCA lobbying clients
                'all',               # All organizations
            ],
            default=['all'],
            help='Category(s) to process in order. E.g.: --category lobbying_agency donor meeting_attendee'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of organizations to process'
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            help='Starting offset for batch processing'
        )
        parser.add_argument(
            '--org-id',
            type=int,
            default=None,
            help='Process a single organization by ID'
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Re-fetch cached API data'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.75,
            help='Minimum confidence score for matches (0.0-1.0, default: 0.75)'
        )
        parser.add_argument(
            '--auto-approve-threshold',
            type=float,
            default=0.85,
            help='Confidence threshold for auto-approval (default: 0.85). Matches below this go to review queue.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-process orgs with existing CH ID and overwrite field values'
        )
        parser.add_argument(
            '--auto-approve-all',
            action='store_true',
            help='Auto-approve all matches above min-confidence (skip review queue)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each organization'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show debug output: search queries, results, similarity scores'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=None,
            help='Process in batches of this size, prompting to continue after each batch'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Run without prompting (for scripts/cron jobs)'
        )

        # Director and PSC fetching
        parser.add_argument(
            '--fetch-directors',
            action='store_true',
            help='Fetch and store company directors for matched organizations'
        )
        parser.add_argument(
            '--fetch-pscs',
            action='store_true',
            help='Fetch and store beneficial owners (PSCs) for matched organizations'
        )
        parser.add_argument(
            '--fetch-all',
            action='store_true',
            help='Fetch both directors AND beneficial owners'
        )
        parser.add_argument(
            '--all-officers',
            action='store_true',
            help='Include all officer types (not just directors)'
        )
        parser.add_argument(
            '--include-resigned',
            action='store_true',
            help='Include resigned directors/ceased PSCs'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        self.debug = options['debug']
        self.refresh = options['refresh']
        self.force = options['force']
        self.auto_approve_threshold = options['auto_approve_threshold']
        self.auto_approve_all = options['auto_approve_all']

        # Director/PSC options
        self.fetch_directors = options.get('fetch_directors', False) or options.get('fetch_all', False)
        self.fetch_pscs = options.get('fetch_pscs', False) or options.get('fetch_all', False)
        self.all_officers = options.get('all_officers', False)
        self.include_resigned = options.get('include_resigned', False)

        # Debug implies verbose
        if self.debug:
            self.verbose = True

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no database changes will be made'))

        # Show confidence thresholds
        self.stdout.write(f'Confidence thresholds:')
        self.stdout.write(f'  Auto-approve: >= {self.auto_approve_threshold}')
        self.stdout.write(f'  Review queue: {options["min_confidence"]} - {self.auto_approve_threshold}')
        if self.auto_approve_all:
            self.stdout.write(self.style.WARNING('  --auto-approve-all: All matches will be auto-approved'))

        # Initialize client and matcher
        try:
            client = CompaniesHouseClient()
            if not client.api_key:
                self.stdout.write(self.style.ERROR(
                    'No API key configured. Set COMPANIES_HOUSE_API_KEY in .env\n'
                    'Get a key from: https://developer.company-information.service.gov.uk/'
                ))
                return

            # Test connection
            self.stdout.write('Testing Companies House API connection...')
            if not client.test_connection():
                self.stdout.write(self.style.ERROR(
                    'Failed to connect to Companies House API.\n'
                    'Please verify your API key is valid.\n'
                    'Get a new key from: https://developer.company-information.service.gov.uk/'
                ))
                return
            self.stdout.write(self.style.SUCCESS('API connection successful'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize API client: {e}'))
            return

        self.matcher = CompaniesHouseMatcher(
            client=client,
            min_confidence=options['min_confidence'],
            dry_run=self.dry_run
        )

        # Initialize director matcher if fetching directors/PSCs
        self.director_matcher = DirectorMatcher(dry_run=self.dry_run)
        self.client = client  # Store client for director/PSC fetching

        # Show director/PSC mode
        if self.fetch_directors or self.fetch_pscs:
            modes = []
            if self.fetch_directors:
                modes.append('directors')
            if self.fetch_pscs:
                modes.append('PSCs')
            self.stdout.write(f'Fetching: {", ".join(modes)}')

        # Get organizations to process
        if options['org_id']:
            orgs = self._get_single_org(options['org_id'])
        else:
            orgs = self._get_organizations(
                category=options['category'],
                include_matched=self.force
            )

        # Apply limit and offset
        if options['offset']:
            orgs = orgs[options['offset']:]
        if options['limit']:
            orgs = orgs[:options['limit']]

        total = len(orgs)
        batch_size = options.get('batch_size')
        no_input = options.get('no_input', False)

        if batch_size:
            self.stdout.write(f'Processing {total} organizations in batches of {batch_size}...')
        else:
            self.stdout.write(f'Processing {total} organizations...')

        # Process organizations (with optional batching)
        matched = 0
        auto_approved = 0
        pending_review = 0
        errors = 0
        stopped_early = False
        directors_imported = 0
        pscs_imported = 0

        for i, org in enumerate(orgs, 1):
            try:
                result = self._process_organization(org, options)
                if result:
                    matched += 1
                    if result.get('status') == 'auto_approved':
                        auto_approved += 1
                    elif result.get('status') == 'pending':
                        pending_review += 1
                    directors_imported += result.get('directors_imported', 0)
                    pscs_imported += result.get('pscs_imported', 0)

                # Progress indicator
                if i % 10 == 0 or i == total:
                    rate_status = client.get_rate_limit_status()
                    self.stdout.write(
                        f'Progress: {i}/{total} '
                        f'(matched: {matched}, auto: {auto_approved}, pending: {pending_review}, '
                        f'API remaining: {rate_status["requests_remaining"]})'
                    )

                # Batch checkpoint - prompt to continue
                if batch_size and i % batch_size == 0 and i < total:
                    remaining = total - i
                    self.stdout.write('')
                    self.stdout.write(self.style.SUCCESS(f'=== Batch Complete ({i}/{total}) ==='))
                    self.stdout.write(f'  Matched: {matched} (auto: {auto_approved}, pending: {pending_review})')
                    self.stdout.write(f'  Errors: {errors}')
                    self.stdout.write(f'  Remaining: {remaining} organizations')
                    self.stdout.write('')

                    if not no_input and not self.dry_run:
                        try:
                            response = input('Continue? [Y/n/q] (Y=yes, n=no/stop, q=quit): ').strip().lower()
                            if response in ('n', 'no', 'q', 'quit', 'stop'):
                                self.stdout.write(self.style.WARNING('Stopped by user.'))
                                stopped_early = True
                                break
                            # Any other response (including empty) continues
                        except (EOFError, KeyboardInterrupt):
                            self.stdout.write(self.style.WARNING('\nStopped by user.'))
                            stopped_early = True
                            break

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'Error processing {org.pk} ({org.name}): {e}'))
                if self.verbose:
                    import traceback
                    traceback.print_exc()

        # Summary
        processed = i if stopped_early else total
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Summary ==='))
        self.stdout.write(f'Organizations processed: {processed}/{total}')
        self.stdout.write(f'Matches found: {matched}')
        self.stdout.write(f'  Auto-approved (enriched): {auto_approved}')
        self.stdout.write(f'  Pending review: {pending_review}')
        if self.fetch_directors or self.fetch_pscs:
            self.stdout.write(f'Directors imported: {directors_imported}')
            self.stdout.write(f'PSCs imported: {pscs_imported}')
        self.stdout.write(f'Errors: {errors}')
        if stopped_early:
            self.stdout.write(self.style.WARNING(f'Stopped early - {total - processed} organizations remaining'))

        # Matcher stats
        self.stdout.write('')
        self.stdout.write('Match breakdown:')
        stats = self.matcher.get_stats()
        self.stdout.write(f'  Already had identifier: {stats["already_has_identifier"]}')
        self.stdout.write(f'  Exact matches: {stats["exact_matches"]}')
        self.stdout.write(f'  Normalized matches: {stats["normalized_matches"]}')
        self.stdout.write(f'  CH-specific matches: {stats.get("ch_matches", 0)}')
        self.stdout.write(f'  Fuzzy matches: {stats["fuzzy_matches"]}')
        self.stdout.write(f'  No match: {stats["no_match"]}')
        self.stdout.write(f'  Duplicates found: {stats["duplicates_found"]}')

        # Director/PSC matcher stats
        if self.fetch_directors or self.fetch_pscs:
            self.stdout.write('')
            self.stdout.write('Director/PSC matching:')
            dm_stats = self.director_matcher.get_stats()
            self.stdout.write(f'  Processed: {dm_stats["processed"]}')
            self.stdout.write(f'  Identifier matches: {dm_stats["identifier_matches"]}')
            self.stdout.write(f'  Name + DOB matches: {dm_stats["name_dob_matches"]}')
            self.stdout.write(f'  Exact name matches: {dm_stats["exact_name_matches"]}')
            self.stdout.write(f'  Created persons: {dm_stats["created_persons"]}')
            self.stdout.write(f'  Created organizations: {dm_stats["created_organizations"]}')

        if self.dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN - no changes were made'))
        else:
            # Show total pending review
            total_pending = models.CompaniesHouseMatch.objects.filter(status='pending').count()
            if total_pending > 0:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING(
                    f'Total pending review: {total_pending} matches\n'
                    f'Review in Django admin or run: manage.py review_ch_matches'
                ))

    def _get_single_org(self, org_id):
        """Get a single organization by ID."""
        try:
            org = models.Organization.objects.get(pk=org_id)
            return [org]
        except models.Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Organization {org_id} not found'))
            return []

    def _get_organizations(self, category, include_matched):
        """
        Get organizations to process based on category(s).

        Categories (can be combined, processed in order):
        - lobbying_agency: PRCA lobbying agencies (~217)
        - donor: All donation donors (~7,830)
        - meeting_attendee: Ministerial meeting attendees (~17,037)
        - lobbying_client: PRCA lobbying clients
        - all: All organizations
        """
        categories = category if isinstance(category, list) else [category]

        # Get IDs already matched (to skip unless include_matched is True)
        org_content_type = ContentType.objects.get_for_model(models.Organization)
        if include_matched:
            matched_ids = set()  # Don't skip any
        else:
            # Skip orgs with existing CH identifier
            matched_ids = set(models.Identifier.objects.filter(
                content_type=org_content_type,
                scheme='uk.gov.companieshouse'
            ).values_list('object_id', flat=True))

            # Also skip orgs with pending/approved CH matches
            pending_ids = set(models.CompaniesHouseMatch.objects.filter(
                status__in=['pending', 'approved', 'auto_approved']
            ).values_list('organization_id', flat=True))
            matched_ids = matched_ids | pending_ids

        # Pre-compute category membership
        agency_ids = set(models.Consultancy.objects.values_list('agency_id', flat=True).distinct())
        client_ids = set(models.Consultancy.objects.values_list('client_id', flat=True).distinct())
        donor_ids = set(models.Donation.objects.values_list('donor_id', flat=True).distinct())
        meeting_attendee_ids = set(models.MinisterialMeeting.objects.filter(
            external_actor__isnull=False
        ).values_list('external_actor_id', flat=True).distinct())
        all_org_ids = set(models.Organization.objects.values_list('pk', flat=True))
        other_ids = all_org_ids - agency_ids - client_ids - donor_ids - meeting_attendee_ids

        # Handle 'all' category
        if 'all' in categories:
            base_qs = models.Organization.objects.all()
            if not include_matched:
                base_qs = base_qs.exclude(pk__in=matched_ids)
            return list(base_qs.order_by('name'))

        # Build ordered list from multiple categories
        seen_ids = set()
        result = []

        for cat in categories:
            if cat == 'lobbying_agency':
                cat_ids = agency_ids
            elif cat == 'donor':
                cat_ids = donor_ids
            elif cat == 'meeting_attendee':
                cat_ids = meeting_attendee_ids
            elif cat == 'lobbying_client':
                cat_ids = client_ids
            elif cat == 'other':
                cat_ids = other_ids
            else:
                continue

            # Filter out already seen and already matched
            new_ids = cat_ids - seen_ids - matched_ids
            seen_ids.update(new_ids)

            # Get orgs for this category
            if new_ids:
                cat_orgs = list(models.Organization.objects.filter(
                    pk__in=new_ids
                ).order_by('name'))
                result.extend(cat_orgs)
                self.stdout.write(f'  {cat}: {len(cat_orgs)} organizations')

        return result

    def _process_organization(self, org, options):
        """
        Process a single organization using confidence-based workflow.

        - High confidence (>= auto_approve_threshold): Auto-approve and enrich
        - Medium confidence (min_confidence to auto_approve_threshold): Queue for review
        - Low confidence (< min_confidence): Skip

        Returns dict with match info or None if no match.
        """
        if self.verbose:
            self.stdout.write(f'\nProcessing: {org.name} (ID: {org.pk})')

        # Check if there's already a pending/approved match for this org
        existing_match = models.CompaniesHouseMatch.objects.filter(
            organization=org,
            status__in=['pending', 'approved', 'auto_approved']
        ).first()

        if existing_match and not self.force:
            if self.verbose:
                self.stdout.write(f'  Already has match: {existing_match.company_number} ({existing_match.status})')
            return None

        # Debug: Show search details
        if self.debug:
            self._debug_search(org)

        # Try to match
        match_result = self.matcher.match_organization(org, refresh=self.refresh)

        if not match_result.is_match:
            if self.verbose:
                self.stdout.write(f'  No match: {match_result.matched_on}')
                if self.debug:
                    self.stdout.write(f'    Search returned {match_result.search_results_count} results')
            return None

        confidence = match_result.confidence
        company_number = match_result.company_number
        match_reason = match_result.match_reason

        if self.verbose:
            self.stdout.write(
                f'  Match: {company_number} '
                f'(confidence: {confidence:.2f}, reason: {match_reason})'
            )

        # Determine action based on confidence
        should_auto_approve = (
            self.auto_approve_all or
            confidence >= self.auto_approve_threshold
        )

        if self.dry_run:
            status = 'auto_approved' if should_auto_approve else 'pending'
            if self.verbose:
                action = 'Would auto-approve' if should_auto_approve else 'Would queue for review'
                self.stdout.write(f'  {action}')
            return {
                'org_id': org.pk,
                'company_number': company_number,
                'confidence': confidence,
                'match_reason': match_reason,
                'status': status,
            }

        # Create or update CompaniesHouseMatch record
        ch_match, created = models.CompaniesHouseMatch.objects.update_or_create(
            organization=org,
            company_number=company_number,
            defaults={
                'company_name': match_result.company_profile.company_name if match_result.company_profile else '',
                'company_status': match_result.company_profile.company_status if match_result.company_profile else '',
                'company_type': match_result.company_profile.company_type if match_result.company_profile else '',
                'confidence': confidence,
                'match_reason': match_reason,
                'match_details': match_result.matched_on,
                'status': 'pending',  # Will be updated below if auto-approved
            }
        )

        if should_auto_approve:
            # Auto-approve and enrich
            ch_match.approve(user=None, auto=True)
            # Also do full enrichment with profile data
            if match_result.company_profile:
                self._enrich_organization(org, match_result)

            if self.verbose:
                self.stdout.write(self.style.SUCCESS(f'  Auto-approved and enriched'))

            # Import directors and/or PSCs if requested
            directors_count = 0
            pscs_count = 0
            if self.fetch_directors:
                directors_count = self._import_directors(org, company_number, options)
                if self.verbose and directors_count:
                    self.stdout.write(f'    Imported {directors_count} directors')
            if self.fetch_pscs:
                pscs_count = self._import_pscs(org, company_number, options)
                if self.verbose and pscs_count:
                    self.stdout.write(f'    Imported {pscs_count} PSCs')

            return {
                'org_id': org.pk,
                'company_number': company_number,
                'confidence': confidence,
                'match_reason': match_reason,
                'status': 'auto_approved',
                'directors_imported': directors_count,
                'pscs_imported': pscs_count,
            }
        else:
            # Queue for review
            if self.verbose:
                self.stdout.write(self.style.WARNING(f'  Queued for review (confidence: {confidence:.2f})'))

            return {
                'org_id': org.pk,
                'company_number': company_number,
                'confidence': confidence,
                'match_reason': match_reason,
                'status': 'pending',
            }

    def _debug_search(self, org):
        """
        Show detailed debug output for CH search and matching.
        """
        from datafetch.utils.normalization import normalize_actor_name

        org_name = org.name
        self.stdout.write(self.style.HTTP_INFO(f'  [DEBUG] Search query: "{org_name}"'))

        # Get search results directly from client
        search_results = self.matcher.client.search_companies(org_name, items_per_page=10)

        if not search_results:
            self.stdout.write(self.style.WARNING(f'  [DEBUG] No search results returned'))
            return

        self.stdout.write(f'  [DEBUG] {len(search_results)} search results:')

        # Show each result with similarity score
        for i, result in enumerate(search_results[:5], 1):  # Top 5 only
            ch_name = result.title
            status = result.company_status

            # Skip dissolved in display but show them
            status_marker = ' (dissolved)' if status == 'dissolved' else ''

            # Calculate similarity
            similarity, reason = calculate_ch_similarity(org_name, ch_name)

            # Color code by similarity
            if similarity >= 0.95:
                style = self.style.SUCCESS
            elif similarity >= 0.75:
                style = self.style.WARNING
            else:
                style = self.style.ERROR

            self.stdout.write(style(
                f'    {i}. [{similarity:.2f} {reason}] {ch_name} ({result.company_number}){status_marker}'
            ))

        # Show normalized versions for debugging
        self.stdout.write(f'  [DEBUG] Normalized org name:')
        self.stdout.write(f'    strong: "{normalize_actor_name(org_name, "strong")}"')
        self.stdout.write(f'    weak: "{normalize_actor_name(org_name, "weak")}"')

    def _enrich_organization(self, org, match_result):
        """
        Enrich organization with Companies House data.

        Returns True if any data was added/updated.
        """
        profile = match_result.company_profile
        company_number = match_result.company_number
        changes = []

        # 1. Add Company Number as Identifier
        org_content_type = ContentType.objects.get_for_model(models.Organization)
        # Handle potential duplicate identifiers
        existing_identifiers = models.Identifier.objects.filter(
            content_type=org_content_type,
            object_id=org.pk,
            scheme='uk.gov.companieshouse',
        )
        if existing_identifiers.exists():
            # Already has identifier - update if different
            identifier = existing_identifiers.first()
            if identifier.identifier != normalize_company_number(company_number):
                identifier.identifier = normalize_company_number(company_number)
                identifier.save()
                changes.append(f'Updated identifier: {company_number}')
        else:
            # Create new identifier
            identifier = models.Identifier.objects.create(
                content_type=org_content_type,
                object_id=org.pk,
                scheme='uk.gov.companieshouse',
                identifier=normalize_company_number(company_number)
            )
            changes.append(f'Added identifier: {company_number}')

        # 2. Update Classification (company type)
        org_changed = False
        if profile.company_type and (self.force or not org.classification):
            new_class = get_company_type_classification(profile.company_type)
            if org.classification != new_class:
                org.classification = new_class
                changes.append(f'Set classification: {org.classification}')
                org_changed = True

        # 3. Update Founding Date
        if profile.date_of_creation and (self.force or not org.founding_date):
            if org.founding_date != profile.date_of_creation:
                org.founding_date = profile.date_of_creation
                changes.append(f'Set founding_date: {org.founding_date}')
                org_changed = True

        # 4. Update Dissolution Date
        if profile.date_of_cessation and (self.force or not org.dissolution_date):
            if org.dissolution_date != profile.date_of_cessation:
                org.dissolution_date = profile.date_of_cessation
                changes.append(f'Set dissolution_date: {org.dissolution_date}')
                org_changed = True

        # Save org changes
        if org_changed:
            org.save()

        # 5. Add Registered Address as ContactDetail
        if profile.registered_office_address:
            address_parts = []
            addr = profile.registered_office_address
            for key in ['address_line_1', 'address_line_2', 'locality',
                       'region', 'postal_code', 'country']:
                if addr.get(key):
                    address_parts.append(addr[key])

            if address_parts:
                address_str = ', '.join(address_parts)
                contact, created = models.ContactDetail.objects.get_or_create(
                    content_type=org_content_type,
                    object_id=org.pk,
                    contact_type='address',
                    value=address_str,
                    defaults={'label': 'Registered Office'}
                )
                if created:
                    changes.append('Added registered address')

        # 6. Add SIC Codes as Notes
        if profile.sic_codes:
            for sic in profile.sic_codes:
                note_content = f'SIC Code: {sic}'
                note, created = models.Note.objects.get_or_create(
                    content_type=org_content_type,
                    object_id=org.pk,
                    content=note_content
                )
                if created:
                    changes.append(f'Added SIC code: {sic}')

        # 7. Add Previous Names as OtherName
        if profile.previous_company_names:
            for prev in profile.previous_company_names:
                name = prev.get('name', '')
                if not name:
                    continue

                other_name, created = models.OtherName.objects.get_or_create(
                    content_type=org_content_type,
                    object_id=org.pk,
                    name=name,
                    defaults={
                        'alias_type': 'strong',
                        'note': 'Former company name (Companies House)',
                        'start_date': prev.get('effective_from', ''),
                        'end_date': prev.get('ceased_on', ''),
                    }
                )
                if created:
                    changes.append(f'Added former name: {name}')

        # 8. Add source link
        ch_url = f'https://find-and-update.company-information.service.gov.uk/company/{company_number}'
        link, created = models.Link.objects.get_or_create(
            content_type=org_content_type,
            object_id=org.pk,
            url=ch_url,
            defaults={'note': 'Companies House'}
        )
        if created:
            changes.append('Added Companies House link')

        if self.verbose and changes:
            for change in changes:
                self.stdout.write(f'    {change}')

        return len(changes) > 0

    def _import_directors(self, org, company_number, options) -> int:
        """
        Import directors for a company.

        Creates:
        - Person/Organization for each director
        - Identifier with scheme='uk.gov.companieshouse.officer'
        - Membership linking director to organization (role='Director')

        Returns: count of new memberships created
        """
        if self.dry_run:
            return 0

        # Get officer roles to fetch
        if self.all_officers:
            officer_roles = None  # All roles
        else:
            officer_roles = ['director', 'corporate-director']

        # Fetch officers from CH
        try:
            officers = self.client.get_company_officers(
                company_number,
                include_resigned=self.include_resigned,
                officer_roles=officer_roles,
                refresh=self.refresh
            )
        except Exception as e:
            logger.error(f"Error fetching officers for {company_number}: {e}")
            return 0

        if not officers:
            if self.debug:
                self.stdout.write(f'    No officers found for {company_number}')
            return 0

        # Import each officer
        new_memberships = 0
        for officer in officers:
            try:
                new_membership = self._create_director_membership(org, officer)
                if new_membership:
                    new_memberships += 1
            except Exception as e:
                logger.error(f"Error importing officer {officer.name}: {e}")

        return new_memberships

    def _create_director_membership(self, org, officer: 'CompanyOfficer') -> bool:
        """
        Create a membership for a director.

        Returns True if new membership was created.
        """
        from django.contrib.contenttypes.models import ContentType

        # Match or create the director actor
        match_result = self.director_matcher.match_officer(officer)
        if not match_result.is_match:
            return False

        director = match_result.actor

        # Determine role label
        role = self._get_officer_role_label(officer.officer_role)

        # Check for existing membership
        existing = models.Membership.objects.filter(
            organization=org,
            role=role
        )

        # Check if this specific director already has this role
        if isinstance(director, models.Person):
            existing = existing.filter(person=director)
        else:
            # For corporate directors, we need to check differently
            # as they link via person field (Actor is polymorphic)
            existing = existing.filter(person_id=director.pk)

        if existing.exists():
            if self.debug:
                self.stdout.write(f'      Existing membership: {director.name} -> {org.name}')
            return False

        # Create membership
        # Note: For corporate directors, we still use person field due to model design
        # The Person model is required but we can link Organization actors via actor_ptr
        if isinstance(director, models.Person):
            membership = models.Membership.objects.create(
                person=director,
                organization=org,
                role=role,
                start_date=officer.appointed_on or '',
                end_date=officer.resigned_on or '',
            )
        else:
            # Corporate director - need to handle differently
            # Create a Note on the organization instead of a membership
            # (since Membership requires a Person, not an Organization)
            org_ct = ContentType.objects.get_for_model(models.Organization)
            note_content = f"Corporate Director: {director.name}"
            if officer.appointed_on:
                note_content += f" (appointed: {officer.appointed_on})"
            if officer.resigned_on:
                note_content += f" (resigned: {officer.resigned_on})"

            models.Note.objects.get_or_create(
                content_type=org_ct,
                object_id=org.pk,
                content=note_content
            )
            if self.debug:
                self.stdout.write(f'      Added corporate director note: {director.name}')
            return True

        if self.debug:
            self.stdout.write(f'      Created membership: {director.name} -> {org.name} ({role})')

        return True

    def _get_officer_role_label(self, officer_role: str) -> str:
        """Map CH officer role to human-readable label."""
        role_map = {
            'director': 'Director',
            'corporate-director': 'Corporate Director',
            'secretary': 'Company Secretary',
            'corporate-secretary': 'Corporate Secretary',
            'llp-member': 'LLP Member',
            'llp-designated-member': 'LLP Designated Member',
            'judicial-factor': 'Judicial Factor',
            'receiver-and-manager': 'Receiver and Manager',
            'cic-manager': 'CIC Manager',
            'nominee-director': 'Nominee Director',
            'nominee-secretary': 'Nominee Secretary',
        }
        return role_map.get(officer_role.lower(), officer_role.title())

    def _import_pscs(self, org, company_number, options) -> int:
        """
        Import beneficial owners (PSCs) for a company.

        Creates:
        - Person/Organization for each PSC
        - Identifier with scheme='uk.gov.companieshouse.psc'
        - Membership linking PSC to organization (role='Beneficial Owner (X%)')
        - Note with natures_of_control details

        Returns: count of new memberships created
        """
        if self.dry_run:
            return 0

        # Fetch PSCs from CH
        try:
            pscs = self.client.get_company_pscs(
                company_number,
                include_ceased=self.include_resigned,  # Reuse resigned flag for ceased
                refresh=self.refresh
            )
        except Exception as e:
            logger.error(f"Error fetching PSCs for {company_number}: {e}")
            return 0

        if not pscs:
            if self.debug:
                self.stdout.write(f'    No PSCs found for {company_number}')
            return 0

        # Import each PSC
        new_memberships = 0
        for psc in pscs:
            try:
                new_membership = self._create_psc_membership(org, psc)
                if new_membership:
                    new_memberships += 1
            except Exception as e:
                logger.error(f"Error importing PSC {psc.name}: {e}")

        return new_memberships

    def _create_psc_membership(self, org, psc: 'PersonWithSignificantControl') -> bool:
        """
        Create a membership for a PSC (beneficial owner).

        Returns True if new membership was created.
        """
        from django.contrib.contenttypes.models import ContentType

        # Match or create the PSC actor
        match_result = self.director_matcher.match_psc(psc)
        if not match_result.is_match:
            return False

        psc_actor = match_result.actor

        # Determine role label based on natures of control
        role = self._get_psc_role_label(psc.natures_of_control)

        # Check for existing membership with this role
        existing = models.Membership.objects.filter(
            organization=org,
            role=role
        )

        if isinstance(psc_actor, models.Person):
            existing = existing.filter(person=psc_actor)
        else:
            existing = existing.filter(person_id=psc_actor.pk)

        if existing.exists():
            if self.debug:
                self.stdout.write(f'      Existing PSC membership: {psc_actor.name} -> {org.name}')
            return False

        # Create membership
        if isinstance(psc_actor, models.Person):
            membership = models.Membership.objects.create(
                person=psc_actor,
                organization=org,
                role=role,
                start_date=psc.notified_on or '',
                end_date=psc.ceased_on or '',
            )

            # Add note with full natures of control
            if psc.natures_of_control:
                membership_ct = ContentType.objects.get_for_model(models.Membership)
                control_details = ', '.join(psc.natures_of_control)
                models.Note.objects.create(
                    content_type=membership_ct,
                    object_id=membership.pk,
                    content=f"Natures of control: {control_details}"
                )
        else:
            # Corporate PSC - add as note on organization
            org_ct = ContentType.objects.get_for_model(models.Organization)
            note_content = f"Corporate Beneficial Owner: {psc_actor.name}"
            if psc.natures_of_control:
                note_content += f" ({', '.join(psc.natures_of_control)})"
            if psc.notified_on:
                note_content += f" (notified: {psc.notified_on})"
            if psc.ceased_on:
                note_content += f" (ceased: {psc.ceased_on})"

            models.Note.objects.get_or_create(
                content_type=org_ct,
                object_id=org.pk,
                content=note_content
            )
            if self.debug:
                self.stdout.write(f'      Added corporate PSC note: {psc_actor.name}')
            return True

        if self.debug:
            self.stdout.write(f'      Created PSC membership: {psc_actor.name} -> {org.name} ({role})')

        return True

    def _get_psc_role_label(self, natures_of_control: list) -> str:
        """
        Map CH natures of control to human-readable role label.

        Picks the most significant control type for the role label.
        Full details are stored in a Note.
        """
        if not natures_of_control:
            return 'Beneficial Owner'

        # Priority order for role label
        control_map = {
            'ownership-of-shares-75-to-100-percent': 'Beneficial Owner (75-100% shares)',
            'ownership-of-shares-50-to-75-percent': 'Beneficial Owner (50-75% shares)',
            'ownership-of-shares-25-to-50-percent': 'Beneficial Owner (25-50% shares)',
            'ownership-of-shares-more-than-25-percent-as-trust': 'Beneficial Owner (Trust >25% shares)',
            'ownership-of-shares-more-than-25-percent-as-firm': 'Beneficial Owner (Firm >25% shares)',
            'voting-rights-75-to-100-percent': 'Beneficial Owner (75-100% voting)',
            'voting-rights-50-to-75-percent': 'Beneficial Owner (50-75% voting)',
            'voting-rights-25-to-50-percent': 'Beneficial Owner (25-50% voting)',
            'voting-rights-more-than-25-percent-as-trust': 'Beneficial Owner (Trust >25% voting)',
            'voting-rights-more-than-25-percent-as-firm': 'Beneficial Owner (Firm >25% voting)',
            'right-to-appoint-and-remove-directors': 'Beneficial Owner (appoint directors)',
            'right-to-appoint-and-remove-directors-as-trust': 'Beneficial Owner (Trust appoint directors)',
            'right-to-appoint-and-remove-directors-as-firm': 'Beneficial Owner (Firm appoint directors)',
            'significant-influence-or-control': 'Beneficial Owner (significant control)',
            'significant-influence-or-control-as-trust': 'Beneficial Owner (Trust significant control)',
            'significant-influence-or-control-as-firm': 'Beneficial Owner (Firm significant control)',
            'right-to-share-surplus-assets-75-to-100-percent': 'Beneficial Owner (75-100% surplus assets)',
            'right-to-share-surplus-assets-50-to-75-percent': 'Beneficial Owner (50-75% surplus assets)',
            'right-to-share-surplus-assets-25-to-50-percent': 'Beneficial Owner (25-50% surplus assets)',
        }

        # Find the highest priority control type
        for control_type, label in control_map.items():
            if control_type in natures_of_control:
                return label

        # Fallback: use first control type
        first = natures_of_control[0] if natures_of_control else 'unknown'
        return f'Beneficial Owner ({first.replace("-", " ").title()})'

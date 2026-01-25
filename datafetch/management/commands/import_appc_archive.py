import json
import os
import glob
import re
from os.path import join
from django.core.management.base import BaseCommand
from datafetch import helpers
from datafetch import models
from datafetch.services.appc_parser import AppcPDFParser
from datafetch.utils.normalization import normalize_actor_name

class Command(BaseCommand):
    help = 'Import historical PRCA professional lobbying registers from PDF files.'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true', help='Refresh downloaded files')
        parser.add_argument('--file', type=str, help='Path to a specific PDF file to process (for debugging)')
        parser.add_argument('--dry-run', action='store_true', help='Parse PDFs but do not save to database')

    def handle(self, *args, **options):
        self.refresh = options.get('refresh', False)
        self.dry_run = options.get('dry_run', False)
        target_file = options.get('file')

        archive_path = "appc_archive"
        helpers.create_data_folder(archive_path)

        parser = AppcPDFParser()

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be saved to database"))

        if target_file:
            self._process_single_file(target_file, parser, archive_path)
        else:
            self._process_all_files(parser, archive_path)

    def _process_single_file(self, target_file, parser, archive_path):
        self.stdout.write(f"Analyzing specific PDF: {target_file}")
        try:
            # If it's a URL, download it first
            if target_file.startswith("http"):
                pdf_filename = target_file.split('/')[-1].split('?')[0]
                helpers.fetch_file(target_file, pdf_filename, path=archive_path, refresh=self.refresh)
                pdf_filepath = join('data', archive_path, pdf_filename)
            else:
                pdf_filepath = target_file

            companies_data = parser.parse(pdf_filepath, target_file)
            self.stdout.write(self.style.SUCCESS(f"  - Extracted {len(companies_data)} companies from {target_file}"))

            # Import to database unless dry-run
            if not self.dry_run:
                imported_count = self._import_companies_data(companies_data)
                self.stdout.write(self.style.SUCCESS(f"  - Imported {imported_count} agencies to database"))
            else:
                # For debugging, print the first few results
                if companies_data:
                    self.stdout.write("\n--- Sample Extracted Data (First 3) ---")
                    for company in companies_data[:3]:
                        self.stdout.write(json.dumps(company, indent=2))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to process {target_file}: {e}"))

    def _process_all_files(self, parser, archive_path):
        self.stdout.write("Processing all PDFs in archive...")

        # In a real scenario, we'd fetch the list of files to download first,
        # but for now we'll assume they are downloaded or just process what's there.
        # Ideally, we should reuse the scraping logic to ensure we have all files.
        # For this step, let's just process the local files.

        pdf_files = glob.glob(join('data', archive_path, "*.pdf"))

        if not pdf_files:
            self.stdout.write(self.style.WARNING(f"No PDF files found in data/{archive_path}."))
            return

        total_companies = 0
        total_imported = 0
        successful_files = 0
        failed_files = 0

        for pdf_path in sorted(pdf_files):
            filename = os.path.basename(pdf_path)
            self.stdout.write(f"\nProcessing {filename}...")
            try:
                companies_data = parser.parse(pdf_path, filename)
                count = len(companies_data)
                self.stdout.write(self.style.SUCCESS(f"  - Extracted {count} companies"))
                total_companies += count

                # Import to database unless dry-run
                if not self.dry_run:
                    imported_count = self._import_companies_data(companies_data)
                    self.stdout.write(self.style.SUCCESS(f"  - Imported {imported_count} agencies"))
                    total_imported += imported_count

                successful_files += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  - Failed: {e}"))
                failed_files += 1

        self.stdout.write("\n" + "*"*40)
        self.stdout.write(f"SUMMARY")
        self.stdout.write(f"Processed {successful_files} files successfully.")
        self.stdout.write(f"Failed {failed_files} files.")
        self.stdout.write(f"Total companies extracted: {total_companies}")
        if not self.dry_run:
            self.stdout.write(f"Total agencies imported: {total_imported}")
        self.stdout.write("*"*40)

    def _import_companies_data(self, companies_data):
        """
        Import a list of company data dicts to the database.
        Returns the number of agencies successfully imported.
        """
        imported_count = 0

        for company in companies_data:
            try:
                self._import_single_company(company)
                imported_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to import {company.get('name', 'Unknown')}: {e}"))

        return imported_count

    def _import_single_company(self, company_data):
        """
        Import a single company's data to the database.
        Structure mirrors the current import_appc command.
        """
        agency_name = company_data.get('name', '').strip()
        if not agency_name:
            return

        # Normalize agency name for consistency
        agency_name = normalize_actor_name(agency_name, strength='strong')

        date_range = company_data.get('date_range', (None, None))
        source_url = company_data.get('source_url', '')

        # Create or get the lobbying agency Organization
        # Handle potential duplicates by using filter().first()
        agency_obj = models.Organization.objects.filter(name=agency_name).first()
        if not agency_obj:
            agency_obj = models.Organization.objects.create(
                name=agency_name,
                classification="Lobbying agency"
            )

        # Add address as contact detail
        addresses = company_data.get('address', [])
        if addresses:
            address_text = ', '.join(addresses)
            # Truncate to 512 characters to fit database field limit
            if len(address_text) > 512:
                address_text = address_text[:509] + '...'
            contact_dict = {
                "value": address_text,
                "contact_type": "address",
            }
            agency_obj.contact_details.add(
                models.ContactDetail.objects.get_or_create(**contact_dict)[0]
            )

        # Add email/phone from contact_details
        for contact_line in company_data.get('contact_details', []):
            # Try to extract email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', contact_line)
            if email_match:
                contact_dict = {
                    "value": email_match.group(0),
                    "contact_type": "email"
                }
                agency_obj.contact_details.add(
                    models.ContactDetail.objects.get_or_create(**contact_dict)[0]
                )

            # Try to extract website
            website_match = re.search(r'(https?://[^\s/$.?#].[^\s]*)', contact_line)
            if website_match:
                url = website_match.group(0).rstrip('.')
                link_dict = {
                    "url": url,
                    "note": "website"
                }
                agency_obj.links.add(
                    models.Link.objects.get_or_create(**link_dict)[0]
                )

        # Add practitioners as Person objects with membership
        for practitioner_name in company_data.get('practitioners', []):
            practitioner_name = practitioner_name.strip()
            if practitioner_name:
                # Normalize practitioner name
                practitioner_name = normalize_actor_name(practitioner_name, strength='strong')

                # Handle potential duplicates by using filter().first()
                # This can happen if practitioners were imported before name normalization
                person_obj = models.Person.objects.filter(name=practitioner_name).first()
                if not person_obj:
                    person_obj = models.Person.objects.create(name=practitioner_name)

                # Create Membership explicitly with dates
                models.Membership.objects.get_or_create(
                    person=person_obj,
                    organization=agency_obj,
                    role="Lobbyist",
                    defaults={
                        "start_date": date_range[0],
                        "end_date": date_range[1]
                    }
                )

        # Add clients and create Consultancy relationships
        for client_name in company_data.get('clients', []):
            client_name = client_name.strip()
            if client_name:
                # Normalize client name
                client_name = normalize_actor_name(client_name, strength='strong')

                # Handle potential duplicates by using filter().first()
                client_obj = models.Organization.objects.filter(name=client_name).first()
                if not client_obj:
                    client_obj = models.Organization.objects.create(name=client_name)

                # Create Consultancy relationship with date range
                models.Consultancy.objects.get_or_create(
                    label="Consultancy",
                    client=client_obj,
                    agency=agency_obj,
                    source=source_url,
                    start_date=date_range[0],
                    end_date=date_range[1],
                )
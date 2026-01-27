import calendar
from datetime import datetime
from os.path import join
import re

from django.core.management.base import BaseCommand, CommandError
from bs4 import BeautifulSoup, element

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import PRCA professional lobbying register'
    base_url = "https://www.prca.global"
    register_url = "https://www.prca.global/professional-lobbying-register"

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true',
                            help='Force refresh of cached HTML pages')
        parser.add_argument('--verbose', action='store_true',
                            help='Show detailed output including split client names')

    # Patterns that should NOT be split (false positives)
    # Keep in sync with split_concatenated_orgs.py EXCLUDE_PATTERNS
    EXCLUDE_PATTERNS = [
        re.compile(r'Limited\s+(Partnership|Company|Liability)$', re.IGNORECASE),
        re.compile(r'Ltd\s+(T/?A|C/?o)\s+', re.IGNORECASE),  # Trading As, Care of
        re.compile(r'Limited\s+(T/?A|C/?o)\s+', re.IGNORECASE),
        re.compile(r'PLC\s+Ltd$', re.IGNORECASE),  # "PLC Ltd" is one entity
        re.compile(r'(Ltd|Limited|PLC)\s+(Co|Company)$', re.IGNORECASE),  # ends in Co/Company
        re.compile(r'(Ltd|Limited|PLC)\s+(UK|USA|Europe|International)$', re.IGNORECASE),  # geographic suffix
        re.compile(r'Public\s+Limited\s+Company$', re.IGNORECASE),  # Full PLC name
    ]

    # Words that are NOT separate company names (common suffixes/modifiers)
    SKIP_WORDS = {'Co', 'Company', 'Partnership', 'Group', 'Holdings', 'UK', 'USA',
                  'Europe', 'International', 'Global', 'Worldwide', 'Inc', 'plc'}

    def _split_concatenated_clients(self, name):
        """
        Split concatenated client names like "CompanyA Ltd CompanyB" into separate names.

        Pattern: Company suffix (Ltd, Limited, PLC, Inc, LLP) followed by space and capital letter
        indicates two companies were concatenated.

        Excludes:
        - Limited Partnership, Limited Company, Limited Liability
        - T/A (Trading As), C/o (Care of) patterns
        - Geographic suffixes (UK, USA, Europe)
        - Public Limited Company
        """
        if not name:
            return []

        # Check exclusion patterns first
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern.search(name):
                return [name]

        # Pattern: (Ltd|Limited|PLC|Inc|LLP) followed by space and capital letter
        concat_pattern = re.compile(
            r'^(.+?(?:Ltd|Limited|PLC|Inc|LLP)\.?)\s+([A-Z].+)$',
            re.IGNORECASE
        )

        match = concat_pattern.match(name)
        if match:
            first = match.group(1).strip()
            second = match.group(2).strip()

            # Skip if second part is too short (likely not a company name)
            if len(second) < 5:
                return [name]

            # Skip if second part is just common suffixes/words
            if second in self.SKIP_WORDS:
                return [name]

            # Skip if second part starts with "t/a" or "trading as"
            if second.lower().startswith('t/a') or second.lower().startswith('trading as'):
                return [name]

            # Skip if second part starts with "c/o" or "care of"
            if second.lower().startswith('c/o') or second.lower().startswith('care of'):
                return [name]

            # Skip duplicates (first and second are essentially the same)
            first_base = re.sub(r'\s*(Ltd|Limited|PLC|Inc|LLP)\.?\s*$', '', first, flags=re.IGNORECASE).strip()
            second_base = re.sub(r'\s*(Ltd|Limited|PLC|Inc|LLP)\.?\s*$', '', second, flags=re.IGNORECASE).strip()
            if first_base.lower() == second_base.lower():
                return [name]

            # Recursively split the second part in case of 3+ companies
            results = [first]
            results.extend(self._split_concatenated_clients(second))
            return results

        return [name]

    def get_dates(self, text):
        # try quarter format first, e.g. "last updated 2025 Q3"
        match = re.search(r'(\d{4})\s+Q(\d)', text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            quarter = int(match.group(2))

            if quarter == 1:
                start_date = datetime(year, 1, 1).date()
                end_date = datetime(year, 3, 31).date()
            elif quarter == 2:
                start_date = datetime(year, 4, 1).date()
                end_date = datetime(year, 6, 30).date()
            elif quarter == 3:
                start_date = datetime(year, 7, 1).date()
                end_date = datetime(year, 9, 30).date()
            else:  # quarter == 4
                start_date = datetime(year, 10, 1).date()
                end_date = datetime(year, 12, 31).date()
            return str(start_date), str(end_date)

        # fallback to old format, e.g. "1st June 2022 to 31st August 2022"
        months = "|".join(calendar.month_name[1:])
        date_range = re.findall(r"(\d+).*?(%s) (\d{4})" % months, text, re.IGNORECASE)
        if date_range:
            return [str(datetime.strptime(" ".join(i for i in x), "%d %B %Y").date()) for x in date_range]

        return None, None

    def _scrape_company_section(self, agency_name, company_soup_section, date_range):
        source_url = self.register_url

        agency_dict = {
            "name": agency_name,
            "classification": "Lobbying Agency"
        }
        agency_obj, created = models.Organization.objects.get_or_create(
            name=agency_dict["name"],
            defaults=agency_dict,
        )
        if created:
            self.stats['agencies_created'] += 1
            if self.verbose:
                self.stdout.write(self.style.SUCCESS(f"Created lobbying agency: {agency_name}"))
        else:
            self.stats['agencies_updated'] += 1

        # The content is in <p> tags, with <strong> tags as labels.
        for p in company_soup_section.find_all('p'):
            strong_tag = p.find('strong')
            if not strong_tag:
                continue

            header_text = strong_tag.text.strip().lower()
            content_text = ''

            # The actual content can be after the <strong> tag as a string, or after a <br> tag.
            if strong_tag.next_sibling and isinstance(strong_tag.next_sibling, element.NavigableString):
                content_text = strong_tag.next_sibling.strip()
            elif p.find('br'):
                content_text = "\n".join([s.strip() for s in p.find('br').find_next_siblings(string=True) if s.strip()])
            else:
                continue

            if not content_text:
                continue

            if "uk address" in header_text:
                address = content_text
                contact_dict = {
                    "value": address.replace('\n', ', '),
                    "contact_type": "address",
                }
                agency_obj.contact_details.add(models.ContactDetail.objects.get_or_create(**contact_dict)[0])

            elif "practitioners conducting" in header_text:
                staff_names = [name.strip() for name in content_text.split('\n') if name.strip()]
                for staff_name in staff_names:
                    # some names might have position in brackets, or other notes
                    staff_name = re.sub(r'\(.*?\)|,.*', '', staff_name).strip()
                    if staff_name:
                        agency_obj.add_member(models.Person.objects.get_or_create(name=staff_name)[0])

            elif "fee-paying clients" in header_text:
                # Split by newlines first
                raw_client_names = [name.strip() for name in content_text.split('\n') if name.strip()]
                # Then split any concatenated names (e.g., "CompanyA Ltd CompanyB")
                client_names = []
                for raw_name in raw_client_names:
                    split_names = self._split_concatenated_clients(raw_name)
                    if len(split_names) > 1:
                        self.stats['names_split'] += 1
                        self.stats['split_parts_total'] += len(split_names)
                        if self.verbose:
                            self.stdout.write(f"  Split '{raw_name}' -> {split_names}")
                    client_names.extend(split_names)
                for client_name in client_names:
                    if client_name:
                        client_dict = {"name": client_name}
                        client_obj, created = models.Organization.objects.get_or_create(
                            name=client_dict["name"],
                            defaults=client_dict,
                        )
                        if created:
                            self.stats['clients_created'] += 1
                        else:
                            self.stats['clients_existing'] += 1
                        _, consultancy_created = models.Consultancy.objects.get_or_create(
                            label="Consultancy",
                            client=client_obj,
                            agency=agency_obj,
                            source=source_url,
                            start_date=date_range[0],
                            end_date=date_range[1],
                        )
                        if consultancy_created:
                            self.stats['consultancies_created'] += 1

        # Contact details like email/website might be in the address block or separate.
        section_text = company_soup_section.get_text()
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', section_text)
        if email_match:
            contact_dict = {"value": email_match.group(0), "contact_type": "email"}
            agency_obj.contact_details.add(models.ContactDetail.objects.get_or_create(**contact_dict)[0])

        website_match = re.search(r'(https?://[^\s/$.?#].[^\s]*)', section_text)
        if website_match:
            url = website_match.group(0).rstrip('.')  # remove trailing dot if any
            link_dict = {"url": url, "note": "website"}
            agency_obj.links.add(models.Link.objects.get_or_create(**link_dict)[0])

    def handle(self, *args, **options):
        self.refresh = options.get('refresh', False)
        self.verbose = options.get('verbose', False)
        helpers.create_data_folder("appc")

        page_num = 0
        date_range = None
        total_companies = 0
        next_url = self.register_url

        # Track statistics
        self.stats = {
            'agencies_created': 0,
            'agencies_updated': 0,
            'clients_created': 0,
            'clients_existing': 0,
            'consultancies_created': 0,
            'names_split': 0,
            'split_parts_total': 0,
        }

        while next_url:
            self.stdout.write(f"Fetching {next_url}...")
            page_filename = f"prca_register_page_{page_num}.html"
            t = helpers.fetch_text(next_url, page_filename, path="appc", refresh=self.refresh)
            soup = BeautifulSoup(t, "lxml")

            if page_num == 0:
                date_range_text_element = soup.find(string=re.compile("Register for", re.IGNORECASE)) or soup.find(string=re.compile("last updated", re.IGNORECASE))
                if not date_range_text_element:
                    raise CommandError("Could not find date range on page.")

                date_range_text = date_range_text_element.parent.parent.get_text()
                date_range = self.get_dates(date_range_text)
                if not date_range or not date_range[0]:
                    raise CommandError(f"Could not parse date range from '{date_range_text}'")

                self.stdout.write(f"Processing register for date range: {date_range[0]} to {date_range[1]}")
                path = join("appc", date_range[1])
                helpers.create_data_folder(path)

            company_headings = soup.find_all('h3')
            page_companies = len(company_headings)
            if page_companies == 0 and page_num > 0:
                # Sometimes the last page link exists but the page is empty
                self.stdout.write("Found an empty page, stopping.")
                break
                
            total_companies += page_companies
            self.stdout.write(f"Found {page_companies} companies on page {page_num + 1}.")

            for heading in company_headings:
                agency_name = heading.text.strip()
                if not agency_name:
                    continue

                section_elements = []
                for sibling in heading.find_next_siblings():
                    if sibling.name == 'h3':
                        break
                    section_elements.append(str(sibling))

                if not section_elements:
                    continue

                company_soup_section = BeautifulSoup("".join(section_elements), "html5lib")
                self._scrape_company_section(agency_name, company_soup_section, date_range)

            next_page_link = soup.select_one('li.next a')
            if next_page_link and next_page_link.has_attr('href'):
                next_url = self.base_url + next_page_link['href']
                page_num += 1
            else:
                next_url = None

        self.stdout.write(self.style.SUCCESS(f"""
Import complete:
  - Agencies found: {total_companies}
  - Agencies created: {self.stats['agencies_created']}
  - Agencies updated: {self.stats['agencies_updated']}
  - Clients created: {self.stats['clients_created']}
  - Clients existing: {self.stats['clients_existing']}
  - Consultancies created: {self.stats['consultancies_created']}
  - Concatenated names split: {self.stats['names_split']} (into {self.stats['split_parts_total']} parts)
"""))

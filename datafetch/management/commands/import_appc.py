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
        parser.add_argument('--refresh', action='store_true')

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
            "classification": "Lobbying agency"
        }
        agency_obj, created = models.Organization.objects.get_or_create(
            name=agency_dict["name"],
            defaults=agency_dict,
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created lobbying agency: {agency_name}"))

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
                client_names = [name.strip() for name in content_text.split('\n') if name.strip()]
                for client_name in client_names:
                    if client_name:
                        client_dict = {"name": client_name}
                        client_obj = models.Organization.objects.get_or_create(
                            name=client_dict["name"],
                            defaults=client_dict,
                        )[0]
                        models.Consultancy.objects.get_or_create(
                            label="Consultancy",
                            client=client_obj,
                            agency=agency_obj,
                            source=source_url,
                            start_date=date_range[0],
                            end_date=date_range[1],
                        )

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
        helpers.create_data_folder("appc")

        page_num = 0
        date_range = None
        total_companies = 0
        next_url = self.register_url

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

        self.stdout.write(self.style.SUCCESS(f"Finished importing. Found {total_companies} companies in total."))

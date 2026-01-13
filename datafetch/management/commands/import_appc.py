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
                start_date = datetime(year, 3, 1).date()
                end_date = datetime(year, 5, 31).date()
            elif quarter == 2:
                start_date = datetime(year, 6, 1).date()
                end_date = datetime(year, 8, 31).date()
            elif quarter == 3:
                start_date = datetime(year, 9, 1).date()
                end_date = datetime(year, 11, 30).date()
            else:  # quarter == 4
                start_date = datetime(year, 12, 1).date()
                end_date = datetime(year, 2, 28).date()
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

        self.stdout.write(f"Fetching {self.register_url}...")
        t = helpers.fetch_text(self.register_url, "prca_register.html", path="appc", refresh=self.refresh)
        soup = BeautifulSoup(t, "lxml")

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

        # The companies are in <h3> tags.
        company_headings = soup.find_all('h3')
        self.stdout.write(f"Found {len(company_headings)} companies in the register.")

        for heading in company_headings:
            agency_name = heading.text.strip()
            if not agency_name:
                continue

            # The content for this company is in the elements between this h3 and the next h3
            section_elements = []
            for sibling in heading.find_next_siblings():
                if sibling.name == 'h3':
                    break
                section_elements.append(str(sibling))

            if not section_elements:
                continue

            company_soup_section = BeautifulSoup("".join(section_elements), "html5lib")
            self._scrape_company_section(agency_name, company_soup_section, date_range)

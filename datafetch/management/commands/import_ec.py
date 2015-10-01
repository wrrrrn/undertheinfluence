import csv
import re
from io import StringIO
from os.path import join, exists

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests
from datafetch import models


class Command(BaseCommand):
    help = 'Import Electoral Commission data'
    data_directory = join(settings.BASE_DIR, 'datafetch', 'data')
    refresh = False

    source_tmpl = "http://search.electoralcommission.org.uk/English/Donations/{}"

    def _parse_name(self, name):
        data = {}
        honorific_prefix = []
        name = name.strip()
        # honorary suffixes
        name = re.sub(r'( [A-Z]{2,})*$', '', name)

        if name.startswith('The Rt Hon '):
            name = name[len('The Rt Hon '):]
            honorific_prefix.append('The Rt Hon')

        if name.startswith('Sir '):
            name = name[len('Sir '):]
            honorific_prefix.append('Sir')
            data['gender'] = "man"

        m = re.match(r'(Mr|Miss|Mrs|Ms) (.*)$', name)
        if m:
            name = m.group(2)
            data['gender'] = "man" if m.group(1) in ["Mr", "Sir"] else "woman"

        # honorary prefixes
        name = re.sub(r'(Cllr|Dr) ', '', name)

        if honorific_prefix:
            data['honorific_prefix'] = ' '.join(honorific_prefix)

        data['name'] = name

        return data

    def _parse_date(self, date):
        return "{}-{}-{}".format(date[6:], date[3:5], date[:2]) if date else ""

    def _process_donor(self, donor):
        ec_identifier, created = models.Identifier.objects.get_or_create(identifier=donor['ecref'], scheme='uk.org.electoralcommission')
        if not created:
            # this donor already exists
            if donor['entity_status_name'] == 'Individual':
                return models.Person.objects.get(identifiers=ec_identifier)
            else:
                return models.Organization.objects.get(identifiers=ec_identifier)

        actor = {'name': donor['regulated_entity_name']}
        if donor['entity_status_name'] == 'Individual':
            actor = dict(zip(('name', 'honorific_prefix', 'gender',), self._parse_name(actor['name'])))
            a, created = models.Person.objects.get_or_create(name=actor['name'], defaults=actor)
        else:
            if donor['regulated_entity_type_name'] == 'Third Party':
                actor['classification'] = donor['entity_status_name']
            else:
                actor['classification'] = 'Political Party'
            a, created = models.Organization.objects.get_or_create(name=actor['name'], defaults=actor)
        a.identifiers.add(ec_identifier)
        return a

    def _process_donations(self, donations):
        # ^(?:The )?co-operati[cv]e
        for donation in donations:
            print(donation)
            exit()
            if donation.get('company_registration_number'):
                reg_num = donation['company_registration_number']
                while len(reg_num) < 8:
                    reg_num = '0' + reg_num
                id_ = {'identifier': reg_num, 'scheme': "uk.gov.companieshouse"}
                i, created = models.Identifier.get_or_create(**id_)

                m = models.Organization.objects.filter(identifiers__identifier=reg_num, identifiers__scheme="uk.gov.companieshouse")
            # donation['regulated_entity_name']
            registered_donor['id'] = self._process_donor(registered_donor).id



                # if not (models.Person.objects.filter(name__icontains=name) or models.OtherName.objects.filter(name__icontains=name) or models.Organization.objects.filter(name__icontains=name)):
                #     print('{} ** {}'.format(d['regulated_entity_type'], name))

        #     if d['regulated_entity_type'] not in ['Political Party']:
        #         success = self._parse_name(d['regulated_entity_name'])
        #         if not success:
        #     output = {
        #         "identifiers": [{'identifier': d["ecref"], 'scheme': 'electoralcommission'}],
        #         "source": self.source_tmpl.format(d["ecref"]),
        #         "value": d['value'][1:].replace(',', ''),
        #         "accepted_date": self._parse_date(d["accepted_date"]),
        #         "received_date": self._parse_date(d["received_date"]),
        #         "reported_date": self._parse_date(d["reported_date"]),
        #     }
        # print(success_dict)
            # {
            #     "regulated_donee_type": ""
            #     "donor_status": "Individual"
            #     "is_aggregation": "True"
            #     "accounting_unit_name": "Central Party"
            #     "donation_type": "Non Cash"
            #     "reporting_period_name": "Q1 2001"
            #     "regulated_entity_name": "Conservative Party"
            #     "purpose_of_visit": ""
            #     "is_sponsorship": "False"
            #     "regulated_entity_type": "Political Party"
            #     "is_reported_pre_poll": "False"
            #     "nature_of_donation": "Travel"
            #     "is_bequest": "False"
            #     "donation_action": ""
            #     "donor_name": " Stanley Kalms"
            #     "company_registration_number": ""
            #     "accounting_units_as_central_party": "False"

            #     "postcode": ""
            # }

    def snake_case(self, camel_case_text):
        return re.sub(r'([a-z])([A-Z])', r'\1_\2', camel_case_text).lower()

    def fetch_csv(self, url, filename):
        filepath = join(self.data_directory, filename)
        if exists(filepath) and not self.refresh:
            with open(filepath) as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [self.snake_case(fieldname) for fieldname in reader.fieldnames]
                return list(reader)
        else:
            r = requests.get(url)
            r.encoding = "utf8"
            raw_text = r.text[1:]
            with open(filepath, "w") as f:
                f.write(raw_text)
            reader = csv.DictReader(StringIO(raw_text))
            reader.fieldnames = [self.snake_case(fieldname) for fieldname in reader.fieldnames]
            return list(reader)

    def handle(self, *args, **options):
        donations_url = "http://search.electoralcommission.org.uk/api/csv/Donations"
        donations = self.fetch_csv(donations_url, "ec.csv")

        # # This turned out to be a bit of a blind alley.
        # # There’s really not much to be gleaned from this register.
        # registrations_url = "http://search.electoralcommission.org.uk/api/csv/Registrations"
        # registered_entities = self.fetch_csv(registrations_url, "ec_reg.csv")
        # registered_entities_dict = {v['regulated_entity_name']: v for v in registered_entities}

        print("Processing donations ...")
        self._process_donations(donations)

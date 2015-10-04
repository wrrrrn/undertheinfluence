from django.core.management.base import BaseCommand, CommandError

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import Companies House data'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')

    def _fetch_companies_house(self, identifiers):
        address_parts = ('CareofName', 'PoBox', 'AddressLine1', 'AddressLine2', 'PostTown', 'Postcode', 'County', 'Country',)
        helpers.create_data_folder('companieshouse')

        for identifier in identifiers:
            url = "http://data.companieshouse.gov.uk/doc/company/{}.json".format(identifier.identifier)
            filename = "ch_{}.json".format(identifier.identifier)
            try:
                j = helpers.fetch_json(url, filename, path='companieshouse', refresh=self.refresh)
            except ValueError:
                continue

            org = models.Organization.objects.get(identifiers=identifier)

            org.founding_date = self._parse_date(j['primaryTopic'].get('IncorporationDate'))
            org.dissolution_date = self._parse_date(j['primaryTopic'].get('DissolutionDate'))
            classification = j['primaryTopic']['CompanyCategory']
            if classification is None:
                classification = ''
            org.classification = classification
            org.save()

            # # TODO: Other names
            # name = j['primaryTopic']['CompanyName']
            # other_names = ...

            address = j['primaryTopic'].get('RegAddress')
            if address:
                address = ', '.join([address[k] for k in address_parts if k in address])
                # TODO: Save contact_detail

            # TODO: Save source URL

    def _fetch_opencorporates(self, identifiers):
        for identifier in identifiers:
            url = "https://api.opencorporates.com/companies/gb/{}".format(identifier.identifier)
            filename = "oc_{}.json".format(identifier.identifier)
            j = helpers.fetch_json(url, filename, refresh=self.refresh)

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')

        print("Fetching extra organizational data from Companies House ...")
        identifiers = models.Identifier.objects.filter(scheme="uk.gov.companieshouse")
        self._fetch_companies_house(identifiers)

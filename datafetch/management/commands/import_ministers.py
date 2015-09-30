import json
from os.path import join, exists

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests
from datafetch import models


class Command(BaseCommand):
    help = 'Import ParlParse minister data'
    data_directory = join(settings.BASE_DIR, 'datafetch', 'data')
    refresh = False

    def add_arguments(self, parser):
        parser.add_argument('--since', nargs='?', type=int)

    def _process_organizations(self, organizations):
        organizations_dict = {}
        for organization in organizations:
            id_ = organization['id']
            del organization['id']
            m, created = models.Organization.objects.get_or_create(name=organization['name'], defaults={k: v for k, v in organization.items()})
            organizations_dict[id_] = m.id

        return organizations_dict

    def _process_minister(self, membership, j):
        ignore_fields = ('id', 'source',)
        unique_fields = ('person_id', 'start_date', 'role', 'organization_id',)

        membership['organization_id'] = j['organizations'][membership['organization_id']]
        scheme, identifier = membership['person_id'].split('/', 1)
        membership['person_id'] = models.Person.objects.get(identifiers__identifier=identifier, identifiers__scheme=scheme).id

        defaults = {k: v for k, v in membership.items() if k not in ignore_fields}
        unique = {k: v for k, v in membership.items() if k in unique_fields}

        models.Membership.objects.get_or_create(defaults=defaults, **unique)

    def handle(self, *args, **options):
        for filename in ["ministers", "ministers-2010"]:
            url = "https://cdn.rawgit.com/mysociety/parlparse/master/members/{}.json".format(filename)
            filepath = join(self.data_directory, '{}.json'.format(filename))
            if exists(filepath) and not self.refresh:
                with open(filepath) as f:
                    j = json.load(f)
            else:
                r = requests.get(url)
                time.sleep(0.5)
                with open(filepath, "w") as f:
                    f.write(r.text)
                j = r.json()

            since = options.get('since')
            if since:
                print("Importing since {} ...".format(since))
                # get a very stripped down version of memberships
                j['memberships'] = [x for x in j['memberships'] if x.get('end_date', '9999-12-31') >= str(since) and not x.get('redirect')]
                organizations = {x['id']: x for x in j['organizations']}
                # get a stripped down version of organizations
                j['organizations'] = {x['organization_id']: organizations[x['organization_id']] for x in j['memberships'] if'organization_id' in x}.values()

            print("Processing organizations ...")
            j['organizations'] = self._process_organizations(j['organizations'])

            print("Processing ministerial posts ...")
            for membership in j['memberships']:
                self._process_minister(membership, j)

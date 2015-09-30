import json
from os.path import join, exists
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests
from datafetch import models


class Command(BaseCommand):
    help = 'Import EveryPolitician data'
    data_directory = join(settings.BASE_DIR, 'datafetch', 'data')
    refresh = False

    def _process_people(self, people):
        person_rels = {
            'links': models.Link,
            'identifiers': models.Identifier,
        }

        ignore_fields = (
            'id', 'links', 'identifiers', 'images',
            'name', 'contact_details',
        )

        for person in people:
            p = models.Person.objects.get(identifiers__identifier=person['id'])
            for k, v in person.items():
                if k not in ignore_fields:
                    setattr(p, k, v)
            p.save()
            for rel_id, rel_model in person_rels.items():
                for rel_dict in person.get(rel_id, []):
                    getattr(p, rel_id).add(rel_model.objects.get_or_create(defaults=rel_dict, **rel_dict)[0])
                for c in person.get('contact_details', []):
                    contact_dict = { 'contact_type': c['type'], 'value': c['value'] }
                    p.contact_details.add(models.ContactDetail.objects.get_or_create(defaults=contact_dict, **contact_dict)[0])

    def handle(self, *args, **options):
        filepath = join(self.data_directory, 'ep-popolo-v1.0.json')
        if exists(filepath) and not self.refresh:
            with open(filepath) as f:
                j = json.load(f)
        else:
            url = "https://cdn.rawgit.com/everypolitician/everypolitician-data/master/data/UK/Commons/ep-popolo-v1.0.json"
            r = requests.get(url)
            time.sleep(0.5)
            with open(filepath, "w") as f:
                f.write(r.text)
            j = r.json()

        print("Processing people ...")
        self._process_people(j['persons'])

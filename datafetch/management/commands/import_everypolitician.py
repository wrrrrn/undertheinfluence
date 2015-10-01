from os.path import join

from django.core.management.base import BaseCommand, CommandError

from datafetch import models
from datafetch.helpers import fetch_file, fetch_json, create_data_folder


class Command(BaseCommand):
    help = 'Import EveryPolitician data'

    def _process_people(self, people):
        person_rels = {
            'links': models.Link,
            'identifiers': models.Identifier,
        }

        ignore_fields = (
            'id', 'links', 'identifiers', 'images',
            'name', 'contact_details',
        )

        path_to_images = join('..', '..', 'media', 'persons')
        create_data_folder(path_to_images)

        for person in people:
            try:
                p = models.Person.objects.get(identifiers__identifier=person['id'], identifiers__scheme="uk.org.publicwhip")
            except models.Person.DoesNotExist:
                continue
            for k, v in person.items():
                if k not in ignore_fields:
                    setattr(p, k, v)
            p.save()
            if p.image:
                filename = str(p.id)
                if p.image.startswith('http://yournextmp.popit.mysociety.org'):
                    filename += '.png'
                else:
                    print(p.image)
                fetch_file(p.image, filename, path=path_to_images)
            for rel_id, rel_model in person_rels.items():
                for rel_dict in person.get(rel_id, []):
                    getattr(p, rel_id).add(rel_model.objects.get_or_create(defaults=rel_dict, **rel_dict)[0])
                for c in person.get('contact_details', []):
                    contact_dict = {'contact_type': c['type'], 'value': c['value']}
                    p.contact_details.add(models.ContactDetail.objects.get_or_create(defaults=contact_dict, **contact_dict)[0])

    def handle(self, *args, **options):
        filename = "ep-popolo-v1.0.json"
        url = "https://cdn.rawgit.com/everypolitician/everypolitician-data/master/data/UK/Commons/ep-popolo-v1.0.json"
        j = fetch_json(url, filename)

        print("Processing people ...")
        self._process_people(j['persons'])

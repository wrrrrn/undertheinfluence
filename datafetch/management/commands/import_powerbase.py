import time

from django.core.management.base import BaseCommand, CommandError
import requests

from datafetch import models
from datafetch.helpers import fetch_json

class Command(BaseCommand):
    help = 'Import Electoral Commission data'
    refresh = False

    def _fetch_powerbase(self, politicians):
        search_url = "http://powerbase.info/api.php?action=opensearch&search={}&limit=10&format=json"
        for politician in politicians:
            j = requests.get(search_url.format(politician.name)).json()
            time.sleep(0.5)
            if not j[1]:
                continue
            # bit of a guess here
            url = 'http://powerbase.info/index.php/{}'.format(j[1][0].replace(' ', '_'))
            link = {'note': 'powerbase', 'url': url}
            l, created = models.Link.objects.get_or_create(**link)
            politician.links.add(l)

    def handle(self, *args, **options):
        print("Discovering Powerbase URLs ...")
        politicians = models.Person.objects.filter(identifiers__scheme='uk.org.publicwhip')
        self._fetch_powerbase(politicians)

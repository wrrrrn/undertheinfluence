from django.core.management.base import BaseCommand, CommandError

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import Lords’ Interests'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')

    # deprecated in favour of bulk download
    def _download_lords_interests(self):
        url = "http://lda.data.parliament.uk/lordsregisteredinterests.json?_view=Registered+Interest&_pageSize=50&_page=0"
        page = 0
        helpers.create_data_folder("lordsinterests")
        data = []
        while url:
            j = helpers.fetch_json(url, "lords_interests_{:02d}.json".format(page), path="lordsinterests", refresh=self.refresh)
            data += j['result']['items']
            url = j['result'].get('next')
            page += 1
        return data

    def _bulk_download_lords_interests(self):
        # it’s possible to fetch historical data from mnis. Something like:
        # http://data.parliament.uk/membersdataplatform/services/mnis/members/query/joinedbetween=%sand%s|lordsmemberbetween=%sand%s/Interests%7CPreferredNames/
        # We don’t use this currently
        url = "http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Lords/Interests%7CPreferredNames/"
        headers = {"content-type": "application/json"}
        return helpers.fetch_json(url, "lords_interests.json", path="lordsinterests", headers=headers, encoding="utf-8-sig", refresh=self.refresh)

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')

        print("Downloading Lords’ Interests ...")
        data = self._bulk_download_lords_interests()

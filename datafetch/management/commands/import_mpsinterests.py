from os.path import join, exists

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import MPs’ Interests'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')

    mps_datadir = join(settings.BASE_DIR, 'data', 'mpsinterests')
    base_url = "http://www.theyworkforyou.com/pwdata/scrapedxml/regmem/"

    # deprecated in favour of bulk download
    def _download_mps_interests(self):
        helpers.create_data_folder("mpsinterests")

        parl_data_path = join(self.mps_datadir, 'parldata', 'scrapedxml', 'regmem')
        print(parl_data_path)
        if not exists(parl_data_path):
            raise CommandError("You should fetch historical MPs’ interests data with `git submodule update`")

        url = "{}changedates.txt".format(self.base_url)
        r = helpers.fetch_text(url, "changedates.txt", path="mpsinterests", refresh=self.refresh)
        to_fetch = [x.split(",") for x in r.split("\n") if x != ""]

        for timestamp, filename in to_fetch:
            date = filename[6:16]
            if date <= "2015-01-06":
                # we already have this as part of the historical data
                continue

            filepath = join(self.mps_datadir, filename)
            url = self.base_url + filename
            print("Fetching %s ..." % url)
            helpers.fetch_text(url, filepath, refresh=self.refresh)

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')

        print("Downloading MPs’ Interests ...")
        data = self._download_mps_interests()

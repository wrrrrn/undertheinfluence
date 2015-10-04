import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import TheyWorkForYou data'

    def add_arguments(self, parser):
        parser.add_argument('--since', nargs='?', type=int)
        parser.add_argument('--refresh', action='store_true')

    base_url = "http://www.theyworkforyou.com"
    # local directory to save fetched files to
    api_key = settings.TWFY_API_KEY
    helpers.create_data_folder('twfy')

    def _get_overview_data(self, date):
        date_str = date.strftime("%d/%m/%Y")
        # print("  Fetching MP overview data from TheyWorkForYou (%s) ..." % date_str)

        filename = "mps_overview_{}.json".format(str(date))
        url = "{}/api/getMPs?key={}&date={}".format(self.base_url, self.api_key, date_str)
        mps = fetch_json(url, filename, path='twfy', refresh=self.refresh)
        return [mp["person_id"] for mp in mps]

    def _get_mps_since(self, since, increment):
        all_mps = set()
        now = datetime.date.today()
        date = datetime.datetime.strptime(since, "%Y-%m-%d").date()
        while date < now:
            all_mps.update(self._get_overview_data(date=date))
            print("  MPs found so far: {}".format(len(all_mps)))
            date += datetime.timedelta(increment)
        all_mps.update(self._get_overview_data(date=now))
        return list(all_mps)

    def _get_mp_info(self, mp_id):
        filename = "twfy_{}_info.json".format(mp_id)
        extra_fields = ", ".join(["wikipedia_url", "bbc_profile_url", "date_of_birth", "mp_website", "guardian_mp_summary", "journa_list_link"])
        url = "{}/api/getMPInfo?key={}&id={}&fields={}".format(
            self.base_url,
            self.api_key,
            mp_id,
            extra_fields)
        info = fetch_json(url, filename, path='twfy', refresh=self.refresh)

        filename = "twfy_{}.json".format(mp_id)
        url = "{}/api/getMP?key={}&id={}".format(
            self.base_url,
            self.api_key,
            mp_id)
        info['details'] = fetch_json(url, filename, path='twfy', refresh=self.refresh)

        return info

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')
        since = options.get('since')

        # print("Fetching MPs ...")
        mp_ids = self._get_mps_since("{}-01-01".format(since), 180)
        # print("Fetching individual MP data ...")
        for mp_id in mp_ids:
            # print("  Fetching MP details for person ID {} ... ({} / {})".format(mp_id, idx+1, len(mp_ids)))
            mp_info = self._get_mp_info(mp_id)

            for term in mp_info["details"]:
                end_date = term["left_house"] if term["left_house"] != "9999-12-31" else None
                membership = models.Membership.objects.get(
                    person_id="person/{}".format(mp_id),
                    start_date=term["entered_house"],
                    end_date=end_date)
                print(membership.organization)
            #     positions = term.get("office", [])
            #     for position in positions:
            #         print(position)

        # print("Done.")

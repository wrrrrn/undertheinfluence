import datetime
import json
from os.path import join, exists
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests
from datafetch import models


class Command(BaseCommand):
    help = 'Import ParlParse data'

    base_url = "http://www.theyworkforyou.com"
    # local directory to save fetched files to
    data_directory = join(settings.BASE_DIR, 'datafetch', 'data')
    refresh = False
    api_key = settings.TWFY_API_KEY

    def _get_overview_data(self, date):
        date_str = date.strftime("%d/%m/%Y")
        # print("  Fetching MP overview data from TheyWorkForYou (%s) ..." % date_str)

        filepath = join(self.data_directory, "mps_overview_{}.json".format(str(date)))
        if exists(filepath) and not self.refresh:
            with open(filepath) as f:
                mps = json.load(f)
        else:
            url = "{}/api/getMPs?key={}&date={}".format(self.base_url, self.api_key, date_str)
            r = requests.get(url)
            time.sleep(0.5)
            with open(filepath, "w") as f:
                f.write(r.text)
            mps = r.json()

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
        filepath = join(self.data_directory, "twfy_{}.json".format(mp_id))
        # print("... {}".format(filepath))
        if exists(filepath) and not self.refresh:
            # if the MP file exists, we bail out
            with open(filepath) as f:
                info = json.load(f)
            return info

        extra_fields = ", ".join(["wikipedia_url", "bbc_profile_url", "date_of_birth", "mp_website", "guardian_mp_summary", "journa_list_link"])
        url = "{}/api/getMPInfo?key={}&id={}&fields={}".format(
            self.base_url,
            self.api_key,
            mp_id,
            extra_fields)
        info = requests.get(url).json()
        time.sleep(0.5)

        url = "{}/api/getMP?key={}&id={}".format(
            self.base_url,
            self.api_key,
            mp_id)
        info["details"] = requests.get(url).json()
        time.sleep(0.5)

        with open(filepath, "w") as f:
            json.dump(info, f)

        return info

    def handle(self, *args, **options):
        # print("Fetching MPs ...")
        mp_ids = self._get_mps_since("2000-01-01", 180)
        # print("Fetching individual MP data ...")
        for idx, mp_id in enumerate(mp_ids):
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

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
    helpers.create_data_folder('twfy')

    def _get_api_key(self):
        """Get API key from settings - must be called after Django is initialized"""
        if not hasattr(self, '_api_key'):
            self._api_key = settings.TWFY_API_KEY
        return self._api_key

    def _get_overview_data(self, date):
        date_str = date.strftime("%d/%m/%Y")
        # print("  Fetching MP overview data from TheyWorkForYou (%s) ..." % date_str)

        filename = "mps_overview_{}.json".format(str(date))
        url = "{}/api/getMPs?key={}&date={}".format(self.base_url, self._get_api_key(), date_str)
        mps = helpers.fetch_json(url, filename, path='twfy', refresh=self.refresh)

        # Handle API errors
        if isinstance(mps, dict) and 'error' in mps:
            raise CommandError("TheyWorkForYou API error: {}".format(mps['error']))

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
            self._get_api_key(),
            mp_id,
            extra_fields)
        info = helpers.fetch_json(url, filename, path='twfy', refresh=self.refresh)

        # Handle API errors
        if isinstance(info, dict) and 'error' in info:
            # Return empty dict on error so enrichment can skip gracefully
            return {}

        filename = "twfy_{}.json".format(mp_id)
        url = "{}/api/getMP?key={}&id={}".format(
            self.base_url,
            self._get_api_key(),
            mp_id)
        details = helpers.fetch_json(url, filename, path='twfy', refresh=self.refresh)

        # Handle API errors
        if isinstance(details, dict) and 'error' in details:
            info['details'] = []
        else:
            info['details'] = details

        return info

    def _import_mp_enrichment(self, mp_id, mp_info):
        """
        Import enrichment data (URLs, birth date, image) to existing Person records.
        This complements parlparse data without duplicating core membership info.
        """
        # Find existing Person by TWFY person_id identifier
        try:
            person = models.Person.objects.get(
                identifiers__scheme='uk.org.publicwhip',
                identifiers__identifier=f'uk.org.publicwhip/person/{mp_id}'
            )
        except models.Person.DoesNotExist:
            # Person not found - skip enrichment
            # This is expected for MPs not yet imported via parlparse
            return False
        except models.Person.MultipleObjectsReturned:
            # Handle duplicates - just use first
            person = models.Person.objects.filter(
                identifiers__scheme='uk.org.publicwhip',
                identifiers__identifier=f'uk.org.publicwhip/person/{mp_id}'
            ).first()

        updated_fields = []

        # Import date of birth if available
        if mp_info.get('date_of_birth') and not person.birth_date:
            person.birth_date = mp_info['date_of_birth']
            updated_fields.append('birth_date')

        # Import image URL if available
        if mp_info.get('details') and len(mp_info['details']) > 0:
            latest_term = mp_info['details'][0]  # Most recent term
            if latest_term.get('image') and not person.image:
                # Construct full image URL
                image_url = f"https://www.theyworkforyou.com{latest_term['image']}"
                person.image = image_url
                updated_fields.append('image')

        # Save person if any fields were updated
        if updated_fields:
            person.save()

        # Import URLs as Link records
        url_types = [
            ('wikipedia_url', 'Wikipedia'),
            ('bbc_profile_url', 'BBC Profile'),
            ('mp_website', 'MP Website'),
            ('guardian_mp_summary', 'Guardian Profile'),
        ]

        for url_key, url_label in url_types:
            if mp_info.get(url_key):
                # Check if link already exists
                existing = person.links.filter(url=mp_info[url_key]).exists()
                if not existing:
                    models.Link.objects.create(
                        content_object=person,
                        url=mp_info[url_key],
                        note=url_label
                    )
                    updated_fields.append(url_label)

        return len(updated_fields) > 0

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')
        since = options.get('since')

        print("Fetching MPs since {} ...".format(since))
        mp_ids = self._get_mps_since("{}-01-01".format(since), 180)

        print("Fetching enrichment data for {} MPs ...".format(len(mp_ids)))
        enriched_count = 0
        skipped_count = 0

        for idx, mp_id in enumerate(mp_ids):
            if (idx + 1) % 50 == 0:
                print("  Processed {} / {} MPs ({} enriched, {} skipped)".format(
                    idx + 1, len(mp_ids), enriched_count, skipped_count))

            mp_info = self._get_mp_info(mp_id)

            if self._import_mp_enrichment(mp_id, mp_info):
                enriched_count += 1
            else:
                skipped_count += 1

        print("Done. Enriched {} MPs, skipped {} MPs.".format(enriched_count, skipped_count))

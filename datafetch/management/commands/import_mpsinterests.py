from os.path import join, exists
import os
import subprocess
from decimal import Decimal
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from datafetch import models, helpers
from datafetch.services.mps_interests_parser import MPsInterestsParser
from datafetch.models import Person, Organization, Donation, Identifier

class Command(BaseCommand):
    help = 'Import MPs’ Interests'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')
        parser.add_argument('--file', type=str, help='Path to a specific XML file to process')

    mps_datadir = join(settings.BASE_DIR, 'data', 'mpsinterests')
    base_url = "https://www.theyworkforyou.com/pwdata/scrapedxml/regmem/"

    def _download_mps_interests(self):
        helpers.create_data_folder("mpsinterests")

        url = "{}changedates.txt".format(self.base_url)
        print(f"Fetching {url}...")
        r = helpers.fetch_text(url, "changedates.txt", path="mpsinterests", refresh=self.refresh)
        
        # Parse the list of files
        to_fetch = [x.split(",") for x in r.split("\n") if x != ""]
        
        downloaded_files = []

        for timestamp, filename in to_fetch:
            if len(filename) < 16:
                continue
            
            date = filename[6:16]
            
            # Fetch recent files (late 2024)
            if date < "2024-10-01":
                continue

            filepath = join(self.mps_datadir, filename)
            url = self.base_url + filename
            
            if not exists(filepath) or self.refresh:
                print(f"Fetching {url} ...")
                subprocess.call(["curl", "-s", "-o", filepath, url])
            
            downloaded_files.append(filepath)
            
        return downloaded_files

    def _get_or_create_donor(self, name, status):
        # Check if exists
        actors = models.Actor.objects.filter(name__iexact=name)
        if actors.exists():
            return actors.first()
        
        # Create new
        if status == "Individual":
            donor = Person.objects.create(name=name)
        else:
            donor = Organization.objects.create(name=name, classification=status)
            
        return donor

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d %B %Y").date()
        except ValueError:
            try:
                 return datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                return None

    def _import_data(self, files):
        parser = MPsInterestsParser()
        
        for xml_file in files:
            if not exists(xml_file):
                print(f"File not found: {xml_file}")
                continue
                
            print(f"Parsing {xml_file}...")
            data = parser.parse(xml_file)
            
            print(f"Found {len(data)} MPs in file. Importing...")
            
            for mp_entry in data:
                person_id = mp_entry['person_id']
                member_name = mp_entry['member_name']
                
                if '/' in person_id:
                    parts = person_id.split('/', 1)
                    scheme_val = parts[0]
                    id_val = parts[1]
                else:
                    scheme_val = "uk.org.publicwhip"
                    id_val = person_id

                try:
                    mp = Person.objects.get(identifiers__scheme=scheme_val, identifiers__identifier=id_val)
                except Person.DoesNotExist:
                    mp = Person.objects.filter(name__iexact=member_name).first()
                    if not mp:
                        continue
                
                for interest in mp_entry['interests']:
                    cat_type = interest['category_type']
                    if cat_type not in ['2', '3']:
                        continue
                        
                    details = interest['details']
                    interest_id = interest['id']
                    
                    if Donation.objects.filter(identifiers__scheme='theyworkforyou_regmem', identifiers__identifier=interest_id).exists():
                        continue

                    donor_name = details.get('Donor Name', 'Unknown')
                    donor_status = details.get('Donor Status', 'Unknown')
                    value_str = details.get('Value', '0').replace(',', '').replace('£', '')
                    try:
                        value = Decimal(value_str)
                    except:
                        value = Decimal(0)
                        
                    donation_type = details.get('Payment Type', 'Unknown')
                    nature = details.get('Payment Description', '')
                    if not nature and cat_type == '3':
                         nature = interest.get('summary', '')

                    reg_date = self._parse_date(interest.get('registration_date'))
                    pub_date = self._parse_date(interest.get('published_date'))
                    
                    donor = self._get_or_create_donor(donor_name, donor_status)
                    
                    donation = Donation.objects.create(
                        recipient=mp,
                        donor=donor,
                        value=value,
                        donation_type=donation_type[:128],
                        nature_of_donation=nature[:128],
                        accepted_date=reg_date,
                        reported_date=pub_date,
                        is_bequest=False,
                        is_aggregation=False,
                        is_sponsorship=False,
                        accounting_units_as_central_party=False
                    )
                    
                    Identifier.objects.create(
                        content_object=donation,
                        scheme='theyworkforyou_regmem',
                        identifier=interest_id
                    )
                    
            print(f"Imported data from {xml_file}")

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')
        target_file = options.get('file')

        if target_file:
            self._import_data([target_file])
            return

        print("Downloading MPs’ Interests ...")
        files = self._download_mps_interests()
        print(f"Downloaded {len(files)} files.")
        
        if files:
            self._import_data(files)
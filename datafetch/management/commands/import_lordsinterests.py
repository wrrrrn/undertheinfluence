from os.path import join, exists
import os
import subprocess
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from datafetch import models, helpers
from datafetch.services.lords_interests_parser import LordsInterestsParser
from datafetch.models import Person, Organization, Donation, Identifier
from datafetch.utils.normalization import normalize_actor_name

class Command(BaseCommand):
    help = 'Import Lords’ Interests'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')
        parser.add_argument('--file', type=str, help='Path to a specific JSON file to process')

    lords_datadir = join(settings.BASE_DIR, 'data', 'lordsinterests')
    # Use HTTPS
    base_url = "https://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Lords/Interests%7CPreferredNames/"

    def _download_lords_interests(self):
        helpers.create_data_folder("lordsinterests")
        
        filename = "lords_interests.json"
        filepath = join(self.lords_datadir, filename)
        
        # We need to set Accept header to application/json
        if not exists(filepath) or self.refresh:
            print(f"Fetching {self.base_url} ...")
            subprocess.call(["curl", "-H", "Accept: application/json", "-o", filepath, self.base_url])
            
        return [filepath]

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            # Format: 2025-04-05T00:00:00
            # datetime.fromisoformat handles this
            return datetime.fromisoformat(date_str).date()
        except:
            return None

    def _get_or_create_donor(self, name):
        # We don't have donor status, assume Organization if it looks like one, else Person?
        # Actually, for Lords, the text is unstructured.
        # "Ticket and hospitality received from Bestway Wholesale..."
        # We can't easily extract the name.
        # So we leave donor blank for now? Or create a placeholder?
        # Donation model allows donor=null.
        return None

    def _import_data(self, files):
        parser = LordsInterestsParser()
        
        for json_file in files:
            print(f"Parsing {json_file}...")
            data = parser.parse(json_file)
            
            print(f"Found {len(data)} Lords in file. Importing...")
            
            count = 0
            for person_data in data:
                member_id = person_data['member_id']
                pims_id = person_data['pims_id']
                name = person_data['name']
                
                # Find Lord
                mp = None
                if member_id:
                    try:
                        mp = Person.objects.get(identifiers__scheme='datadotparl', identifiers__identifier=member_id)
                    except Person.DoesNotExist:
                        pass
                
                if not mp and pims_id:
                    try:
                        mp = Person.objects.get(identifiers__scheme='pims', identifiers__identifier=pims_id)
                    except Person.DoesNotExist:
                        pass
                
                if not mp:
                    # Try name match
                    mp = Person.objects.filter(name__iexact=name).first()
                
                if not mp:
                    # print(f"Warning: Lord not found: {name} (ID: {member_id})")
                    continue
                
                count += 1
                
                for interest in person_data['interests']:
                    cat_id = interest['category_id']
                    
                    # Category 4: Sponsorship (1007)
                    # Category 5: Overseas visits (1008)
                    # Category 6: Gifts (1009)
                    if cat_id not in ['1007', '1008', '1009']:
                        continue
                        
                    interest_id = interest['interest_id']
                    
                    # Check duplication
                    if Donation.objects.filter(identifiers__scheme='lords_interest', identifiers__identifier=interest_id).exists():
                        continue
                        
                    text = interest['registered_interest']
                    created_date = self._parse_date(interest['created'])
                    
                    # Map categories
                    donation_type = "Unknown"
                    if cat_id == '1007':
                        donation_type = "Sponsorship"
                    elif cat_id == '1008':
                        donation_type = "Visit"
                    elif cat_id == '1009':
                        donation_type = "Gift"
                        
                    # Create Donation
                    # value is unknown (0)
                    donation = Donation.objects.create(
                        recipient=mp,
                        donor=None, # Cannot reliably extract from text
                        value=Decimal(0),
                        donation_type=donation_type,
                        nature_of_donation=text[:128], # Truncate to fit field
                        accepted_date=created_date,
                        is_bequest=False,
                        is_aggregation=False,
                        is_sponsorship=(cat_id == '1007'),
                        accounting_units_as_central_party=False
                    )
                    
                    # Store full text in Note if it was truncated?
                    # Or just rely on source/link?
                    # We can store full text in a Note if truncated.
                    if len(text) > 128:
                        models.Note.objects.create(
                            content_object=donation,
                            content=text
                        )
                    
                    Identifier.objects.create(
                        content_object=donation,
                        scheme='lords_interest',
                        identifier=interest_id
                    )
            
            print(f"Matched {count} Lords.")

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')
        target_file = options.get('file')

        if target_file:
            self._import_data([target_file])
            return

        print("Downloading Lords’ Interests ...")
        files = self._download_lords_interests()
        
        if files:
            self._import_data(files)
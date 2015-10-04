import re
from os.path import join, exists

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import Electoral Commission data'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')

    data_directory = join(settings.BASE_DIR, 'datafetch', 'data')

    donation_source_tmpl = "http://search.electoralcommission.org.uk/English/Donations/{}"
    reg_source_tmpl = "http://{}.electoralcommission.org.uk/English/Registrations/{}"

    # from dd-mm-(yy)yy to yyyy-mm-dd
    def _parse_date(self, date):
        if not date:
            return None
        date = "{}-{}-{}".format(date[6:], date[3:5], date[:2])
        if len(date) == 8:
            date = "20" + date
        return date

    def _get_or_create_reg_num_id(self, reg_num):
        reg_num = reg_num.upper()
        while len(reg_num) < 8:
            reg_num = '0' + reg_num
        id_ = {'identifier': reg_num, 'scheme': "companieshouse"}
        return models.Identifier.objects.get_or_create(**id_)

    def _process_donor(self, donation):
        ec_identifier = None
        reg_ent = self.registered_entities_dict.get(donation['donor_name'])
        if reg_ent:
            # check if the donor is already in the database
            ec_identifier, created = models.Identifier.objects.get_or_create(identifier=reg_ent["ecref"], scheme="electoralcommission")
            if not created:
                # if it is, return it
                try:
                    return models.Organization.objects.get(identifiers=ec_identifier)
                except models.Organization.DoesNotExist:
                    return models.Person.objects.get(identifiers=ec_identifier)

        reg_num_identifier = None
        if donation.get('company_registration_number'):
            reg_num_identifier, created = self._get_or_create_reg_num_id(donation['company_registration_number'])
            if not created:
                org = models.Organization.objects.get(identifiers=reg_num_identifier)
                if ec_identifier:
                    org.identifiers.add(ec_identifier)
                return org

        if donation['donor_status'] == 'Individual':
            donor_type = 'person'
            donor, created = self._process_individual(donation['donor_name'])
        else:
            donor_type = 'organization'
            donor_dict = {
                'name': donation['donor_name'].strip(),
                'classification': donation['donor_status'],
            }
            donor, created = models.Organization.objects.get_or_create(name=donor_dict['name'], defaults=donor_dict)

        if ec_identifier:
            donor.identifiers.add(ec_identifier)

        if reg_num_identifier:
            donor.identifiers.add(reg_num_identifier)

        if created:
            if donation['postcode']:
                contact = models.ContactDetail.objects.create(contact_type='address', value=donation['postcode'])
                donor.contact_details.add(contact)

            note_content = "This {} was auto-generated when scraping the donor register.".format(donor_type)
            note = models.Note.objects.create(content=note_content)
            donor.notes.add(note)

        return donor

    def _process_individual(self, name):
        stripped_name, person_dict = helpers.parse_name(name)
        person = models.Person.objects.filter(Q(other_names__name=person_dict['name']) | Q(other_names__name=stripped_name))
        if person:
            person = person[0]
            dirty = False
            if person_dict.get('honorific_prefix') and not person.honorific_prefix:
                person.honorific_prefix = person_dict['honorific_prefix']
                dirty = True
            if person_dict.get('gender') and not person.gender:
                person.gender = person_dict['gender']
                dirty = True
            if dirty:
                person.save()
            created = False
        else:
            # create a new person
            person = models.Person.objects.create(**person_dict)
            name = models.OtherName.objects.create(name=person_dict['name'])
            person.other_names.add(name)
            if stripped_name != person_dict['name']:
                other_name = models.OtherName.objects.create(name=stripped_name)
                person.other_names.add(other_name)
            created = True
        return person, created

    def _process_org_recipient(self, donation, reg_ent):
        recipient_dict = {}
        recipient_dict['name'], deregistered = re.match(r'^(.*?)(?: \[De-registered ([^\]]*)\])?$', donation['regulated_entity_name']).groups()
        if deregistered:
            recipient_dict['dissolution_date'] = self._parse_date(deregistered)

        recipient_dict['classification'] = donation.get('regulated_donee_type')
        if not recipient_dict['classification']:
            recipient_dict['classification'] = donation.get('regulated_entity_type')

        if reg_ent:
            reg_num_identifier = None
            if reg_ent['company_registration_number']:
                reg_num_identifier, created = self._get_or_create_reg_num_id(reg_ent['company_registration_number'])
                if not created:
                    # We already have a log of this company number, but the
                    # company may have had a different name or be from a
                    # different source
                    recipient = models.Organization.objects.get(identifiers=reg_num_identifier)
                    return recipient, created

            # This isn't _really_ the founding date...
            # Might not be a good idea to set this here.
            recipient_dict['founding_date'] = self._parse_date(reg_ent['approved_date'])
            recipient, created = models.Organization.objects.get_or_create(name=recipient_dict['name'], defaults=recipient_dict)
            if reg_num_identifier:
                recipient.identifiers.add(reg_num_identifier)
        else:
            # Get or create an organization based on the name only
            recipient, created = models.Organization.objects.get_or_create(name=recipient_dict['name'], defaults=recipient_dict)

        return recipient, created

    def _process_recipient(self, donation):
        # look the recipient up in the registered entities dict
        ec_identifier = None
        reg_ent = self.registered_entities_dict.get(donation['regulated_entity_name'])
        if reg_ent:
            # check if the recipient is already in the database
            ec_identifier, created = models.Identifier.objects.get_or_create(identifier=reg_ent["ecref"], scheme="electoralcommission")
            if not created:
                # if it is, return it
                try:
                    return models.Organization.objects.get(identifiers=ec_identifier)
                except models.Organization.DoesNotExist:
                    return models.Person.objects.get(identifiers=ec_identifier)

        if donation['regulated_entity_type'] == 'Regulated Donee' and donation['regulated_donee_type'] != 'Members Association':
            # Individual recipient e.g. MPs, MEPs
            recipient, created = self._process_individual(donation['regulated_entity_name'])
            note_content = "This person was auto-generated when scraping the donor register.\n\nThey had donee type: '{}'.".format(donation['regulated_donee_type'])
        else:
            # Organizational recipient e.g. political parties

            # Known bug: There is ONE individual in this category:
            #  - C0106416
            # This recipient is a "Permitted Participant" rather than
            # a "Regulated Donee".

            recipient, created = self._process_org_recipient(donation, reg_ent)
            note_content = "This organization was auto-generated when scraping the donor register."

        if ec_identifier:
            recipient.identifiers.add(ec_identifier)

        if created:
            note = models.Note.objects.create(content=note_content)
            recipient.notes.add(note)

        return recipient

    def _save_donation(self, donor, recipient, donation):
        id_ = donation["ecref"]
        identifier = models.Identifier.objects.create(identifier=id_, scheme="electoralcommission")

        donation_dict = {
            "value": donation['value'][1:].replace(',', ''),
            "donation_type": donation['donation_type'],
            "nature_of_donation": donation['nature_of_donation'],
            "influenced_by": donor,
            "influences": recipient,
            "source": self.donation_source_tmpl.format(id_),
            "received_date": self._parse_date(donation["received_date"]),
            "accepted_date": self._parse_date(donation["accepted_date"]),
            "reported_date": self._parse_date(donation["reported_date"]),
            "purpose_of_visit": donation['purpose_of_visit'],
            "accounting_unit_name": donation['accounting_unit_name'],
            "accounting_units_as_central_party": donation['accounting_units_as_central_party'] == "True",
            "is_bequest": donation['is_bequest'] == "True",
            "is_aggregation": donation['is_aggregation'] == "True",
            "is_sponsorship": donation['is_sponsorship'] == "True",
        }

        # create the donation
        d = models.Donation.objects.create(**donation_dict)
        # add the identifier
        d.identifiers.add(identifier)

    def _process_donations(self, donations):
        recipient_dict = {}
        # ^(?:The )?co-operati[cv]e
        donor_dict = {}
        total = len(donations)
        all_ids = [x.identifier for x in models.Identifier.objects.filter(scheme="electoralcommission")]
        for i, donation in enumerate(donations):
            print('{} ({} / {})'.format(donation['ecref'], i, total))
            if donation['ecref'] in all_ids:
                # skip this - we have it already.
                continue
            if donation['donation_action']:
                # if there's anything in this column, it seems the
                # donation wasn't made. I guess we can ignore these.
                continue
            if not donation['donor_name']:
                # this happens when donations are not reported individually
                donor = None
            else:
                donor = donor_dict.get(donation['donor_name'])
                if not donor:
                    donor = self._process_donor(donation)
                    donor_dict[donation['donor_name']] = donor

            recipient = recipient_dict.get(donation['regulated_entity_name'])
            if not recipient:
                recipient = self._process_recipient(donation)
                recipient_dict[donation['regulated_entity_name']] = recipient

            self._save_donation(donor, recipient, donation)

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')

        donations_url = "http://search.electoralcommission.org.uk/api/csv/Donations"
        donations = helpers.fetch_ec_csv(donations_url, "ec.csv", self.refresh)

        registrations_url = "http://search.electoralcommission.org.uk/api/csv/Registrations"
        registered_entities = helpers.fetch_ec_csv(registrations_url, "ec_reg.csv", self.refresh)
        # TODO: this is a bit too simple at the moment.
        # If there are multiple entities with the same name
        # listed, an arbitrary one will be used.
        self.registered_entities_dict = {v['regulated_entity_name']: v for v in registered_entities}

        print("Processing donations ...")
        self._process_donations(donations)

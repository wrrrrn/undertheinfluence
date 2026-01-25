import datetime
from django.core.management.base import BaseCommand, CommandError

from datafetch import models, helpers
from datafetch.utils.normalization import normalize_actor_name


class Command(BaseCommand):
    help = 'Import ParlParse data'

    def add_arguments(self, parser):
        parser.add_argument('--since', nargs='?', type=int)
        parser.add_argument('--refresh', action='store_true')

    def _create_name_dict(self, n, name):
        name_dict = dict(n)
        name_dict['name'] = name
        return name_dict

    def _convert_other_name(self, name_dict):
        primary_name = None
        other_names = {}
        other_name_dict = {x: name_dict.get(x) for x in ['note', 'start_date', 'end_date']}

        if name_dict.get('surname'):
            # fix the mixed usage of these
            name_dict['family_name'] = name_dict['surname']
        if name_dict.get('lordname') and not name_dict.get('family_name'):
            # if a person has a lordname but no family_name,
            # it’s their family_name
            name_dict['family_name'] = name_dict['lordname']

        if name_dict.get('additional_name') and name_dict.get('family_name'):
            name = "{} {}".format(name_dict.get('additional_name'), name_dict.get('family_name'))
            other_names[name] = self._create_name_dict(other_name_dict, name)

        if name_dict.get('honorific_prefix'):
            # I think lordofname_full is the title they've been given
            # but haven't taken so we can ignore it.
            if name_dict.get('lordname'):
                name = "{} {}".format(name_dict['honorific_prefix'], name_dict['lordname'])
                if name_dict.get('lordofname'):
                    name += " of {}".format(name_dict['lordofname'])
            elif name_dict.get('lordofname'):
                name = "{} of {}".format(name_dict['honorific_prefix'], name_dict['lordofname'])
            elif name_dict.get('family_name'):
                name = "{} {}".format(name_dict['honorific_prefix'], name_dict['family_name'])
            else:
                # this happens when we just have a family_name.
                # TODO, though for now I _think_ we can ignore these.
                pass
            other_names[name] = self._create_name_dict(other_name_dict, name)

        if name_dict.get('given_name') and name_dict.get('family_name'):
            name = "{} {}".format(name_dict.get('given_name'), name_dict.get('family_name'))
            other_names[name] = self._create_name_dict(other_name_dict, name)

        if name_dict.get('name'):
            name = name_dict.get('name')
            other_names[name] = self._create_name_dict(other_name_dict, name)

        if name_dict.get("note") == "Main" and name_dict.get('end_date', '9999-12-31'):
            name_dict['name'] = name
            primary_name = name_dict
        return other_names.values(), primary_name

    def _process_people(self, people):
        person_rels = {
            'identifiers': models.Identifier,
            'other_names': models.OtherName,
            'shortcuts': None,
        }

        people_dict = {}
        for person in people:
            id_ = person['id']
            del person['id']
            if id_.endswith("13935"):
                # Ignore the Queen (partly because her
                # official name is vv long)
                continue
            if person.get('redirect'):
                # TODO
                continue

            identifier_dict = dict(zip(('scheme', 'identifier'), id_.split('/', 1)))

            other_names = []
            for n in person.get('other_names', []):
                o, primary_name = self._convert_other_name(n)
                if primary_name:
                    name_dict = primary_name
                other_names += o
            person['other_names'] = other_names

            for x in ['given_name', 'additional_name', 'family_name', 'honorific_prefix', 'honorific_suffix']:
                if name_dict.get(x):
                    person[x] = name_dict[x]
            person['name'] = name_dict.get('name')
            # TODO: sort_name

            person_data = {k: v for k, v in person.items() if k not in person_rels.keys()}

            # Normalize the name for consistency
            if person_data.get('name'):
                person_data['name'] = normalize_actor_name(person_data['name'], strength='strong')

            # Deduplicate by identifier FIRST to avoid creating duplicates
            try:
                identifier = models.Identifier.objects.get(**identifier_dict)
                p = models.Person.objects.get(pk=identifier.object_id)
                for k, v in person_data.items():
                    setattr(p, k, v)
                p.save()
            except (models.Identifier.DoesNotExist, models.Person.DoesNotExist):
                p = models.Person.objects.create(**person_data)
                p.identifiers.create(**identifier_dict)

            for rel_id, rel_model in person_rels.items():
                if not rel_model or rel_id == 'identifiers':
                    continue
                for rel_dict in person.get(rel_id, []):
                    getattr(p, rel_id).get_or_create(**rel_dict)

            people_dict[id_] = p.id
        return people_dict

    def _process_organizations(self, organizations):
        org_rels = {
            'identifiers': models.Identifier,
            'other_names': models.OtherName,
        }

        organizations_dict = {}
        for organization in organizations:
            if organization.get('classification') == 'party':
                organization['classification'] = 'Political Party'
            id_ = organization.pop('id')

            org_data = {k: v for k, v in organization.items() if k not in org_rels.keys()}

            # Normalize organization name for consistency
            if org_data.get('name'):
                org_data['name'] = normalize_actor_name(org_data['name'], strength='strong')

            # Try to find by identifier first to avoid duplicates
            identifier_dict = None
            for identifier in organization.get('identifiers', []):
                if identifier.get('identifier') and identifier.get('scheme'):
                    identifier_dict = {'identifier': identifier['identifier'], 'scheme': identifier['scheme']}
                    break

            if identifier_dict:
                try:
                    existing_identifier = models.Identifier.objects.get(**identifier_dict)
                    o = models.Organization.objects.get(pk=existing_identifier.object_id)
                    # Update existing org with new data
                    for k, v in org_data.items():
                        setattr(o, k, v)
                    o.save()
                    created = False
                except (models.Identifier.DoesNotExist, models.Organization.DoesNotExist):
                    o, created = models.Organization.objects.get_or_create(name=org_data['name'], defaults=org_data)
            else:
                o, created = models.Organization.objects.get_or_create(name=org_data['name'], defaults=org_data)

            for rel_id, rel_model in org_rels.items():
                if not rel_model:
                    continue
                for rel_dict in organization.get(rel_id, []):
                    rel, _ = getattr(o, rel_id).get_or_create(**rel_dict)

            organizations_dict[id_] = o.id
        return organizations_dict 
    
        # for organization in organizations:
        #     if organization.get('classification') == 'party':
        #         organization['classification'] = 'Political Party'
        #     id_ = organization.pop('id')

        #     org_data = {k: v for k, v in organization.items() if k not in org_rels.keys()}

        #     if id_ in party_lookup:
        #         ec_identifier, org_data["name"] = party_lookup[id_]
        #         identifier_dict = {'identifier': ec_identifier, 'scheme': 'electoralcommission'}
        #         try:
        #             identifier = models.Identifier.objects.get(**identifier_dict)
        #             o = models.Organization.objects.get(pk=identifier.object_id)
        #         except (models.Identifier.DoesNotExist, models.Organization.DoesNotExist):
        #             o = models.Organization.objects.create(**org_data)
        #             o.identifiers.create(**identifier_dict)
        #     else:
        #         o, _ = models.Organization.objects.get_or_create(name=org_data.get('name'), defaults=org_data)

        #     for rel_id, rel_model in org_rels.items():
        #         if not rel_model or rel_id == 'identifiers':
        #             continue
        #         for rel_dict in organization.get(rel_id, []):
        #             rel, _ = getattr(o, rel_id).get_or_create(**rel_dict)

        #     organizations_dict[id_] = o.id
        # return organizations_dict

    def _process_posts(self, posts, j):
        ignore_fields = ('id', 'area', 'identifiers',)
        unique_fields = ("label", "organization_id", "start_date",)

        posts_dict = {}
        for post in posts:
            id_ = post['id']
            post['organization_id'] = j['organizations'][post['organization_id']]
            defaults = {k: v for k, v in post.items() if k not in ignore_fields}
            unique = {k: v for k, v in defaults.items() if k in unique_fields}
            p, created = models.Post.objects.get_or_create(defaults=defaults, **unique)
            posts_dict[id_] = p
        return posts_dict

    def _process_memberships(self, memberships, j):
        ignore_fields = ('id', 'identifiers', 'start_reason', 'end_reason', 'redirect', 'name', 'source',)
        unique_fields = ('person_id', 'post_id', 'organization_id', 'on_behalf_of_id', 'start_date',)

        for membership in memberships:
            if membership.get('role') == 'Queen':
                # Ignore the Queen
                continue
            if membership.get('redirect'):
                # TODO
                continue

            if membership.get('post_id'):
                post = j['posts'][membership['post_id']]
                membership['post_id'] = post.id
                membership['role'] = post.label
                membership['organization_id'] = post.organization_id
            else:
                membership['organization_id'] = j['organizations'][membership['organization_id']]

            if membership.get('person_id'):
                membership['person_id'] = j['persons'][membership['person_id']]

            if membership.get('on_behalf_of_id'):
                membership['on_behalf_of_id'] = j['organizations'][membership['on_behalf_of_id']]

            # Validate date order (start_date <= end_date)
            start_date = membership.get('start_date')
            end_date = membership.get('end_date')
            if start_date and end_date:
                try:
                    start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                    end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                    if end < start:
                        # Swap dates if they are in the wrong order
                        print(f"Swapping invalid dates for membership: {start_date} -> {end_date}")
                        membership['start_date'] = end_date
                        membership['end_date'] = start_date
                except ValueError:
                    # Ignore partial dates or other formats
                    pass

            defaults = {k: v for k, v in membership.items() if k not in ignore_fields}
            unique = {k: v for k, v in defaults.items() if k in unique_fields}

            models.Membership.objects.get_or_create(defaults=defaults, **unique)

    def handle(self, *args, **options):
        self.refresh = options.get('refresh')

        # RawGit CDN was shut down, use GitHub raw content directly
        url = "https://raw.githubusercontent.com/mysociety/parlparse/master/members/people.json"
        filename = "people.json"
        j = helpers.fetch_json(url, filename, refresh=self.refresh)

        since = options.get('since')
        if since:
            print("Importing since {} ...".format(since))
            # get a very stripped down version of memberships
            memberships = [x for x in j['memberships'] if x.get('end_date', '9999-12-31') >= str(since) and not x.get('redirect')]
            data = {}
            for k in ['persons', 'posts']:
                data[k] = {x['id']: x for x in j[k]}
            # get a stripped down version of persons
            data['persons'] = {x['person_id']: data['persons'][x['person_id']] for x in memberships if'person_id' in x}
            j['persons'] = data['persons'].values()
            # now get all the memberships for which our persons are involved
            j['memberships'] = [x for x in j['memberships'] if x.get('person_id') in data['persons']]
            j['posts'] = {x['post_id']: data['posts'][x['post_id']] for x in j['memberships'] if 'post_id' in x}.values()

        print("Processing people ...")
        j['persons'] = self._process_people(j['persons'])

        print("Processing organizations ...")
        j['organizations'] = self._process_organizations(j['organizations'])

        print("Processing posts ...")
        j['posts'] = self._process_posts(j['posts'], j)

        print("Processing memberships ...")
        self._process_memberships(j['memberships'], j)

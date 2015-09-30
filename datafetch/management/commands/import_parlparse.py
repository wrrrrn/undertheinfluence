import json
from os.path import join, exists
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests
from datafetch import models


class Command(BaseCommand):
    help = 'Import ParlParse data'
    data_directory = join(settings.BASE_DIR, 'datafetch', 'data')
    refresh = False

    def add_arguments(self, parser):
        parser.add_argument('--since', nargs='?', type=int)

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

            identifier = dict(zip(('scheme', 'identifier'), id_.split('/', 1)))
            identifier, created = models.Identifier.objects.get_or_create(identifier=identifier['identifier'], defaults=identifier)

            other_names = []
            for n in person.get('other_names', []):
                o, primary_name = self._convert_other_name(n)
                other_names += o
                if primary_name:
                    name_dict = primary_name
            person['other_names'] = other_names

            if name_dict.get('given_name'):
                person['given_name'] = name_dict.get('given_name')
            if name_dict.get('additional_name'):
                person['additional_name'] = name_dict.get('additional_name')
            if name_dict.get('family_name'):
                person['family_name'] = name_dict.get('family_name')
            if name_dict.get('honorific_prefix'):
                person['honorific_prefix'] = name_dict.get('honorific_prefix')
            if name_dict.get('honorific_suffix'):
                person['honorific_suffix'] = name_dict.get('honorific_suffix')
            person['name'] = name_dict.get('name')
            # TODO: sort_name

            if not created:
                p = models.Person.objects.get(identifiers=identifier)
            else:
                p = models.Person.objects.create(**{k: v for k, v in person.items() if k not in person_rels.keys()})
                p.identifiers.add(identifier)
            for rel_id, rel_model in person_rels.items():
                if not rel_model:
                    continue
                for rel_dict in person.get(rel_id, []):
                    if rel_id == 'Identifier' and rel_dict.get('scheme').endswith('_id'):
                        rel_dict['scheme'] = rel_dict['scheme'][:-3]
                    getattr(p, rel_id).add(rel_model.objects.get_or_create(defaults=rel_dict, **rel_dict)[0])
            people_dict[id_] = p.id
        return people_dict

    def _process_organizations(self, organizations):
        organizations_dict = {}
        organizations += [{
            'id': 'house-of-commons',
            'name': 'House of Commons',
            'classification': 'Legislature',
        }, {
            'id': 'house-of-lords',
            'name': 'House of Lords',
            'classification': 'Legislature',
        }, {
            'id': 'scottish-parliament',
            'name': 'Scottish Parliament',
            'classification': 'Legislature',
        }, {
            'id': 'northern-ireland-assembly',
            'name': 'Northern Ireland Assembly',
            'classification': 'Legislature',
        }]
        for organization in organizations:
            if organization['classification'] == 'party':
                organization['classification'] = 'Political Party'
            id_ = organization['id']
            del organization['id']
            o, created = models.Organization.objects.get_or_create(**organization)
            organizations_dict[id_] = o.id
        return organizations_dict

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
        ignore_fields = ('id', 'identifiers', 'start_reason', 'end_reason', 'redirect',)
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
                membership['organization_id'] = post.organization_id
            else:
                membership['organization_id'] = j['organizations'][membership['organization_id']]

            if membership.get('person_id'):
                membership['person_id'] = j['persons'][membership['person_id']]

            if membership.get('on_behalf_of_id'):
                membership['on_behalf_of_id'] = j['organizations'][membership['on_behalf_of_id']]

            defaults = {k: v for k, v in membership.items() if k not in ignore_fields}
            unique = {k: v for k, v in defaults.items() if k in unique_fields}

            m, created = models.Membership.objects.get_or_create(defaults=defaults, **unique)

    def handle(self, *args, **options):
        filepath = join(self.data_directory, 'people.json')
        if exists(filepath) and not self.refresh:
            with open(filepath) as f:
                j = json.load(f)
        else:
            url = "https://cdn.rawgit.com/mysociety/parlparse/master/members/people.json"
            r = requests.get(url)
            time.sleep(0.5)
            with open(filepath, "w") as f:
                f.write(r.text)
            j = r.json()

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

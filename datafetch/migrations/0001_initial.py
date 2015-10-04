# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.core.validators
import datafetch.models.popolo.behaviors
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('name', models.CharField(help_text="A person or organization's preferred full name", max_length=512, verbose_name='name')),
                ('image', models.URLField(help_text='An image representing the person or organization', blank=True, verbose_name='image', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('name', models.CharField(help_text='A primary name', blank=True, max_length=256, verbose_name='name')),
                ('identifier', models.CharField(help_text='An issued identifier', blank=True, max_length=512, verbose_name='identifier')),
                ('classification', models.CharField(help_text='An area category, e.g. city', blank=True, max_length=512, verbose_name='identifier')),
                ('geom', models.TextField(help_text='A geometry', blank=True, verbose_name='geom', null=True)),
                ('inhabitants', models.IntegerField(help_text='The total number of inhabitants', blank=True, verbose_name='inhabitants', null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
                ('parent', models.ForeignKey(to='datafetch.Area', null=True, help_text='The area that contains this area', blank=True, related_name='children')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AreaI18Name',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('area', models.ForeignKey(to='datafetch.Area', related_name='i18n_names')),
            ],
            options={
                'verbose_name': 'I18N Name',
                'verbose_name_plural': 'I18N Names',
            },
        ),
        migrations.CreateModel(
            name='ContactDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A human-readable label for the contact detail', blank=True, max_length=512, verbose_name='label')),
                ('contact_type', models.CharField(help_text="A type of medium, e.g. 'fax' or 'email'", choices=[('ADDRESS', 'Address'), ('EMAIL', 'Email'), ('URL', 'Url'), ('MAIL', 'Snail mail'), ('TWITTER', 'Twitter'), ('FACEBOOK', 'Facebook'), ('PHONE', 'Telephone'), ('MOBILE', 'Mobile'), ('TEXT', 'Text'), ('VOICE', 'Voice'), ('FAX', 'Fax'), ('CELL', 'Cell'), ('VIDEO', 'Video'), ('PAGER', 'Pager'), ('TEXTPHONE', 'Textphone')], max_length=12, verbose_name='type')),
                ('value', models.CharField(help_text='A value, e.g. a phone number or email address', max_length=512, verbose_name='value')),
                ('note', models.CharField(help_text='A note, e.g. for grouping contact details by physical location', blank=True, max_length=512, verbose_name='note')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Identifier',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('identifier', models.CharField(help_text='An issued identifier, e.g. a DUNS number', max_length=512, verbose_name='identifier')),
                ('scheme', models.CharField(help_text='An identifier scheme, e.g. DUNS', blank=True, max_length=128, verbose_name='scheme')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('dbpedia_resource', models.CharField(help_text='DbPedia URI of the resource', max_length=255, unique=True)),
                ('iso639_1_code', models.CharField(max_length=2)),
                ('name', models.CharField(help_text='English name of the language', max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(help_text='A URL', max_length=350, verbose_name='url')),
                ('note', models.CharField(help_text="A note, e.g. 'Wikipedia page'", blank=True, max_length=512, verbose_name='note')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the membership', blank=True, max_length=512, verbose_name='label')),
                ('role', models.CharField(help_text='The role that the person fulfills in the organization', blank=True, max_length=512, verbose_name='role')),
                ('area', models.ForeignKey(to='datafetch.Area', null=True, help_text='The geographic area to which the post is related', blank=True, related_name='memberships')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('content', models.TextField(help_text='A note about this person or organization', blank=True, verbose_name='content')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OtherName',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('name', models.CharField(help_text='An alternate or former name', max_length=512, verbose_name='name')),
                ('note', models.CharField(help_text="A note, e.g. 'Birth name'", blank=True, max_length=1024, verbose_name='note')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the post', blank=True, max_length=512, verbose_name='label')),
                ('other_label', models.CharField(help_text='An alternate label, such as an abbreviation', blank=True, verbose_name='other label', null=True, max_length=512)),
                ('role', models.CharField(help_text='The function that the holder of the post fulfills', blank=True, max_length=512, verbose_name='role')),
                ('area', models.ForeignKey(to='datafetch.Area', null=True, help_text='The geographic area to which the post is related', blank=True, related_name='posts')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Relationship',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', null=True, verbose_name='start date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', null=True, verbose_name='end date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='Date has wrong format', regex='^[0-9]{4}(-[0-9]{2}){0,2}$'), datafetch.models.popolo.behaviors.validate_partial_date])),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the relationship', blank=True, max_length=512, verbose_name='label')),
                ('source', models.URLField(help_text='URL to the source that documents the relationship', blank=True, verbose_name='source', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(help_text='A URL', verbose_name='url')),
                ('note', models.CharField(help_text="A note, e.g. 'Parliament website'", blank=True, max_length=512, verbose_name='note')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('relationship_ptr', models.OneToOneField(parent_link=True, to='datafetch.Relationship', auto_created=True, primary_key=True, serialize=False)),
                ('value', models.DecimalField(max_digits=12, help_text='The monetary value of the donation', decimal_places=2, blank=True, verbose_name='value')),
                ('donation_type', models.CharField(help_text='The type of donation e.g. cash', max_length=128, verbose_name='donation type')),
                ('nature_of_donation', models.CharField(help_text='The nature of the donation e.g. hospitality', blank=True, max_length=128, verbose_name='nature of donation')),
                ('received_date', models.DateField(blank=True, verbose_name='received date', null=True)),
                ('accepted_date', models.DateField(blank=True, verbose_name='accepted date', null=True)),
                ('reported_date', models.DateField(blank=True, verbose_name='reported date', null=True)),
                ('accounting_unit_name', models.CharField(blank=True, max_length=128, verbose_name='accounting unit name')),
                ('accounting_units_as_central_party', models.BooleanField(verbose_name='accounting units as central party')),
                ('purpose_of_visit', models.CharField(blank=True, max_length=512, verbose_name='purpose of visit')),
                ('is_bequest', models.BooleanField(verbose_name='is bequest')),
                ('is_aggregation', models.BooleanField(verbose_name='is aggregation')),
                ('is_sponsorship', models.BooleanField(verbose_name='is sponsorship')),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.relationship',),
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('actor_ptr', models.OneToOneField(parent_link=True, to='datafetch.Actor', auto_created=True, primary_key=True, serialize=False)),
                ('summary', models.CharField(help_text='A one-line description of an organization', blank=True, max_length=1024, verbose_name='summary')),
                ('description', models.TextField(help_text='An extended description of an organization', blank=True, verbose_name='biography')),
                ('classification', models.CharField(help_text='An organization category, e.g. committee', blank=True, max_length=512, verbose_name='classification')),
                ('founding_date', models.CharField(help_text='A date of founding', null=True, verbose_name='founding date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', regex='^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_founding_date')])),
                ('dissolution_date', models.CharField(help_text='A date of dissolution', null=True, verbose_name='dissolution date', blank=True, max_length=10, validators=[django.core.validators.RegexValidator(message='dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', regex='^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_dissolution_date')])),
                ('area', models.ForeignKey(to='datafetch.Area', null=True, help_text='The geographic area to which this organization is related', blank=True, related_name='organizations')),
                ('parent', models.ForeignKey(to='datafetch.Organization', null=True, help_text='The organization that contains this organization', blank=True, related_name='children')),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.actor',),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('actor_ptr', models.OneToOneField(parent_link=True, to='datafetch.Actor', auto_created=True, primary_key=True, serialize=False)),
                ('family_name', models.CharField(help_text='One or more family names', blank=True, max_length=128, verbose_name='family name')),
                ('given_name', models.CharField(help_text='One or more primary given names', blank=True, max_length=128, verbose_name='given name')),
                ('additional_name', models.CharField(help_text='One or more secondary given names', blank=True, max_length=128, verbose_name='additional name')),
                ('honorific_prefix', models.CharField(help_text="One or more honorifics preceding a person's name", blank=True, max_length=128, verbose_name='honorific prefix')),
                ('honorific_suffix', models.CharField(help_text="One or more honorifics following a person's name", blank=True, max_length=128, verbose_name='honorific suffix')),
                ('patronymic_name', models.CharField(help_text='One or more patronymic names', blank=True, max_length=128, verbose_name='patronymic name')),
                ('sort_name', models.CharField(help_text='A name to use in an lexicographically ordered list', blank=True, max_length=128, verbose_name='sort name')),
                ('email', models.EmailField(help_text='A preferred email address', blank=True, verbose_name='email', null=True, max_length=254)),
                ('gender', models.CharField(help_text='A gender', blank=True, max_length=128, verbose_name='gender')),
                ('birth_date', models.CharField(help_text='A date of birth', blank=True, max_length=10, verbose_name='birth date')),
                ('death_date', models.CharField(help_text='A date of death', blank=True, max_length=10, verbose_name='death date')),
                ('summary', models.CharField(help_text="A one-line account of a person's life", blank=True, max_length=1024, verbose_name='summary')),
                ('biography', models.TextField(help_text="An extended account of a person's life", blank=True, verbose_name='biography')),
                ('national_identity', models.CharField(help_text='A national identity', blank=True, verbose_name='national identity', null=True, max_length=128)),
            ],
            options={
                'verbose_name_plural': 'People',
            },
            bases=('datafetch.actor',),
        ),
        migrations.AddField(
            model_name='relationship',
            name='influenced_by',
            field=models.ForeignKey(related_name='influences', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='relationship',
            name='influences',
            field=models.ForeignKey(related_name='influenced_by', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='relationship',
            name='polymorphic_ctype',
            field=models.ForeignKey(to='contenttypes.ContentType', null=True, related_name='polymorphic_datafetch.relationship_set+', editable=False),
        ),
        migrations.AddField(
            model_name='membership',
            name='post',
            field=models.ForeignKey(to='datafetch.Post', null=True, help_text='The post held by the person in the organization through this membership', blank=True, related_name='memberships'),
        ),
        migrations.AddField(
            model_name='areai18name',
            name='language',
            field=models.ForeignKey(to='datafetch.Language'),
        ),
        migrations.AddField(
            model_name='actor',
            name='content_type',
            field=models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='actor',
            name='polymorphic_ctype',
            field=models.ForeignKey(to='contenttypes.ContentType', null=True, related_name='polymorphic_datafetch.actor_set+', editable=False),
        ),
        migrations.AddField(
            model_name='actor',
            name='relationships',
            field=models.ManyToManyField(help_text='Relationships involving the person or organization', to='datafetch.Actor', through='datafetch.Relationship'),
        ),
        migrations.AddField(
            model_name='post',
            name='organization',
            field=models.ForeignKey(to='datafetch.Organization', related_name='posts', help_text='The organization in which the post is held'),
        ),
        migrations.AddField(
            model_name='membership',
            name='on_behalf_of',
            field=models.ForeignKey(to='datafetch.Organization', null=True, help_text='The organization on whose behalf the person is a party to the relationship', blank=True, related_name='memberships_on_behalf_of'),
        ),
        migrations.AddField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(to='datafetch.Organization', null=True, help_text='The organization that is a party to the relationship', blank=True, related_name='memberships'),
        ),
        migrations.AddField(
            model_name='membership',
            name='person',
            field=models.ForeignKey(to='datafetch.Person', related_name='memberships', help_text='The person who is a party to the relationship', to_field='id'),
        ),
        migrations.AlterUniqueTogether(
            name='areai18name',
            unique_together=set([('area', 'language', 'name')]),
        ),
    ]

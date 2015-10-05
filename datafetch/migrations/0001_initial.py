# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import datafetch.models.popolo.behaviors
import model_utils.fields
import django.core.validators


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
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('name', models.CharField(help_text="A person or organization's preferred full name", verbose_name='name', max_length=512)),
                ('image', models.URLField(help_text='An image representing the person or organization', verbose_name='image', blank=True, null=True)),
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
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('name', models.CharField(help_text='A primary name', verbose_name='name', blank=True, max_length=256)),
                ('identifier', models.CharField(help_text='An issued identifier', verbose_name='identifier', blank=True, max_length=512)),
                ('classification', models.CharField(help_text='An area category, e.g. city', verbose_name='identifier', blank=True, max_length=512)),
                ('geom', models.TextField(help_text='A geometry', verbose_name='geom', blank=True, null=True)),
                ('inhabitants', models.IntegerField(help_text='The total number of inhabitants', verbose_name='inhabitants', blank=True, null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
                ('parent', models.ForeignKey(help_text='The area that contains this area', related_name='children', to='datafetch.Area', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AreaI18Name',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(verbose_name='name', max_length=255)),
                ('area', models.ForeignKey(to='datafetch.Area', related_name='i18n_names')),
            ],
            options={
                'verbose_name_plural': 'I18N Names',
                'verbose_name': 'I18N Name',
            },
        ),
        migrations.CreateModel(
            name='Consultancy',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the relationship', verbose_name='label', blank=True, max_length=512)),
                ('source', models.URLField(help_text='URL to the source that documents the relationship', verbose_name='source', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ContactDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A human-readable label for the contact detail', verbose_name='label', blank=True, max_length=512)),
                ('contact_type', models.CharField(verbose_name='type', help_text="A type of medium, e.g. 'fax' or 'email'", choices=[('address', 'Address'), ('email', 'Email'), ('url', 'Url'), ('mail', 'Snail mail'), ('twitter', 'Twitter'), ('facebook', 'Facebook'), ('phone', 'Telephone'), ('mobile', 'Mobile'), ('text', 'Text'), ('voice', 'Voice'), ('fax', 'Fax'), ('cell', 'Cell'), ('video', 'Video'), ('pager', 'Pager'), ('textphone', 'Textphone')], max_length=12)),
                ('value', models.CharField(help_text='A value, e.g. a phone number or email address', verbose_name='value', max_length=512)),
                ('note', models.CharField(help_text='A note, e.g. for grouping contact details by physical location', verbose_name='note', blank=True, max_length=512)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the relationship', verbose_name='label', blank=True, max_length=512)),
                ('source', models.URLField(help_text='URL to the source that documents the relationship', verbose_name='source', blank=True, null=True)),
                ('value', models.DecimalField(max_digits=12, help_text='The monetary value of the donation', verbose_name='value', blank=True, decimal_places=2)),
                ('donation_type', models.CharField(help_text='The type of donation e.g. cash', verbose_name='donation type', max_length=128)),
                ('nature_of_donation', models.CharField(help_text='The nature of the donation e.g. hospitality', verbose_name='nature of donation', blank=True, max_length=128)),
                ('received_date', models.DateField(verbose_name='received date', blank=True, null=True)),
                ('accepted_date', models.DateField(verbose_name='accepted date', blank=True, null=True)),
                ('reported_date', models.DateField(verbose_name='reported date', blank=True, null=True)),
                ('accounting_unit_name', models.CharField(verbose_name='accounting unit name', blank=True, max_length=128)),
                ('accounting_units_as_central_party', models.BooleanField(verbose_name='accounting units as central party')),
                ('purpose_of_visit', models.CharField(verbose_name='purpose of visit', blank=True, max_length=512)),
                ('is_bequest', models.BooleanField(verbose_name='is bequest')),
                ('is_aggregation', models.BooleanField(verbose_name='is aggregation')),
                ('is_sponsorship', models.BooleanField(verbose_name='is sponsorship')),
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
                ('identifier', models.CharField(help_text='An issued identifier, e.g. a DUNS number', verbose_name='identifier', max_length=512)),
                ('scheme', models.CharField(help_text='An identifier scheme, e.g. DUNS', verbose_name='scheme', blank=True, max_length=128)),
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
                ('dbpedia_resource', models.CharField(help_text='DbPedia URI of the resource', unique=True, max_length=255)),
                ('iso639_1_code', models.CharField(max_length=2)),
                ('name', models.CharField(help_text='English name of the language', max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(help_text='A URL', verbose_name='url', max_length=350)),
                ('note', models.CharField(help_text="A note, e.g. 'Wikipedia page'", verbose_name='note', blank=True, max_length=512)),
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
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the membership', verbose_name='label', blank=True, max_length=512)),
                ('role', models.CharField(help_text='The role that the person fulfills in the organization', verbose_name='role', blank=True, max_length=512)),
                ('area', models.ForeignKey(help_text='The geographic area to which the post is related', related_name='memberships', to='datafetch.Area', blank=True, null=True)),
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
                ('content', models.TextField(help_text='A note about this person or organization', verbose_name='content', blank=True)),
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
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('name', models.CharField(help_text='An alternate or former name', verbose_name='name', max_length=512)),
                ('note', models.CharField(help_text="A note, e.g. 'Birth name'", verbose_name='note', blank=True, max_length=1024)),
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
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, verbose_name='creation time', default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, verbose_name='last modification time', default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the post', verbose_name='label', blank=True, max_length=512)),
                ('other_label', models.CharField(help_text='An alternate label, such as an abbreviation', verbose_name='other label', blank=True, max_length=512, null=True)),
                ('role', models.CharField(help_text='The function that the holder of the post fulfills', verbose_name='role', blank=True, max_length=512)),
                ('area', models.ForeignKey(help_text='The geographic area to which the post is related', related_name='posts', to='datafetch.Area', blank=True, null=True)),
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
                ('note', models.CharField(help_text="A note, e.g. 'Parliament website'", verbose_name='note', blank=True, max_length=512)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('actor_ptr', models.OneToOneField(to='datafetch.Actor', primary_key=True, auto_created=True, parent_link=True, serialize=False)),
                ('summary', models.CharField(help_text='A one-line description of an organization', verbose_name='summary', blank=True, max_length=1024)),
                ('description', models.TextField(help_text='An extended description of an organization', verbose_name='biography', blank=True)),
                ('classification', models.CharField(help_text='An organization category, e.g. committee', verbose_name='classification', blank=True, max_length=512)),
                ('founding_date', models.CharField(help_text='A date of founding', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_founding_date', message='founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$')], verbose_name='founding date', blank=True, max_length=10, null=True)),
                ('dissolution_date', models.CharField(help_text='A date of dissolution', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_dissolution_date', message='dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$')], verbose_name='dissolution date', blank=True, max_length=10, null=True)),
                ('area', models.ForeignKey(help_text='The geographic area to which this organization is related', related_name='organizations', to='datafetch.Area', blank=True, null=True)),
                ('parent', models.ForeignKey(help_text='The organization that contains this organization', related_name='children', to='datafetch.Organization', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.actor',),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('actor_ptr', models.OneToOneField(to='datafetch.Actor', primary_key=True, auto_created=True, parent_link=True, serialize=False)),
                ('family_name', models.CharField(help_text='One or more family names', verbose_name='family name', blank=True, max_length=128)),
                ('given_name', models.CharField(help_text='One or more primary given names', verbose_name='given name', blank=True, max_length=128)),
                ('additional_name', models.CharField(help_text='One or more secondary given names', verbose_name='additional name', blank=True, max_length=128)),
                ('honorific_prefix', models.CharField(help_text="One or more honorifics preceding a person's name", verbose_name='honorific prefix', blank=True, max_length=128)),
                ('honorific_suffix', models.CharField(help_text="One or more honorifics following a person's name", verbose_name='honorific suffix', blank=True, max_length=128)),
                ('patronymic_name', models.CharField(help_text='One or more patronymic names', verbose_name='patronymic name', blank=True, max_length=128)),
                ('sort_name', models.CharField(help_text='A name to use in an lexicographically ordered list', verbose_name='sort name', blank=True, max_length=128)),
                ('email', models.EmailField(help_text='A preferred email address', verbose_name='email', blank=True, max_length=254, null=True)),
                ('gender', models.CharField(help_text='A gender', verbose_name='gender', blank=True, max_length=128)),
                ('birth_date', models.CharField(help_text='A date of birth', verbose_name='birth date', blank=True, max_length=10)),
                ('death_date', models.CharField(help_text='A date of death', verbose_name='death date', blank=True, max_length=10)),
                ('summary', models.CharField(help_text="A one-line account of a person's life", verbose_name='summary', blank=True, max_length=1024)),
                ('biography', models.TextField(help_text="An extended account of a person's life", verbose_name='biography', blank=True)),
                ('national_identity', models.CharField(help_text='A national identity', verbose_name='national identity', blank=True, max_length=128, null=True)),
            ],
            options={
                'verbose_name_plural': 'People',
            },
            bases=('datafetch.actor',),
        ),
        migrations.AddField(
            model_name='membership',
            name='post',
            field=models.ForeignKey(help_text='The post held by the person in the organization through this membership', related_name='memberships', to='datafetch.Post', blank=True, null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='donor',
            field=models.ForeignKey(related_name='donated_to', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='recipient',
            field=models.ForeignKey(related_name='received_donations_from', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='consultancy',
            name='agency',
            field=models.ForeignKey(related_name='consults_for', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='consultancy',
            name='client',
            field=models.ForeignKey(related_name='consultants', to='datafetch.Actor', null=True),
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
            field=models.ForeignKey(editable=False, related_name='polymorphic_datafetch.actor_set+', to='contenttypes.ContentType', null=True),
        ),
        migrations.AddField(
            model_name='post',
            name='organization',
            field=models.ForeignKey(help_text='The organization in which the post is held', related_name='posts', to='datafetch.Organization'),
        ),
        migrations.AddField(
            model_name='membership',
            name='on_behalf_of',
            field=models.ForeignKey(help_text='The organization on whose behalf the person is a party to the relationship', related_name='memberships_on_behalf_of', to='datafetch.Organization', blank=True, null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(help_text='The organization that is a party to the relationship', related_name='memberships', to='datafetch.Organization', blank=True, null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='person',
            field=models.ForeignKey(help_text='The person who is a party to the relationship', related_name='memberships', to='datafetch.Person', to_field='id'),
        ),
        migrations.AlterUniqueTogether(
            name='areai18name',
            unique_together=set([('area', 'language', 'name')]),
        ),
    ]

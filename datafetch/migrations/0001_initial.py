# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields
import datafetch.models.popolo.behaviors
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('name', models.CharField(max_length=512, help_text="A person or organization's preferred full name", verbose_name='name')),
                ('image', models.URLField(help_text='An image representing the person or organization', blank=True, null=True, verbose_name='image')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('name', models.CharField(max_length=256, help_text='A primary name', blank=True, verbose_name='name')),
                ('identifier', models.CharField(max_length=512, help_text='An issued identifier', blank=True, verbose_name='identifier')),
                ('classification', models.CharField(max_length=512, help_text='An area category, e.g. city', blank=True, verbose_name='identifier')),
                ('geom', models.TextField(help_text='A geometry', blank=True, null=True, verbose_name='geom')),
                ('inhabitants', models.IntegerField(help_text='The total number of inhabitants', blank=True, null=True, verbose_name='inhabitants')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
                ('parent', models.ForeignKey(blank=True, null=True, help_text='The area that contains this area', related_name='children', to='datafetch.Area')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AreaI18Name',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
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
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('label', models.CharField(max_length=512, help_text='A label describing the relationship', blank=True, verbose_name='label')),
                ('source', models.URLField(help_text='URL to the source that documents the relationship', blank=True, null=True, verbose_name='source')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ContactDetail',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('label', models.CharField(max_length=512, help_text='A human-readable label for the contact detail', blank=True, verbose_name='label')),
                ('contact_type', models.CharField(max_length=12, help_text="A type of medium, e.g. 'fax' or 'email'", choices=[('address', 'Address'), ('email', 'Email'), ('url', 'Url'), ('mail', 'Snail mail'), ('twitter', 'Twitter'), ('facebook', 'Facebook'), ('phone', 'Telephone'), ('mobile', 'Mobile'), ('text', 'Text'), ('voice', 'Voice'), ('fax', 'Fax'), ('cell', 'Cell'), ('video', 'Video'), ('pager', 'Pager'), ('textphone', 'Textphone')], verbose_name='type')),
                ('value', models.CharField(max_length=512, help_text='A value, e.g. a phone number or email address', verbose_name='value')),
                ('note', models.CharField(max_length=512, help_text='A note, e.g. for grouping contact details by physical location', blank=True, verbose_name='note')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('label', models.CharField(max_length=512, help_text='A label describing the relationship', blank=True, verbose_name='label')),
                ('source', models.URLField(help_text='URL to the source that documents the relationship', blank=True, null=True, verbose_name='source')),
                ('value', models.DecimalField(max_digits=12, decimal_places=2, help_text='The monetary value of the donation', blank=True, verbose_name='value')),
                ('donation_type', models.CharField(max_length=128, help_text='The type of donation e.g. cash', verbose_name='donation type')),
                ('nature_of_donation', models.CharField(max_length=128, help_text='The nature of the donation e.g. hospitality', blank=True, verbose_name='nature of donation')),
                ('received_date', models.DateField(blank=True, null=True, verbose_name='received date')),
                ('accepted_date', models.DateField(blank=True, null=True, verbose_name='accepted date')),
                ('reported_date', models.DateField(blank=True, null=True, verbose_name='reported date')),
                ('accounting_unit_name', models.CharField(max_length=128, blank=True, verbose_name='accounting unit name')),
                ('accounting_units_as_central_party', models.BooleanField(verbose_name='accounting units as central party')),
                ('purpose_of_visit', models.CharField(max_length=512, blank=True, verbose_name='purpose of visit')),
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
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('identifier', models.CharField(max_length=512, help_text='An issued identifier, e.g. a DUNS number', verbose_name='identifier')),
                ('scheme', models.CharField(max_length=128, help_text='An identifier scheme, e.g. DUNS', blank=True, verbose_name='scheme')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('dbpedia_resource', models.CharField(max_length=255, help_text='DbPedia URI of the resource', unique=True)),
                ('iso639_1_code', models.CharField(max_length=2)),
                ('name', models.CharField(max_length=128, help_text='English name of the language')),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(max_length=350, help_text='A URL', verbose_name='url')),
                ('note', models.CharField(max_length=512, help_text="A note, e.g. 'Wikipedia page'", blank=True, verbose_name='note')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('label', models.CharField(max_length=512, help_text='A label describing the membership', blank=True, verbose_name='label')),
                ('role', models.CharField(max_length=512, help_text='The role that the person fulfills in the organization', blank=True, verbose_name='role')),
                ('area', models.ForeignKey(blank=True, null=True, help_text='The geographic area to which the post is related', related_name='memberships', to='datafetch.Area')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('content', models.TextField(help_text='A note about this person or organization', blank=True, verbose_name='content')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OtherName',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('name', models.CharField(max_length=512, help_text='An alternate or former name', verbose_name='name')),
                ('note', models.CharField(max_length=1024, help_text="A note, e.g. 'Birth name'", blank=True, verbose_name='note')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('start_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', max_length=10, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', max_length=10, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(editable=False, default=django.utils.timezone.now, verbose_name='creation time')),
                ('updated_at', model_utils.fields.AutoLastModifiedField(editable=False, default=django.utils.timezone.now, verbose_name='last modification time')),
                ('label', models.CharField(max_length=512, help_text='A label describing the post', blank=True, verbose_name='label')),
                ('other_label', models.CharField(max_length=512, help_text='An alternate label, such as an abbreviation', blank=True, null=True, verbose_name='other label')),
                ('role', models.CharField(max_length=512, help_text='The function that the holder of the post fulfills', blank=True, verbose_name='role')),
                ('area', models.ForeignKey(blank=True, null=True, help_text='The geographic area to which the post is related', related_name='posts', to='datafetch.Area')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(help_text='A URL', verbose_name='url')),
                ('note', models.CharField(max_length=512, help_text="A note, e.g. 'Parliament website'", blank=True, verbose_name='note')),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('actor_ptr', models.OneToOneField(parent_link=True, serialize=False, auto_created=True, to='datafetch.Actor', primary_key=True)),
                ('summary', models.CharField(max_length=1024, help_text='A one-line description of an organization', blank=True, verbose_name='summary')),
                ('description', models.TextField(help_text='An extended description of an organization', blank=True, verbose_name='biography')),
                ('classification', models.CharField(max_length=512, help_text='An organization category, e.g. committee', blank=True, verbose_name='classification')),
                ('founding_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_founding_date')], verbose_name='founding date', max_length=10, help_text='A date of founding')),
                ('dissolution_date', models.CharField(blank=True, null=True, validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_dissolution_date')], verbose_name='dissolution date', max_length=10, help_text='A date of dissolution')),
                ('area', models.ForeignKey(blank=True, null=True, help_text='The geographic area to which this organization is related', related_name='organizations', to='datafetch.Area')),
                ('parent', models.ForeignKey(blank=True, null=True, help_text='The organization that contains this organization', related_name='children', to='datafetch.Organization')),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.actor',),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('actor_ptr', models.OneToOneField(parent_link=True, serialize=False, auto_created=True, to='datafetch.Actor', primary_key=True)),
                ('family_name', models.CharField(max_length=128, help_text='One or more family names', blank=True, verbose_name='family name')),
                ('given_name', models.CharField(max_length=128, help_text='One or more primary given names', blank=True, verbose_name='given name')),
                ('additional_name', models.CharField(max_length=128, help_text='One or more secondary given names', blank=True, verbose_name='additional name')),
                ('honorific_prefix', models.CharField(max_length=128, help_text="One or more honorifics preceding a person's name", blank=True, verbose_name='honorific prefix')),
                ('honorific_suffix', models.CharField(max_length=128, help_text="One or more honorifics following a person's name", blank=True, verbose_name='honorific suffix')),
                ('patronymic_name', models.CharField(max_length=128, help_text='One or more patronymic names', blank=True, verbose_name='patronymic name')),
                ('sort_name', models.CharField(max_length=128, help_text='A name to use in an lexicographically ordered list', blank=True, verbose_name='sort name')),
                ('email', models.EmailField(max_length=254, help_text='A preferred email address', blank=True, null=True, verbose_name='email')),
                ('gender', models.CharField(max_length=128, help_text='A gender', blank=True, verbose_name='gender')),
                ('birth_date', models.CharField(max_length=10, help_text='A date of birth', blank=True, verbose_name='birth date')),
                ('death_date', models.CharField(max_length=10, help_text='A date of death', blank=True, verbose_name='death date')),
                ('summary', models.CharField(max_length=1024, help_text="A one-line account of a person's life", blank=True, verbose_name='summary')),
                ('biography', models.TextField(help_text="An extended account of a person's life", blank=True, verbose_name='biography')),
                ('national_identity', models.CharField(max_length=128, help_text='A national identity', blank=True, null=True, verbose_name='national identity')),
            ],
            options={
                'verbose_name_plural': 'People',
            },
            bases=('datafetch.actor',),
        ),
        migrations.AddField(
            model_name='membership',
            name='post',
            field=models.ForeignKey(blank=True, null=True, help_text='The post held by the person in the organization through this membership', related_name='memberships', to='datafetch.Post'),
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
            field=models.ForeignKey(related_name='consulting_clients', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='consultancy',
            name='client',
            field=models.ForeignKey(related_name='consulting_agencies', to='datafetch.Actor', null=True),
        ),
        migrations.AddField(
            model_name='areai18name',
            name='language',
            field=models.ForeignKey(to='datafetch.Language'),
        ),
        migrations.AddField(
            model_name='actor',
            name='content_type',
            field=models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True),
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
            field=models.ForeignKey(blank=True, null=True, help_text='The organization on whose behalf the person is a party to the relationship', related_name='memberships_on_behalf_of', to='datafetch.Organization'),
        ),
        migrations.AddField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, help_text='The organization that is a party to the relationship', related_name='memberships', to='datafetch.Organization'),
        ),
        migrations.AddField(
            model_name='membership',
            name='person',
            field=models.ForeignKey(to_field='id', help_text='The person who is a party to the relationship', related_name='memberships', to='datafetch.Person'),
        ),
        migrations.AlterUniqueTogether(
            name='areai18name',
            unique_together=set([('area', 'language', 'name')]),
        ),
    ]

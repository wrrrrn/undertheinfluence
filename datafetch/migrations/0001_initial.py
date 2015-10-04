# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datafetch.models.popolo.behaviors
import model_utils.fields
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('name', models.CharField(verbose_name='name', max_length=512, help_text="A person or organization's preferred full name")),
                ('image', models.URLField(verbose_name='image', blank=True, null=True, help_text='An image representing the person or organization')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('name', models.CharField(verbose_name='name', blank=True, max_length=256, help_text='A primary name')),
                ('identifier', models.CharField(verbose_name='identifier', blank=True, max_length=512, help_text='An issued identifier')),
                ('classification', models.CharField(verbose_name='identifier', blank=True, max_length=512, help_text='An area category, e.g. city')),
                ('geom', models.TextField(verbose_name='geom', blank=True, null=True, help_text='A geometry')),
                ('inhabitants', models.IntegerField(verbose_name='inhabitants', blank=True, null=True, help_text='The total number of inhabitants')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
                ('parent', models.ForeignKey(related_name='children', to='datafetch.Area', blank=True, help_text='The area that contains this area', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AreaI18Name',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(verbose_name='name', max_length=255)),
                ('area', models.ForeignKey(related_name='i18n_names', to='datafetch.Area')),
            ],
            options={
                'verbose_name': 'I18N Name',
                'verbose_name_plural': 'I18N Names',
            },
        ),
        migrations.CreateModel(
            name='ContactDetail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(verbose_name='label', blank=True, max_length=512, help_text='A human-readable label for the contact detail')),
                ('contact_type', models.CharField(verbose_name='type', max_length=12, choices=[('ADDRESS', 'Address'), ('EMAIL', 'Email'), ('URL', 'Url'), ('MAIL', 'Snail mail'), ('TWITTER', 'Twitter'), ('FACEBOOK', 'Facebook'), ('PHONE', 'Telephone'), ('MOBILE', 'Mobile'), ('TEXT', 'Text'), ('VOICE', 'Voice'), ('FAX', 'Fax'), ('CELL', 'Cell'), ('VIDEO', 'Video'), ('PAGER', 'Pager'), ('TEXTPHONE', 'Textphone')], help_text="A type of medium, e.g. 'fax' or 'email'")),
                ('value', models.CharField(verbose_name='value', max_length=512, help_text='A value, e.g. a phone number or email address')),
                ('note', models.CharField(verbose_name='note', blank=True, max_length=512, help_text='A note, e.g. for grouping contact details by physical location')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Identifier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('identifier', models.CharField(verbose_name='identifier', max_length=512, help_text='An issued identifier, e.g. a DUNS number')),
                ('scheme', models.CharField(verbose_name='scheme', blank=True, max_length=128, help_text='An identifier scheme, e.g. DUNS')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('dbpedia_resource', models.CharField(max_length=255, help_text='DbPedia URI of the resource', unique=True)),
                ('iso639_1_code', models.CharField(max_length=2)),
                ('name', models.CharField(max_length=128, help_text='English name of the language')),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(verbose_name='url', max_length=350, help_text='A URL')),
                ('note', models.CharField(verbose_name='note', blank=True, max_length=512, help_text="A note, e.g. 'Wikipedia page'")),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(verbose_name='label', blank=True, max_length=512, help_text='A label describing the membership')),
                ('role', models.CharField(verbose_name='role', blank=True, max_length=512, help_text='The role that the person fulfills in the organization')),
                ('area', models.ForeignKey(related_name='memberships', to='datafetch.Area', blank=True, help_text='The geographic area to which the post is related', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('content', models.TextField(verbose_name='content', blank=True, help_text='A note about this person or organization')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OtherName',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('name', models.CharField(verbose_name='name', max_length=512, help_text='An alternate or former name')),
                ('note', models.CharField(verbose_name='note', blank=True, max_length=1024, help_text="A note, e.g. 'Birth name'")),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(verbose_name='label', blank=True, max_length=512, help_text='A label describing the post')),
                ('other_label', models.CharField(verbose_name='other label', blank=True, max_length=512, null=True, help_text='An alternate label, such as an abbreviation')),
                ('role', models.CharField(verbose_name='role', blank=True, max_length=512, help_text='The function that the holder of the post fulfills')),
                ('area', models.ForeignKey(related_name='posts', to='datafetch.Area', blank=True, help_text='The geographic area to which the post is related', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Relationship',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('start_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='start date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item starts')),
                ('end_date', models.CharField(validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], verbose_name='end date', blank=True, max_length=10, null=True, help_text='The date when the validity of the item ends')),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(verbose_name='label', blank=True, max_length=512, help_text='A label describing the relationship')),
                ('source', models.URLField(verbose_name='source', blank=True, null=True, help_text='URL to the source that documents the relationship')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(verbose_name='url', help_text='A URL')),
                ('note', models.CharField(verbose_name='note', blank=True, max_length=512, help_text="A note, e.g. 'Parliament website'")),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('relationship_ptr', models.OneToOneField(to='datafetch.Relationship', serialize=False, parent_link=True, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(verbose_name='value', blank=True, max_digits=12, help_text='The monetary value of the donation', decimal_places=2)),
                ('donation_type', models.CharField(verbose_name='donation type', max_length=128, help_text='The type of donation e.g. cash')),
                ('nature_of_donation', models.CharField(verbose_name='nature of donation', blank=True, max_length=128, help_text='The nature of the donation e.g. hospitality')),
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
            bases=('datafetch.relationship',),
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('actor_ptr', models.OneToOneField(to='datafetch.Actor', serialize=False, parent_link=True, auto_created=True, primary_key=True)),
                ('summary', models.CharField(verbose_name='summary', blank=True, max_length=1024, help_text='A one-line description of an organization')),
                ('description', models.TextField(verbose_name='biography', blank=True, help_text='An extended description of an organization')),
                ('classification', models.CharField(verbose_name='classification', blank=True, max_length=512, help_text='An organization category, e.g. committee')),
                ('founding_date', models.CharField(validators=[django.core.validators.RegexValidator(code='invalid_founding_date', message='founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', regex='^[0-9]{4}(-[0-9]{2}){0,2}$')], verbose_name='founding date', blank=True, max_length=10, null=True, help_text='A date of founding')),
                ('dissolution_date', models.CharField(validators=[django.core.validators.RegexValidator(code='invalid_dissolution_date', message='dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', regex='^[0-9]{4}(-[0-9]{2}){0,2}$')], verbose_name='dissolution date', blank=True, max_length=10, null=True, help_text='A date of dissolution')),
                ('area', models.ForeignKey(related_name='organizations', to='datafetch.Area', blank=True, help_text='The geographic area to which this organization is related', null=True)),
                ('parent', models.ForeignKey(related_name='children', to='datafetch.Organization', blank=True, help_text='The organization that contains this organization', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.actor',),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('actor_ptr', models.OneToOneField(to='datafetch.Actor', serialize=False, parent_link=True, auto_created=True, primary_key=True)),
                ('family_name', models.CharField(verbose_name='family name', blank=True, max_length=128, help_text='One or more family names')),
                ('given_name', models.CharField(verbose_name='given name', blank=True, max_length=128, help_text='One or more primary given names')),
                ('additional_name', models.CharField(verbose_name='additional name', blank=True, max_length=128, help_text='One or more secondary given names')),
                ('honorific_prefix', models.CharField(verbose_name='honorific prefix', blank=True, max_length=128, help_text="One or more honorifics preceding a person's name")),
                ('honorific_suffix', models.CharField(verbose_name='honorific suffix', blank=True, max_length=128, help_text="One or more honorifics following a person's name")),
                ('patronymic_name', models.CharField(verbose_name='patronymic name', blank=True, max_length=128, help_text='One or more patronymic names')),
                ('sort_name', models.CharField(verbose_name='sort name', blank=True, max_length=128, help_text='A name to use in an lexicographically ordered list')),
                ('email', models.EmailField(verbose_name='email', blank=True, max_length=254, null=True, help_text='A preferred email address')),
                ('gender', models.CharField(verbose_name='gender', blank=True, max_length=128, help_text='A gender')),
                ('birth_date', models.CharField(verbose_name='birth date', blank=True, max_length=10, help_text='A date of birth')),
                ('death_date', models.CharField(verbose_name='death date', blank=True, max_length=10, help_text='A date of death')),
                ('summary', models.CharField(verbose_name='summary', blank=True, max_length=1024, help_text="A one-line account of a person's life")),
                ('biography', models.TextField(verbose_name='biography', blank=True, help_text="An extended account of a person's life")),
                ('national_identity', models.CharField(verbose_name='national identity', blank=True, max_length=128, null=True, help_text='A national identity')),
            ],
            options={
                'verbose_name_plural': 'People',
            },
            bases=('datafetch.actor',),
        ),
        migrations.AddField(
            model_name='relationship',
            name='influenced_by',
            field=models.ForeignKey(to='datafetch.Actor', related_name='influenced_by', null=True),
        ),
        migrations.AddField(
            model_name='relationship',
            name='influences',
            field=models.ForeignKey(to='datafetch.Actor', related_name='influences', null=True),
        ),
        migrations.AddField(
            model_name='relationship',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_datafetch.relationship_set+', to='contenttypes.ContentType', editable=False, null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='post',
            field=models.ForeignKey(related_name='memberships', to='datafetch.Post', blank=True, help_text='The post held by the person in the organization through this membership', null=True),
        ),
        migrations.AddField(
            model_name='areai18name',
            name='language',
            field=models.ForeignKey(to='datafetch.Language'),
        ),
        migrations.AddField(
            model_name='actor',
            name='content_type',
            field=models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True),
        ),
        migrations.AddField(
            model_name='actor',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_datafetch.actor_set+', to='contenttypes.ContentType', editable=False, null=True),
        ),
        migrations.AddField(
            model_name='actor',
            name='relationships',
            field=models.ManyToManyField(to='datafetch.Actor', through='datafetch.Relationship', help_text='Relationships involving the person or organization'),
        ),
        migrations.AddField(
            model_name='post',
            name='organization',
            field=models.ForeignKey(to='datafetch.Organization', related_name='posts', help_text='The organization in which the post is held'),
        ),
        migrations.AddField(
            model_name='membership',
            name='on_behalf_of',
            field=models.ForeignKey(related_name='memberships_on_behalf_of', to='datafetch.Organization', blank=True, help_text='The organization on whose behalf the person is a party to the relationship', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(related_name='memberships', to='datafetch.Organization', blank=True, help_text='The organization that is a party to the relationship', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='person',
            field=models.ForeignKey(to='datafetch.Person', to_field='id', related_name='memberships', help_text='The person who is a party to the relationship'),
        ),
        migrations.AlterUniqueTogether(
            name='areai18name',
            unique_together=set([('area', 'language', 'name')]),
        ),
    ]

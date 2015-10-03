# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import django.utils.timezone
import model_utils.fields
import datafetch.models.popolo.behaviors


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('name', models.CharField(help_text="A person or organization's preferred full name", verbose_name='name', max_length=512)),
                ('image', models.URLField(help_text='An image representing the person or organization', blank=True, verbose_name='image', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('name', models.CharField(help_text='A primary name', blank=True, verbose_name='name', max_length=256)),
                ('identifier', models.CharField(help_text='An issued identifier', blank=True, verbose_name='identifier', max_length=512)),
                ('classification', models.CharField(help_text='An area category, e.g. city', blank=True, verbose_name='identifier', max_length=512)),
                ('geom', models.TextField(help_text='A geometry', blank=True, verbose_name='geom', null=True)),
                ('inhabitants', models.IntegerField(help_text='The total number of inhabitants', blank=True, verbose_name='inhabitants', null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
                ('parent', models.ForeignKey(help_text='The area that contains this area', to='datafetch.Area', blank=True, related_name='children', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AreaI18Name',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('name', models.CharField(verbose_name='name', max_length=255)),
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
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A human-readable label for the contact detail', blank=True, verbose_name='label', max_length=512)),
                ('contact_type', models.CharField(help_text="A type of medium, e.g. 'fax' or 'email'", choices=[('ADDRESS', 'Address'), ('EMAIL', 'Email'), ('URL', 'Url'), ('MAIL', 'Snail mail'), ('TWITTER', 'Twitter'), ('FACEBOOK', 'Facebook'), ('PHONE', 'Telephone'), ('MOBILE', 'Mobile'), ('TEXT', 'Text'), ('VOICE', 'Voice'), ('FAX', 'Fax'), ('CELL', 'Cell'), ('VIDEO', 'Video'), ('PAGER', 'Pager'), ('TEXTPHONE', 'Textphone')], verbose_name='type', max_length=12)),
                ('value', models.CharField(help_text='A value, e.g. a phone number or email address', verbose_name='value', max_length=512)),
                ('note', models.CharField(help_text='A note, e.g. for grouping contact details by physical location', blank=True, verbose_name='note', max_length=512)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Identifier',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('identifier', models.CharField(help_text='An issued identifier, e.g. a DUNS number', verbose_name='identifier', max_length=512)),
                ('scheme', models.CharField(help_text='An identifier scheme, e.g. DUNS', blank=True, verbose_name='scheme', max_length=128)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('dbpedia_resource', models.CharField(help_text='DbPedia URI of the resource', unique=True, max_length=255)),
                ('iso639_1_code', models.CharField(max_length=2)),
                ('name', models.CharField(help_text='English name of the language', max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(help_text='A URL', verbose_name='url', max_length=350)),
                ('note', models.CharField(help_text="A note, e.g. 'Wikipedia page'", blank=True, verbose_name='note', max_length=512)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the membership', blank=True, verbose_name='label', max_length=512)),
                ('role', models.CharField(help_text='The role that the person fulfills in the organization', blank=True, verbose_name='role', max_length=512)),
                ('area', models.ForeignKey(help_text='The geographic area to which the post is related', to='datafetch.Area', blank=True, related_name='memberships', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('content', models.TextField(help_text='A note about this person or organization', blank=True, verbose_name='content')),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OtherName',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('name', models.CharField(help_text='An alternate or former name', verbose_name='name', max_length=512)),
                ('note', models.CharField(help_text="A note, e.g. 'Birth name'", blank=True, verbose_name='note', max_length=1024)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the post', blank=True, verbose_name='label', max_length=512)),
                ('other_label', models.CharField(help_text='An alternate label, such as an abbreviation', blank=True, verbose_name='other label', max_length=512, null=True)),
                ('role', models.CharField(help_text='The function that the holder of the post fulfills', blank=True, verbose_name='role', max_length=512)),
                ('area', models.ForeignKey(help_text='The geographic area to which the post is related', to='datafetch.Area', blank=True, related_name='posts', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Relationship',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('start_date', models.CharField(help_text='The date when the validity of the item starts', max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('end_date', models.CharField(help_text='The date when the validity of the item ends', max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', editable=False, default=django.utils.timezone.now)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', editable=False, default=django.utils.timezone.now)),
                ('label', models.CharField(help_text='A label describing the influence', blank=True, verbose_name='label', max_length=512)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(help_text='A URL', verbose_name='url')),
                ('note', models.CharField(help_text="A note, e.g. 'Parliament website'", blank=True, verbose_name='note', max_length=512)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('actor_ptr', models.OneToOneField(parent_link=True, primary_key=True, to='datafetch.Actor', serialize=False, auto_created=True)),
                ('summary', models.CharField(help_text='A one-line description of an organization', blank=True, verbose_name='summary', max_length=1024)),
                ('description', models.TextField(help_text='An extended description of an organization', blank=True, verbose_name='biography')),
                ('classification', models.CharField(help_text='An organization category, e.g. committee', blank=True, verbose_name='classification', max_length=512)),
                ('founding_date', models.CharField(help_text='A date of founding', max_length=10, blank=True, verbose_name='founding date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_founding_date')], null=True)),
                ('dissolution_date', models.CharField(help_text='A date of dissolution', max_length=10, blank=True, verbose_name='dissolution date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$', code='invalid_dissolution_date')], null=True)),
                ('area', models.ForeignKey(help_text='The geographic area to which this organization is related', to='datafetch.Area', blank=True, related_name='organizations', null=True)),
                ('parent', models.ForeignKey(help_text='The organization that contains this organization', to='datafetch.Organization', blank=True, related_name='children', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.actor',),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('actor_ptr', models.OneToOneField(parent_link=True, primary_key=True, to='datafetch.Actor', serialize=False, auto_created=True)),
                ('family_name', models.CharField(help_text='One or more family names', blank=True, verbose_name='family name', max_length=128)),
                ('given_name', models.CharField(help_text='One or more primary given names', blank=True, verbose_name='given name', max_length=128)),
                ('additional_name', models.CharField(help_text='One or more secondary given names', blank=True, verbose_name='additional name', max_length=128)),
                ('honorific_prefix', models.CharField(help_text="One or more honorifics preceding a person's name", blank=True, verbose_name='honorific prefix', max_length=128)),
                ('honorific_suffix', models.CharField(help_text="One or more honorifics following a person's name", blank=True, verbose_name='honorific suffix', max_length=128)),
                ('patronymic_name', models.CharField(help_text='One or more patronymic names', blank=True, verbose_name='patronymic name', max_length=128)),
                ('sort_name', models.CharField(help_text='A name to use in an lexicographically ordered list', blank=True, verbose_name='sort name', max_length=128)),
                ('email', models.EmailField(help_text='A preferred email address', blank=True, verbose_name='email', max_length=254, null=True)),
                ('gender', models.CharField(help_text='A gender', blank=True, verbose_name='gender', max_length=128)),
                ('birth_date', models.CharField(help_text='A date of birth', blank=True, verbose_name='birth date', max_length=10)),
                ('death_date', models.CharField(help_text='A date of death', blank=True, verbose_name='death date', max_length=10)),
                ('summary', models.CharField(help_text="A one-line account of a person's life", blank=True, verbose_name='summary', max_length=1024)),
                ('biography', models.TextField(help_text="An extended account of a person's life", blank=True, verbose_name='biography')),
                ('national_identity', models.CharField(help_text='A national identity', blank=True, verbose_name='national identity', max_length=128, null=True)),
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
            field=models.ForeignKey(to='contenttypes.ContentType', editable=False, related_name='polymorphic_datafetch.relationship_set+', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='post',
            field=models.ForeignKey(help_text='The post held by the person in the organization through this membership', to='datafetch.Post', blank=True, related_name='memberships', null=True),
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
            field=models.ForeignKey(to='contenttypes.ContentType', editable=False, related_name='polymorphic_datafetch.actor_set+', null=True),
        ),
        migrations.AddField(
            model_name='actor',
            name='relationships',
            field=models.ManyToManyField(help_text='Relationships involving the person or organization', through='datafetch.Relationship', to='datafetch.Actor'),
        ),
        migrations.AddField(
            model_name='post',
            name='organization',
            field=models.ForeignKey(help_text='The organization in which the post is held', to='datafetch.Organization', related_name='posts'),
        ),
        migrations.AddField(
            model_name='membership',
            name='on_behalf_of',
            field=models.ForeignKey(help_text='The organization on whose behalf the person is a party to the relationship', to='datafetch.Organization', blank=True, related_name='memberships_on_behalf_of', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(help_text='The organization that is a party to the relationship', to='datafetch.Organization', blank=True, related_name='memberships', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='person',
            field=models.ForeignKey(help_text='The person who is a party to the relationship', to_field='id', to='datafetch.Person', related_name='memberships'),
        ),
        migrations.AlterUniqueTogether(
            name='areai18name',
            unique_together=set([('area', 'language', 'name')]),
        ),
    ]

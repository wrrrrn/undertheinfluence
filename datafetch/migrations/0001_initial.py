# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import datafetch.models.popolo.behaviors
import django.core.validators
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('name', models.CharField(verbose_name='name', max_length=256, help_text='A primary name', blank=True)),
                ('identifier', models.CharField(verbose_name='identifier', max_length=512, help_text='An issued identifier', blank=True)),
                ('classification', models.CharField(verbose_name='identifier', max_length=512, help_text='An area category, e.g. city', blank=True)),
                ('geom', models.TextField(verbose_name='geom', blank=True, help_text='A geometry', null=True)),
                ('inhabitants', models.IntegerField(verbose_name='inhabitants', blank=True, help_text='The total number of inhabitants', null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
                ('parent', models.ForeignKey(to='datafetch.Area', blank=True, related_name='children', help_text='The area that contains this area', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AreaI18Name',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
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
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('label', models.CharField(verbose_name='label', max_length=512, help_text='A human-readable label for the contact detail', blank=True)),
                ('contact_type', models.CharField(choices=[('ADDRESS', 'Address'), ('EMAIL', 'Email'), ('URL', 'Url'), ('MAIL', 'Snail mail'), ('TWITTER', 'Twitter'), ('FACEBOOK', 'Facebook'), ('PHONE', 'Telephone'), ('MOBILE', 'Mobile'), ('TEXT', 'Text'), ('VOICE', 'Voice'), ('FAX', 'Fax'), ('CELL', 'Cell'), ('VIDEO', 'Video'), ('PAGER', 'Pager'), ('TEXTPHONE', 'Textphone')], verbose_name='type', max_length=12, help_text="A type of medium, e.g. 'fax' or 'email'")),
                ('value', models.CharField(verbose_name='value', max_length=512, help_text='A value, e.g. a phone number or email address')),
                ('note', models.CharField(verbose_name='note', max_length=512, help_text='A note, e.g. for grouping contact details by physical location', blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Identifier',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('identifier', models.CharField(verbose_name='identifier', max_length=512, help_text='An issued identifier, e.g. a DUNS number')),
                ('scheme', models.CharField(verbose_name='scheme', max_length=128, help_text='An identifier scheme, e.g. DUNS', blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('dbpedia_resource', models.CharField(unique=True, max_length=255, help_text='DbPedia URI of the resource')),
                ('iso639_1_code', models.CharField(max_length=2)),
                ('name', models.CharField(max_length=128, help_text='English name of the language')),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(verbose_name='url', max_length=350, help_text='A URL')),
                ('note', models.CharField(verbose_name='note', max_length=512, help_text="A note, e.g. 'Wikipedia page'", blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('label', models.CharField(verbose_name='label', max_length=512, help_text='A label describing the membership', blank=True)),
                ('role', models.CharField(verbose_name='role', max_length=512, help_text='The role that the person fulfills in the organization', blank=True)),
                ('area', models.ForeignKey(to='datafetch.Area', blank=True, related_name='memberships', help_text='The geographic area to which the post is related', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('name', models.CharField(verbose_name='name', max_length=512, help_text='A primary name, e.g. a legally recognized name')),
                ('summary', models.CharField(verbose_name='summary', max_length=1024, help_text='A one-line description of an organization', blank=True)),
                ('description', models.TextField(verbose_name='biography', help_text='An extended description of an organization', blank=True)),
                ('classification', models.CharField(verbose_name='classification', max_length=512, help_text='An organization category, e.g. committee', blank=True)),
                ('founding_date', models.CharField(max_length=10, blank=True, verbose_name='founding date', validators=[django.core.validators.RegexValidator(code='invalid_founding_date', regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='founding date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$')], help_text='A date of founding', null=True)),
                ('dissolution_date', models.CharField(max_length=10, blank=True, verbose_name='dissolution date', validators=[django.core.validators.RegexValidator(code='invalid_dissolution_date', regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='dissolution date must follow the given pattern: ^[0-9]{4}(-[0-9]{2}){0,2}$')], help_text='A date of dissolution', null=True)),
                ('image', models.URLField(verbose_name='image', blank=True, help_text='A URL of an image, to identify the organization visually', null=True)),
                ('area', models.ForeignKey(to='datafetch.Area', blank=True, related_name='organizations', help_text='The geographic area to which this organization is related', null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
                ('parent', models.ForeignKey(to='datafetch.Organization', blank=True, related_name='children', help_text='The organization that contains this organization', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OtherName',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('name', models.CharField(verbose_name='name', max_length=512, help_text='An alternate or former name')),
                ('note', models.CharField(verbose_name='note', max_length=1024, help_text="A note, e.g. 'Birth name'", blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('name', models.CharField(verbose_name='name', max_length=512, help_text="A person's preferred full name")),
                ('family_name', models.CharField(verbose_name='family name', max_length=128, help_text='One or more family names', blank=True)),
                ('given_name', models.CharField(verbose_name='given name', max_length=128, help_text='One or more primary given names', blank=True)),
                ('additional_name', models.CharField(verbose_name='additional name', max_length=128, help_text='One or more secondary given names', blank=True)),
                ('honorific_prefix', models.CharField(verbose_name='honorific prefix', max_length=128, help_text="One or more honorifics preceding a person's name", blank=True)),
                ('honorific_suffix', models.CharField(verbose_name='honorific suffix', max_length=128, help_text="One or more honorifics following a person's name", blank=True)),
                ('patronymic_name', models.CharField(verbose_name='patronymic name', max_length=128, help_text='One or more patronymic names', blank=True)),
                ('sort_name', models.CharField(verbose_name='sort name', max_length=128, help_text='A name to use in an lexicographically ordered list', blank=True)),
                ('email', models.EmailField(verbose_name='email', blank=True, max_length=254, help_text='A preferred email address', null=True)),
                ('gender', models.CharField(verbose_name='gender', max_length=128, help_text='A gender', blank=True)),
                ('birth_date', models.CharField(verbose_name='birth date', max_length=10, help_text='A date of birth', blank=True)),
                ('death_date', models.CharField(verbose_name='death date', max_length=10, help_text='A date of death', blank=True)),
                ('image', models.URLField(verbose_name='image', blank=True, help_text='A URL of a head shot', null=True)),
                ('summary', models.CharField(verbose_name='summary', max_length=1024, help_text="A one-line account of a person's life", blank=True)),
                ('biography', models.TextField(verbose_name='biography', help_text="An extended account of a person's life", blank=True)),
                ('national_identity', models.CharField(verbose_name='national identity', blank=True, max_length=128, help_text='A national identity', null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'verbose_name_plural': 'People',
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('label', models.CharField(verbose_name='label', max_length=512, help_text='A label describing the post', blank=True)),
                ('other_label', models.CharField(verbose_name='other label', blank=True, max_length=512, help_text='An alternate label, such as an abbreviation', null=True)),
                ('role', models.CharField(verbose_name='role', max_length=512, help_text='The function that the holder of the post fulfills', blank=True)),
                ('area', models.ForeignKey(to='datafetch.Area', blank=True, related_name='posts', help_text='The geographic area to which the post is related', null=True)),
                ('organization', models.ForeignKey(to='datafetch.Organization', related_name='posts', help_text='The organization in which the post is held')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Relationship',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('start_date', models.CharField(max_length=10, blank=True, verbose_name='start date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item starts', null=True)),
                ('end_date', models.CharField(max_length=10, blank=True, verbose_name='end date', validators=[django.core.validators.RegexValidator(regex='^[0-9]{4}(-[0-9]{2}){0,2}$', message='Date has wrong format'), datafetch.models.popolo.behaviors.validate_partial_date], help_text='The date when the validity of the item ends', null=True)),
                ('created_at', model_utils.fields.AutoCreatedField(verbose_name='creation time', default=django.utils.timezone.now, editable=False)),
                ('updated_at', model_utils.fields.AutoLastModifiedField(verbose_name='last modification time', default=django.utils.timezone.now, editable=False)),
                ('label', models.CharField(verbose_name='label', max_length=512, help_text='A label describing the influence', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('url', models.URLField(verbose_name='url', help_text='A URL')),
                ('note', models.CharField(verbose_name='note', max_length=512, help_text="A note, e.g. 'Parliament website'", blank=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType', blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='membership',
            name='on_behalf_of',
            field=models.ForeignKey(to='datafetch.Organization', blank=True, related_name='memberships_on_behalf_of', help_text='The organization on whose behalf the person is a party to the relationship', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='organization',
            field=models.ForeignKey(to='datafetch.Organization', blank=True, related_name='memberships', help_text='The organization that is a party to the relationship', null=True),
        ),
        migrations.AddField(
            model_name='membership',
            name='person',
            field=models.ForeignKey(to='datafetch.Person', related_name='memberships', help_text='The person who is a party to the relationship'),
        ),
        migrations.AddField(
            model_name='membership',
            name='post',
            field=models.ForeignKey(to='datafetch.Post', blank=True, related_name='memberships', help_text='The post held by the person in the organization through this membership', null=True),
        ),
        migrations.AddField(
            model_name='areai18name',
            name='language',
            field=models.ForeignKey(to='datafetch.Language'),
        ),
        migrations.AlterUniqueTogether(
            name='areai18name',
            unique_together=set([('area', 'language', 'name')]),
        ),
    ]

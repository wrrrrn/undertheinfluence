# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import wagtail.wagtailcore.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0019_verbose_names_cleanup'),
        ('cms', '0004_analysis_owner'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataPage',
            fields=[
                ('page_ptr', models.OneToOneField(primary_key=True, to='wagtailcore.Page', parent_link=True, serialize=False, auto_created=True)),
                ('body', wagtail.wagtailcore.fields.RichTextField(blank=True)),
                ('analysis', models.ForeignKey(blank=True, null=True, related_name='+', to='cms.Analysis', on_delete=django.db.models.deletion.SET_NULL)),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]

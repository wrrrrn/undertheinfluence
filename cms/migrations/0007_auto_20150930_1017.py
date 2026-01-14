# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import wagtail.wagtailcore.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0006_auto_20150930_1016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quote',
            name='quote',
            field=wagtail.wagtailcore.fields.RichTextField(),
        ),
    ]

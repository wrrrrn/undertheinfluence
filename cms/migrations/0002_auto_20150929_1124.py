# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailimages', '0008_image_created_at_index'),
        ('cms', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='mypage',
            options={'verbose_name': 'Page'},
        ),
        migrations.AddField(
            model_name='profile',
            name='image',
            field=models.ForeignKey(to='wagtailimages.Image', related_name='+', blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
    ]

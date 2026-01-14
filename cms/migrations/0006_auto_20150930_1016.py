# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import wagtail.wagtailcore.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0005_datapage'),
    ]

    operations = [
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('quote', wagtail.wagtailcore.fields.RichTextField(blank=True)),
                ('attribution', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='mypage',
            name='quote',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='cms.Quote', related_name='+'),
        ),
    ]

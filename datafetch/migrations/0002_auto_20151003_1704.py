# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datafetch', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('relationship_ptr', models.OneToOneField(serialize=False, parent_link=True, auto_created=True, to='datafetch.Relationship', primary_key=True)),
                ('value', models.DecimalField(help_text='The monetary value of the donation', max_digits=12, blank=True, decimal_places=2, verbose_name='value')),
                ('category', models.CharField(help_text='The category of the donation e.g. cash', max_length=512, verbose_name='category')),
                ('nature', models.CharField(help_text='The nature of the donation e.g. hospitality', blank=True, max_length=512, verbose_name='nature')),
                ('accepted_date', models.CharField(help_text='The date the donation was accepted', max_length=10, verbose_name='accepted date')),
            ],
            options={
                'abstract': False,
            },
            bases=('datafetch.relationship',),
        ),
        migrations.AddField(
            model_name='relationship',
            name='source',
            field=models.URLField(help_text='URL to the source that documents the relationship', null=True, blank=True, verbose_name='source'),
        ),
        migrations.AlterField(
            model_name='relationship',
            name='label',
            field=models.CharField(help_text='A label describing the relationship', blank=True, max_length=512, verbose_name='label'),
        ),
    ]

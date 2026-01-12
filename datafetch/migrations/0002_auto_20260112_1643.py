# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datafetch', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='additional_name',
            field=models.CharField(verbose_name='additional name', max_length=512, blank=True, help_text='One or more secondary given names'),
        ),
        migrations.AlterField(
            model_name='person',
            name='family_name',
            field=models.CharField(verbose_name='family name', max_length=512, blank=True, help_text='One or more family names'),
        ),
        migrations.AlterField(
            model_name='person',
            name='given_name',
            field=models.CharField(verbose_name='given name', max_length=512, blank=True, help_text='One or more primary given names'),
        ),
        migrations.AlterField(
            model_name='person',
            name='honorific_prefix',
            field=models.CharField(verbose_name='honorific prefix', max_length=512, blank=True, help_text="One or more honorifics preceding a person's name"),
        ),
        migrations.AlterField(
            model_name='person',
            name='honorific_suffix',
            field=models.CharField(verbose_name='honorific suffix', max_length=512, blank=True, help_text="One or more honorifics following a person's name"),
        ),
        migrations.AlterField(
            model_name='person',
            name='patronymic_name',
            field=models.CharField(verbose_name='patronymic name', max_length=512, blank=True, help_text='One or more patronymic names'),
        ),
        migrations.AlterField(
            model_name='person',
            name='sort_name',
            field=models.CharField(verbose_name='sort name', max_length=512, blank=True, help_text='A name to use in an lexicographically ordered list'),
        ),
    ]

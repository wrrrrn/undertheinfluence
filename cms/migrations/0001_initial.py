# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import wagtail.wagtailcore.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0019_verbose_names_cleanup'),
    ]

    operations = [
        migrations.CreateModel(
            name='Analysis',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('title', models.CharField(max_length=255)),
                ('date', models.DateField(verbose_name='Post date')),
                ('body', wagtail.wagtailcore.fields.RichTextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'Analyses',
            },
        ),
        migrations.CreateModel(
            name='MyPage',
            fields=[
                ('page_ptr', models.OneToOneField(primary_key=True, serialize=False, auto_created=True, to='wagtailcore.Page', parent_link=True)),
                ('body', wagtail.wagtailcore.fields.RichTextField(blank=True)),
                ('analysis', models.ForeignKey(null=True, to='cms.Analysis', on_delete=django.db.models.deletion.SET_NULL, related_name='+')),
            ],
            options={
                'verbose_name': 'Pages',
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('body', wagtail.wagtailcore.fields.RichTextField(blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='mypage',
            name='profile',
            field=models.ForeignKey(null=True, blank=True, to='cms.Profile', on_delete=django.db.models.deletion.SET_NULL, related_name='+'),
        ),
        migrations.AlterField(
            model_name='mypage',
            name='analysis',
            field=models.ForeignKey(null=True, blank=True, to='cms.Analysis', on_delete=django.db.models.deletion.SET_NULL, related_name='+'),
        ),
    ]

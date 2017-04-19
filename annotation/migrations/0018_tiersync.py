# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-04-19 10:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('annotation', '0017_tier_created_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='TierSync',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tiers', models.ManyToManyField(related_name='sync_tiers', to='annotation.Tier')),
            ],
        ),
    ]
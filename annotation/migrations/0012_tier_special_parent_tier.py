# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-02-06 18:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('annotation', '0011_dataset_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='tier',
            name='special_parent_tier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='special_child_tiers', to='annotation.Tier'),
        ),
    ]

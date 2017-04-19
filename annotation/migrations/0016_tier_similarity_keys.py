# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-03 15:41
from __future__ import unicode_literals

import annotation.models
import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('annotation', '0015_remove_similarity_measure_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='tier',
            name='similarity_keys',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=annotation.models.default_keys, null=True),
        ),
    ]
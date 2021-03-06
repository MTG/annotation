# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-01-20 17:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('annotation', '0006_sound_annotation_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='annotation',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]

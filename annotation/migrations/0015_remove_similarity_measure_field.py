# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-02 09:58
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('annotation', '0014_auto_20170302_0958'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='annotationsimilarity',
            name='similarity_measure'
        ),

    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-02 09:58
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


def migrate_similarity_value(apps, schema_editor):
    AnnotationSimilarity = apps.get_model("annotation", "AnnotationSimilarity")

    for annotation in AnnotationSimilarity.objects.filter(reference__sound__exercise__data_set__name='Riyaz'):
        annotation.similarity['value'] = annotation.similarity_measure
        annotation.save()


class Migration(migrations.Migration):

    dependencies = [
        ('annotation', '0013_tier_point_annotations'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotationsimilarity',
            name='similarity',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, default=dict),
        ),
        migrations.RunPython(migrate_similarity_value),

    ]

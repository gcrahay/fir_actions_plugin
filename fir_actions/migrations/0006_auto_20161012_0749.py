# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-10-12 07:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0009_add_incicent_permissions'),
        ('fir_actions', '0005_block_artifacts'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionlist',
            name='plan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='incidents.Label', verbose_name='plan'),
        ),
        migrations.AlterField(
            model_name='actionlist',
            name='detection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='incidents.Label', verbose_name='detection'),
        ),
    ]

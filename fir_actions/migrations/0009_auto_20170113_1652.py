# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2017-01-13 16:52
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fir_actions', '0008_auto_20161013_1735'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blocklocation',
            name='business_line',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='incidents.BusinessLine', verbose_name='business line'),
        ),
    ]
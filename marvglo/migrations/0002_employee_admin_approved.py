# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-01-24 18:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marvglo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='admin_approved',
            field=models.BooleanField(default=False),
        ),
    ]

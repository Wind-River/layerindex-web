# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('layerindex', '0008_yp_compatible'),
    ]

    operations = [
        migrations.CreateModel(
            name='WRTemplate',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('layerbranch', models.ForeignKey(to='layerindex.LayerBranch')),
            ],
        ),
        migrations.CreateModel(
            name='WRTemplateFile',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('wrtemplate', models.ForeignKey(to='layerindex.WRTemplate')),
            ],
        ),
        migrations.AlterField(
            model_name='layeritem',
            name='layer_type',
            field=models.CharField(choices=[('A', 'Base'), ('B', 'Machine (BSP)'), ('S', 'Software'), ('D', 'Distribution'), ('W', 'WRTemplates'), ('M', 'Miscellaneous')], max_length=1),
        ),
    ]

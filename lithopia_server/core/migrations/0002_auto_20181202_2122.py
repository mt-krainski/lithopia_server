# Generated by Django 2.1.3 on 2018-12-02 20:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicationsettings',
            name='bounding_box',
        ),
        migrations.AddField(
            model_name='applicationsettings',
            name='search_radius',
            field=models.FloatField(default=None),
            preserve_default=False,
        ),
    ]

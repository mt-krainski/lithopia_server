# Generated by Django 2.1.4 on 2018-12-21 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acquisition', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='acquisition',
            name='satellite',
            field=models.CharField(default='', max_length=100),
        ),
    ]

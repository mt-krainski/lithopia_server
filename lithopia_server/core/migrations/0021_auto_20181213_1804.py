# Generated by Django 2.1.3 on 2018-12-13 17:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_auto_20181213_1754'),
    ]

    operations = [
        migrations.RenameField(
            model_name='requestimage',
            old_name='result_metrics',
            new_name='statistic_metrics',
        ),
        migrations.AddField(
            model_name='requestimage',
            name='marker_score_path',
            field=models.CharField(default='', max_length=1000),
        ),
    ]

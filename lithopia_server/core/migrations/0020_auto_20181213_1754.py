# Generated by Django 2.1.3 on 2018-12-13 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_auto_20181213_1335'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenceimage',
            name='marker_path',
            field=models.CharField(default='', max_length=1000),
        ),
        migrations.AlterField(
            model_name='referenceimage',
            name='image_path',
            field=models.CharField(max_length=1000),
        ),
    ]

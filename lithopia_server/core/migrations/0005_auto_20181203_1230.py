# Generated by Django 2.1.3 on 2018-12-03 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_dataset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='download_stamp',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]

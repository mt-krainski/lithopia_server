# Generated by Django 2.1.3 on 2018-12-11 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20181211_1951'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestimage',
            name='cropped_diff_image_path',
            field=models.CharField(default='', max_length=1000),
        ),
    ]

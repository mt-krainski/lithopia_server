# Generated by Django 2.1.3 on 2018-12-01 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archive_path', models.TextField()),
                ('download_stamp', models.DateTimeField()),
                ('dataset_id', models.CharField(max_length=100)),
                ('coords', models.TextField()),
                ('transformation', models.TextField()),
            ],
        ),
    ]

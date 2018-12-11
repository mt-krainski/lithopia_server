# Generated by Django 2.1.3 on 2018-12-11 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_dataset_cloud_cover'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferenceImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('used_datasets', models.ManyToManyField(to='core.Dataset')),
            ],
        ),
    ]

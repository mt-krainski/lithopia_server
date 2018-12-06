# Generated by Django 2.1.3 on 2018-12-03 18:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20181203_1230'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bounds', models.TextField()),
                ('detected', models.BooleanField()),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Dataset')),
            ],
        ),
    ]

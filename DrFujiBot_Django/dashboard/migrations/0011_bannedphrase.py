# Generated by Django 2.2.5 on 2019-10-17 02:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_chatlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='BannedPhrase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phrase', models.CharField(max_length=200)),
            ],
        ),
    ]

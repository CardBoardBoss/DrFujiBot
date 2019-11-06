# Generated by Django 2.2.5 on 2019-11-04 12:12

from django.db import migrations
from dashboard.models import DISABLED

coin_commands = [('!open', DISABLED, False),
                 ('!event', DISABLED, False),
                 ('!close', DISABLED, False),
                 ('!resolve', DISABLED, False),
                 ('!unresolve', DISABLED, False),
                 ('!cancel', DISABLED, False),
                 ('!bet', DISABLED, False),
                 ('!daily', DISABLED, False),
                 ('!credit', DISABLED, False),
                 ('!balance', DISABLED, True),
                 ('!coins', DISABLED, True),
                 ('!leaderboard', DISABLED, True),
                 ('!resetcoins', DISABLED, False),
                ]

def create_coin_commands(apps, schema_editor):
    Command = apps.get_model('dashboard', 'Command')

    commands = []
    for coin_command in coin_commands:
        cmd = Command(command=coin_command[0], permissions=coin_command[1], invocation_count=0, is_built_in=True, cooldown=coin_command[2], output=None)
        commands.append(cmd)

    Command.objects.bulk_create(commands)

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_coinentry'),
    ]

    operations = [
        migrations.RunPython(create_coin_commands),
    ]

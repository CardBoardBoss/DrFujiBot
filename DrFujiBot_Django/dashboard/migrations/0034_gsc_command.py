from django.db import migrations
from dashboard.models import DISABLED

def create_gsc_command(apps, schema_editor):
    Command = apps.get_model('dashboard', 'Command')

    cmd = Command(command='!gsc', permissions=DISABLED, invocation_count=0, is_built_in=True, cooldown=False, output=None)
    cmd.save()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0033_new_twitch_settings'),
    ]

    operations = [
        migrations.RunPython(create_gsc_command),
    ]

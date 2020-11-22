from .models import *
from scheduled_tasks.uptime_check import get_uptime
from apscheduler.schedulers.background import BackgroundScheduler
from westwood.models import Game
from os import path
from shutil import copyfile

import datetime
import math
import random
import urllib
import json

def update_run(command_name, simple_output):
    if '!lastrun' == command_name or '!howfar' == command_name:
        current_run_setting = Setting.objects.filter(key='Current Run')[0]
        run_matches = Run.objects.filter(name__iexact=current_run_setting.value)
        if len(run_matches) > 0:
            run_object = run_matches[0]
            if '!lastrun' == command_name:
                run_object.last_run_output = simple_output
                run_object.save()
            elif '!howfar' == command_name:
                run_object.how_far_output = simple_output
                run_object.save()

def handle_setgame(args):
    game_name = ' '.join(args)
    output = 'Game "' + game_name + '" not found'
    game_objects = Game.objects.all()
    for game_object in game_objects:
        short_name = game_object.name.replace('Pokemon ', '').lower()
        if game_name.lower() == short_name or game_name.replace(' ', '').lower() == short_name:
            game_setting_matches = Setting.objects.filter(key__exact='Current Game')
            if len(game_setting_matches) > 0:
                game_setting_matches[0].value = game_object.name
                game_setting_matches[0].save()
                return 'Current game set to ' + game_object.name
    return output

def handle_addcom(args):
    output = ''
    command_name = args[0].lower()
    simple_output_text = ' '.join(args[1:])

    if not command_name.startswith('!'):
        return 'Command must start with "!"'

    if len(simple_output_text) > 5000:
        return 'Command output too long (over 5000 characters)'

    command_matches = Command.objects.filter(command__iexact=command_name)
    if len(command_matches) == 0:
        simple_output = SimpleOutput(output_text=simple_output_text)
        simple_output.save()

        command = Command(command=command_name, output=simple_output)
        command.save()

        update_run(command_name, simple_output)

        output = 'Command "' + command_name + '" successfully created'
    else:
        output = 'Command "' + command_name + '" already exists'
    return output

def handle_delcom(args):
    output = ''
    command_name = args[0].lower()

    if not command_name.startswith('!'):
        return 'Command must start with "!"'

    command_matches = Command.objects.filter(command__iexact=command_name)
    if len(command_matches) == 1:
        if not command_matches[0].is_built_in:
            command_matches[0].delete()
            output = 'Command "' + command_name + '" successfully deleted'
        else:
            output = 'Cannot delete built-in command "' + command_name + '"'
    else:
        output = 'Command "' + command_name + '" not found'
    return output

def handle_editcom(args):
    output = ''
    command_name = args[0].lower()
    simple_output_text = ' '.join(args[1:])

    if not command_name.startswith('!'):
        return 'Command must start with "!"'

    if len(simple_output_text) > 5000:
        return 'Command output too long (over 5000 characters)'

    command_matches = Command.objects.filter(command__iexact=command_name)
    if len(command_matches) == 1:
        command_object = command_matches[0]
        if not command_object.is_built_in:
            prefix = ''
            simple_output = command_object.output

            if None != simple_output:
                # We need to check if the current SimpleOutput is referenced by any Run that is not the current Run
                need_new_simple_output = False
                current_run_setting = Setting.objects.filter(key='Current Run')[0]
                run_matches = Run.objects.all()
                for run in run_matches:
                    if run.name != current_run_setting.value:
                        if simple_output == run.last_run_output or simple_output == run.how_far_output:
                            need_new_simple_output = True
                            prefix = simple_output.prefix
            else:
                need_new_simple_output = True

            if need_new_simple_output:
                # Create a new SimpleOutput and point the Command to it, in order to preserve other Run references to the current SimpleOutput
                new_simple_output = SimpleOutput(prefix=prefix, output_text=simple_output_text)
                new_simple_output.save()
                command_object.output = new_simple_output
                command_object.save()
                simple_output = new_simple_output
            else:
                # No other Run references the current SimpleOutput, so it's safe to just edit it
                simple_output.output_text = simple_output_text
                simple_output.save()

            update_run(command_name, simple_output)

            output = 'Command "' + command_name + '" successfully modified'
        else:
            output = 'Cannot modify built-in command "' + command_name + '"'
    else:
        output = 'Command "' + command_name + '" not found'
    return output

def handle_alias(args):
    output = ''
    existing_command_name = args[0].lower()
    new_command_name = args[1].lower()

    if not new_command_name.startswith('!'):
        return 'New command must start with "!"'

    existing_command_matches = Command.objects.filter(command__iexact=existing_command_name)
    found = (len(existing_command_matches) == 1)

    if not found:
        # Try reversing the order
        temp = existing_command_name
        existing_command_name = new_command_name
        new_command_name = temp

        existing_command_matches = Command.objects.filter(command__iexact=existing_command_name)
        found = (len(command_matches) == 1)

    if found:
        # Make sure the new command doesn't already exist
        new_command_matches = Command.objects.filter(command__iexact=new_command_name)
        if len(new_command_matches) == 0:
            existing_command = existing_command_matches[0]
            if not existing_command.is_built_in:
                new_command = Command(command=new_command_name, permissions=existing_command.permissions, output=existing_command.output)
                new_command.save()
                output = new_command_name + ' is now aliased to ' + existing_command_name
            else:
                output = 'Cannot create an alias for a built-in command'
        else:
            output = 'New command already exists'
    else:
        output = 'Existing command not found'
    return output

def handle_addrun(args):
    output = ''
    run_name = ' '.join(args)

    run_matches = Run.objects.filter(name__iexact=run_name)
    if len(run_matches) == 0:
        current_game_setting = Setting.objects.filter(key='Current Game')[0]
        run_object = Run(name=run_name, game_setting=current_game_setting.value)
        run_object.save()

        output = 'Added new run "' + run_object.name + '" playing ' + run_object.game_setting
    else:
        output = 'Run "' + run_name + '" already exists'
    return output

def handle_setrun(args):
    output = ''
    run_name = ' '.join(args)

    run_matches = Run.objects.filter(name__iexact=run_name)
    if len(run_matches) > 0:
        run_object = run_matches[0]
        current_game_setting = Setting.objects.filter(key='Current Game')[0]
        current_game_setting.value = run_object.game_setting
        current_game_setting.save()

        current_run_setting = Setting.objects.filter(key='Current Run')[0]
        current_run_setting.value = run_name
        current_run_setting.save()

        command_matches = Command.objects.filter(command__iexact='!lastrun')
        if len(command_matches) > 0:
            lastrun_command = command_matches[0]
            aliased_commands = Command.objects.filter(output=lastrun_command.output)

            lastrun_command.output = run_object.last_run_output
            lastrun_command.save()

            for cmd in aliased_commands:
                cmd.output = run_object.last_run_output
                cmd.save()

        command_matches = Command.objects.filter(command__iexact='!howfar')
        if len(command_matches) > 0:
            howfar_command = command_matches[0]
            aliased_commands = Command.objects.filter(output=howfar_command.output)

            howfar_command.output = run_object.how_far_output
            howfar_command.save()

            for cmd in aliased_commands:
                cmd.output = run_object.how_far_output
                cmd.save()

        output = 'Current run set to "' + run_object.name + '" playing ' + run_object.game_setting
    else:
        output = 'Run "' + run_name + '" not found'
    return output

def handle_riprun(args):
    output = ''
    last_run_text = ' '.join(args)

    current_run_setting = Setting.objects.filter(key='Current Run')[0]

    run_matches = Run.objects.filter(name__iexact=current_run_setting.value)
    if len(run_matches) > 0:
        current_run_object = run_matches[0]
        current_run_object.attempt_number += 1

        last_run_simple_output = None
        command_matches = Command.objects.filter(command__iexact='!lastrun')
        if len(command_matches) > 0:
            lastrun_command = command_matches[0]

            prefix = ''
            if lastrun_command.output:
                prefix = lastrun_command.output.prefix
            last_run_simple_output = SimpleOutput(prefix=prefix, output_text=last_run_text)
            last_run_simple_output.save()

            lastrun_command.output = last_run_simple_output
            lastrun_command.save()
        else:
            last_run_simple_output = SimpleOutput(output_text=last_run_text)
            last_run_simple_output.save()

        current_run_object.last_run_output = last_run_simple_output
        current_run_object.save()

        output = 'Attempt number for "' + current_run_object.name + '" run is now ' + str(current_run_object.attempt_number) + ', and !lastrun was updated'
    else:
        output = 'Run "' + current_run_setting.value + '" not found'
    return output

def handle_listruns(args):
    output = ''

    run_matches = Run.objects.all()
    if len(run_matches) > 0:
        runs = []
        output = 'Runs: '
        for run in run_matches:
            runs.append(f'"{run.name}" (attempt {run.attempt_number})')
        output += ', '.join(runs)
    else:
        output = 'No runs were found'
    return output

def update_respects(death_object_id):
    death_matches = Death.objects.filter(id=death_object_id)
    if len(death_matches) > 0:
        death_object = death_matches[0]

        utc_tz = datetime.timezone.utc
        twenty_seconds_ago = datetime.datetime.now(utc_tz) - datetime.timedelta(seconds=20)

        f_matches = ChatLog.objects.filter(line__iexact='F').filter(timestamp__gte=twenty_seconds_ago)
        f_users = set()
        for match in f_matches:
            f_users.add(match.username)

        pokemof_matches = ChatLog.objects.filter(line__exact='pokemoF').filter(timestamp__gte=twenty_seconds_ago)
        pokemof_users = set()
        for match in pokemof_matches:
            pokemof_users.add(match.username)

        pokemo7_matches = ChatLog.objects.filter(line__exact='pokemo7').filter(timestamp__gte=twenty_seconds_ago)
        pokemo7_users = set()
        for match in pokemo7_matches:
            pokemo7_users.add(match.username)

        respect_count = len(f_users) + len(pokemof_users) + len(pokemo7_users)

        death_object.respect_count = respect_count
        death_object.save()

        output = str(respect_count) + ' respects for ' + death_object.nickname
        respects_output = SimpleOutput(output_text=output)
        respects_output.save()
        two_minutes_ago = datetime.datetime.now(utc_tz) - datetime.timedelta(minutes=2)
        respects_message = TimedMessage(minutes_interval=1, last_output_time=two_minutes_ago, max_output_count=1, message=respects_output)
        respects_message.save()

def handle_rip(args):
    nickname = ' '.join(args)

    current_run_setting = Setting.objects.filter(key='Current Run')[0]
    run = Run.objects.filter(name=current_run_setting.value)[0]

    death_object = Death(nickname=nickname, run=run, attempt=run.attempt_number)
    death_object.save()

    death_count = Death.objects.filter(run=run, attempt=run.attempt_number).count()

    output = 'Death count: ' + str(death_count) + ' - Press F to pay respects to "' + nickname + '"'

    utc_tz = datetime.timezone.utc
    twenty_seconds_from_now = datetime.datetime.now(utc_tz) + datetime.timedelta(seconds=20)
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_respects, 'date', run_date=twenty_seconds_from_now, args=[death_object.id])
    scheduler.start()

    # TODO: Auto-marker

    return output

def handle_deaths(args):
    current_run_setting = Setting.objects.filter(key='Current Run')[0]
    run = Run.objects.filter(name=current_run_setting.value)[0]

    death_count = Death.objects.filter(run=run, attempt=run.attempt_number).count()
    death_objects = Death.objects.filter(run=run, attempt=run.attempt_number).order_by('-time_of_death')[:3]
    death_names = [death.nickname for death in death_objects]

    if death_count == 1:
        output = 'There has been ' + str(death_count) + ' death so far. Most recent deaths (latest first): '
    else:
        output = 'There have been ' + str(death_count) + ' deaths so far. Most recent deaths (latest first): '
    output += ', '.join(death_names)

    return output

def handle_fallen(args):
    current_run_setting = Setting.objects.filter(key='Current Run')[0]
    run = Run.objects.filter(name=current_run_setting.value)[0]

    death_objects = Death.objects.filter(run=run).order_by('-respect_count')
    if len(death_objects) > 3:
        death_objects = death_objects[:3]

    output = 'The most respected fallen: '
    for death in death_objects:
        output += death.nickname + ' (' + str(death.respect_count) + '), '

    if output.endswith(', '):
        output = output[:-2]
    return output

def handle_quote(args):
    output = ''
    quote_matches = []
    quote_num = 0
    if len(args) > 0:
        if args[0].isnumeric():
            quote_num = int(args[0])
            quote_matches = Quote.objects.filter(id=quote_num)
        else:
            keyword = args[0]
            quote_matches = Quote.objects.filter(quote_text__icontains=keyword)
    else:
        quote_matches = Quote.objects.all().order_by('?')

    if len(quote_matches) > 0:
        quote = quote_matches[0]
        output = 'Quote #' + str(quote.id) + ' "' + quote.quote_text + '" -' + quote.quotee
    else:
        output = 'Quote not found'
    return output

def handle_latestquote(args):
    output = ''
    quote_matches = Quote.objects.all().order_by('-id')
    if len(quote_matches) > 0:
        quote = quote_matches[0]
        output = 'Quote #' + str(quote.id) + ' "' + quote.quote_text + '" -' + quote.quotee
    else:
        output = 'Quote not found'
    return output

def handle_addquote(args):
    if args[0] == "-q":
        quotee = args[1]
        quote_text = ' '.join(args[2:])
        quote_object = Quote(quote_text=quote_text, quotee=quotee)
    else:
        quote_text = ' '.join(args)
        quotee_setting = Setting.objects.get(key='Quotee')
        quote_object = Quote(quote_text=quote_text, quotee=quotee_setting.value)
    quote_object.save()
    return 'Quote #' + str(quote_object.id) + ' successfully added'

def handle_delquote(args):
    output = ''
    if args[0].isnumeric():
        quote_number = int(args[0])
        quote_matches = Quote.objects.filter(id=quote_number)
        if len(quote_matches) > 0:
            quote_matches[0].delete()
            output = 'Quote #' + args[0] + ' successfully deleted'
    else:
        output = 'Invalid quote number'
    return output

def handle_nuke(args):
    expiry = None
    expiry_minutes = 0
    maybe_expiry = args[0]
    phrase = ' '.join(args)
    if maybe_expiry.isnumeric():
        expiry_minutes = int(maybe_expiry)
        phrase = ' '.join(args[1:])
        utc_tz = datetime.timezone.utc
        expiry = datetime.datetime.now(utc_tz) + datetime.timedelta(minutes=expiry_minutes)

    banned_phrase = BannedPhrase(phrase=phrase, expiry=expiry)
    banned_phrase.save()

    output_text = 'The phrase "' + phrase + '" is now banned'
    if expiry_minutes > 0:
        output_text += ' for ' + str(expiry_minutes) + ' minutes'
    output = [output_text]

    chat_log_matches = ChatLog.objects.filter(line__icontains=phrase)
    for match in chat_log_matches:
        output.append('/timeout ' + match.username + ' 1')

    return output

def handle_unnuke(args):
    phrase = ' '.join(args)
    output = 'Phrase "' + phrase + '" not found'

    banned_phrase_matches = BannedPhrase.objects.filter(phrase__icontains=phrase)
    if len(banned_phrase_matches) > 0:
        for banned_phrase in banned_phrase_matches:
            banned_phrase.delete()
        output = 'The phrase "' + phrase + '" is no longer banned'

    return output

def handle_uptime(args):
    output = 'Stream is offline'

    uptime = get_uptime()
    if uptime:
        output = 'The current stream uptime is '
        if uptime.days > 0:
            output += f'{uptime.days} days, '
        hours = uptime.seconds // 3600
        if hours > 0:
            output += f'{hours} hours, '
        minutes = (uptime.seconds // 60) % 60
        output += f'{minutes} minutes'

    return output

def handle_shoutout(args):
    twitch_username = args[0]
    output = 'Go check out @' + twitch_username + ' at twitch.tv/' + twitch_username + ' They make great content and if you enjoy this stream, you will enjoy them as well!'
    return output

def handle_debug(args):
    # Not sure what else would be useful to put here.
    output = 'DrFujiBot 2.0.20'
    return output

def handle_afflict(args):
    output = ''
    nickname = ' '.join(args)

    all_afflictions = Affliction.objects.all()
    random_affliction = random.choice(all_afflictions)

    afflicted_pokemon_results = AfflictedPokemon.objects.filter(nickname__iexact=nickname)
    if 0 == len(afflicted_pokemon_results):
        afflicted_pokemon = AfflictedPokemon(nickname=nickname, affliction_1=random_affliction)
        output = nickname + ' has been afflicted with ' + random_affliction.name + ' (' + random_affliction.description + ')'
    else:
        afflicted_pokemon = afflicted_pokemon_results[0]
        afflicted_pokemon.affliction_2 = random_affliction
        output = nickname + ' is now afflicted with ' + afflicted_pokemon.affliction_1.name + ' (' + afflicted_pokemon.affliction_1.description + ') and '
        output += random_affliction.name + ' (' + random_affliction.description + ')'
    afflicted_pokemon.save()

    return output

def handle_check(args):
    output = ''
    nickname = ' '.join(args)

    afflicted_pokemon_results = AfflictedPokemon.objects.filter(nickname__iexact=nickname)
    if len(afflicted_pokemon_results) > 0:
        afflicted_pokemon = afflicted_pokemon_results[0]
        output = nickname + ' is afflicted with ' + afflicted_pokemon.affliction_1.name + ' (' + afflicted_pokemon.affliction_1.description + ')'
        if None != afflicted_pokemon.affliction_2:
            output += ' and ' + afflicted_pokemon.affliction_2.name + ' (' + afflicted_pokemon.affliction_2.description + ')'
    else:
        output = nickname + ' was not found'

    return output

def handle_song(args):
    output = 'Unable to determine current song, LastFM not configured'

    lastfm_key_results = Setting.objects.filter(key='LastFM API Key')
    lastfm_username_results = Setting.objects.filter(key='LastFM Username')
    if len(lastfm_key_results) > 0 and len(lastfm_username_results) > 0:
        lastfm_key = lastfm_key_results[0]
        lastfm_username = lastfm_username_results[0]
        if len(lastfm_key.value) > 0 and len(lastfm_username.value) > 0:
            url = "http://ws.audioscrobbler.com/2.0?"
            url += urllib.parse.urlencode({
                "api_key": lastfm_key.value,
                "user": lastfm_username.value,
                "method": "user.getrecenttracks",
                "format": "json"
            })
            try:
                response = urllib.request.urlopen(url).read()
                lastfm_data = json.loads(response)
                most_recent_track = lastfm_data['recenttracks']['track'][0]
                output = f"Current song: {most_recent_track['name']} - {most_recent_track['artist']['#text']}"
            except Exception as e:
                output = "Unable to determine current song"
    return output

def handle_pickegg(args):
    output = ''

    def divide_into_groups_of(group_size, value):
        return math.ceil(value / group_size)

    used_eggs_setting = Setting.objects.filter(key='Used Eggs')[0]
    used_eggs = []
    if len(used_eggs_setting.value) > 0:
        used_eggs = used_eggs_setting.value.split(',')
    total_eggs = int(Setting.objects.filter(key='Total Eggs')[0].value)

    if len(used_eggs) >= total_eggs:
        output = "All eggs have been used!"
    else:
        egg_num = random.randint(1, total_eggs)

        while str(egg_num) in used_eggs:
            egg_num = random.randint(1, total_eggs)

        remainder = egg_num

        # There are 30 pokemon per box.
        box_num = divide_into_groups_of(30, remainder)
        remainder -= (box_num - 1) * 30

        # There are six pokemon per row.
        row_num = divide_into_groups_of(6, remainder)
        remainder -= (row_num - 1) * 6

        column_num = remainder

        used_eggs.append(str(egg_num))
        used_eggs_setting.value = ','.join(used_eggs)
        used_eggs_setting.save()

        output = "Egg #" + str(egg_num) + " (Box: " + str(box_num) + " Row: " + str(row_num) + " Column: " + str(column_num) + ")"

    return output

def handle_useegg(args):
    output = ''

    if args[0].isnumeric():
        egg_num = int(args[0])
        total_eggs = int(Setting.objects.filter(key='Total Eggs')[0].value)

        if egg_num <= total_eggs:
            used_eggs_setting = Setting.objects.filter(key='Used Eggs')[0]
            used_eggs = []
            if len(used_eggs_setting.value) > 0:
                used_eggs = used_eggs_setting.value.split(',')
            used_eggs.append(str(egg_num))
            used_eggs_setting.value = ','.join(used_eggs)
            used_eggs_setting.save()

            output = 'Marked egg #' + str(egg_num) + ' as used.'
        else:
            output = 'Invalid egg number'
    else:
        output = 'Usage: !useegg <egg number>'

    return output

def handle_reseteggs(args):
    output = ''

    if args[0].isnumeric():
        used_eggs_setting = Setting.objects.filter(key='Used Eggs')[0]
        used_eggs_setting.value = ''
        used_eggs_setting.save()

        total_eggs_setting = Setting.objects.filter(key='Total Eggs')[0]
        total_eggs_setting.value = args[0]
        total_eggs_setting.save()

        output = "Set number of eggs to " + args[0] + " and cleared used egg list."
    else:
        output = 'Usage: !reseteggs <total number of eggs>'

    return output

def is_safe_path(sprites_folder, sprite_filename):
    requested_path = path.join(sprites_folder, sprite_filename)
    requested_path = path.abspath(requested_path)
    common_prefix = path.commonprefix([requested_path, sprites_folder])
    return common_prefix == sprites_folder

def handle_setslot(args):
    sprites_folder_results = Setting.objects.filter(key='Sprites Folder')

    if len(sprites_folder_results) > 0:
        sprites_folder = sprites_folder_results[0].value
        if len(sprites_folder) > 0:
            if not args[0].isdecimal():
                return 'Invalid slot number'

            slot_to_set = int(args[0])
            if slot_to_set < 1 or slot_to_set > 6:
                return 'Invalid slot number ' + str(slot_to_set)

            pokemon_to_set = args[1] + '.png'
            if is_safe_path(sprites_folder, pokemon_to_set):
                desired_sprite_path = path.join(sprites_folder, pokemon_to_set)
                desired_sprite_exists = path.exists(desired_sprite_path)
                if not desired_sprite_exists:
                    return 'Pokemon ' + pokemon_to_set + ' is invalid'

                slot_path = path.join(sprites_folder, 'p' + str(slot_to_set) + '.png')

                copyfile(desired_sprite_path, slot_path)
                return 'Slot ' + str(slot_to_set) + ' sprite has been updated'
            else:
                return 'Invalid filename'
        else:
            return 'Sprite folder not set'


handlers = {'!setgame': handle_setgame,
            '!addcom': handle_addcom,
            '!delcom': handle_delcom,
            '!editcom': handle_editcom,
            '!alias': handle_alias,
            '!addrun': handle_addrun,
            '!setrun': handle_setrun,
            '!riprun': handle_riprun,
            '!rip': handle_rip,
            '!deaths': handle_deaths,
            '!fallen': handle_fallen,
            '!quote': handle_quote,
            '!latestquote': handle_latestquote,
            '!addquote': handle_addquote,
            '!delquote': handle_delquote,
            '!nuke': handle_nuke,
            '!unnuke': handle_unnuke,
            '!uptime': handle_uptime,
            '!listruns': handle_listruns,
            '!shoutout': handle_shoutout,
            '!so': handle_shoutout,
            '!debug': handle_debug,
            '!afflict': handle_afflict,
            '!check': handle_check,
            '!song': handle_song,
            '!pickegg': handle_pickegg,
            '!useegg': handle_useegg,
            '!reseteggs': handle_reseteggs,
            '!setslot': handle_setslot
           }

expected_args = {'!setgame': 1,
                 '!addcom': 2,
                 '!delcom': 1,
                 '!editcom': 2,
                 '!alias': 2,
                 '!addrun': 1,
                 '!setrun': 1,
                 '!riprun': 1,
                 '!rip': 1,
                 '!deaths': 0,
                 '!fallen': 0,
                 '!quote': 0,
                 '!latestquote': 0,
                 '!addquote': 1,
                 '!delquote': 1,
                 '!nuke': 1,
                 '!unnuke': 1,
                 '!uptime': 0,
                 '!listruns': 0,
                 '!shoutout': 1,
                 '!so': 1,
                 '!debug': 0,
                 '!afflict': 1,
                 '!check': 1,
                 '!song': 0,
                 '!pickegg': 0,
                 '!useegg': 1,
                 '!reseteggs': 1,
                 '!setslot': 2
                }

usage = {'!setgame': 'Usage: !setgame <pokemon game name>',
         '!addcom': 'Usage: !addcom <command> <output>',
         '!delcom': 'Usage: !delcom <command>',
         '!editcom': 'Usage: !editcom <command> <output>',
         '!alias': 'Usage: !alias <existing command> <new command>',
         '!addrun': 'Usage: !addrun <run name>',
         '!setrun': 'Usage: !setrun <run name>',
         '!riprun': 'Usage: !riprun <!lastrun text>',
         '!rip': 'Usage: !rip <pokemon nickname>',
         '!deaths': 'Usage: !deaths',
         '!fallen': 'Usage: !fallen',
         '!quote': 'Usage: !quote <optional quote number or keyword>',
         '!latestquote': 'Usage: !latestquote',
         '!addquote': 'Usage: !addquote <quote>',
         '!delquote': 'Usage: !delquote <quote number>',
         '!nuke': 'Usage: !nuke <word or phrase>',
         '!unnuke': 'Usage: !nuke <word or phrase>',
         '!uptime': 'Usage: !uptime',
         '!listruns': 'Usage: !listruns',
         '!shoutout': 'Usage: !shoutout <Twitch username>',
         '!so': 'Usage: !so <Twitch username>',
         '!debug': 'Usage: !debug',
         '!afflict': 'Usage: !afflict <nickname>',
         '!check': 'Usage: !check <nickname>',
         '!song': 'Usage: !song',
         '!pickegg': 'Usage: !pickegg',
         '!useegg': 'Usage: !useegg <egg number>',
         '!reseteggs': 'Usage: !reseteggs <total number of eggs>',
         '!setslot': 'Usage: !setslot <slot number> <pokemon name>'
        }

def handle_admin_command(line):
    output = ''
    args = line.split(' ')
    command = args[0]
    handler = handlers.get(command)
    if handler:
        args = args[1:]
        if len(args) >= expected_args[command]:
            output = handler(args)
        else:
            output = usage[command]
    return output

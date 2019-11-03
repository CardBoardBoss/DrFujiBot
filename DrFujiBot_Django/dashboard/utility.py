import certifi
import iso8601
import json
import urllib.request as request

CLIENT_ID = 'cnus4j6y1dvr60vkqsgvto5almy5j8'

def twitch_api_request(url):
    data = None
    try:
        twitch_request = request.Request(url)
        twitch_request.add_header('Client-ID', CLIENT_ID)
        response = request.urlopen(twitch_request, cafile=certifi.where())
        data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print('Twitch API exception: ' + str(e))
    return data

def get_stream_start_time():
    from .models import Setting
    start_time = None
    username = Setting.objects.get(key='Twitch Username').value
    if len(username) > 0:
        url = 'https://api.twitch.tv/helix/streams?user_login=' + username
        stream_data = twitch_api_request(url)
        if stream_data:
            if 'live' == stream_data['data'][0]['type']:
                start_time = iso8601.parse_date(stream_data['data'][0]['started_at'])

    return start_time

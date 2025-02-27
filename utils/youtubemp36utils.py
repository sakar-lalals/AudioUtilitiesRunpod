import random
from urllib.parse import urlparse, parse_qs


def choose_mp36_header_in_random():
    headers_dict = {
        "shaswat_shady" : {
            "x-rapidapi-key": "a8f57e288cmsh509804c0a280a04p1db83djsna326e7679a61",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        },

        "shaswat_lalals": {
            "x-rapidapi-key": "c713eb10ffmsh6a671a386d30b26p17415cjsne70f01970aa7",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        },

        "shaswat_715": {
            "x-rapidapi-key": "f0e4d73e0emsh4fbb1f1a2d426d6p1c2270jsn5e82b7ddebd4",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        },

        "ganga_ghimire": {
            "x-rapidapi-key": "754d116e81msh5684a15043cf6acp15877djsnec9b47e0c26e",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        },

        "rana_kholi_accounts":{
            "x-rapidapi-key": "27844933aemsh957aaf1271392e3p189fb1jsn35de5766987a",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        }
    }
    headers = random.choice(list(headers_dict.values()))
    return headers

def extract_video_id(url):
    """
    Extract the YouTube video ID from a URL.

    Parameters:
    url (str): The YouTube URL.

    Returns:
    str: The video ID if found, otherwise None.
    """
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Valid hostnames for YouTube
    valid_hostnames = ['www.youtube.com', 'youtube.com', 'music.youtube.com']

    # Handle URLs of the format 'https://www.youtube.com/watch?v=VIDEO_ID'
    if parsed_url.hostname in valid_hostnames:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        if parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        if parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]

    # Handle URLs of the format 'https://youtu.be/VIDEO_ID'
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    
    return None  
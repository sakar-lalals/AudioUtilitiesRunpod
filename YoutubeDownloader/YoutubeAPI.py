import os 
import sys 
import time 
import configparser
from utils.logger import get_logger
import re
from urllib.parse import urlparse, parse_qs
import isodate
import requests


def iso8601_duration_to_seconds_iso(date_str):
    # Parse the duration using isodate and get the total seconds
    duration = isodate.parse_duration(date_str)
    return int(duration.total_seconds())


class YoutubeAPI:
    def __init__(self) -> None:
        try:
            self.logger = get_logger("YoutubeAPI")
            self.api_key = os.environ.get("YOUTUBE_API_KEY")
            if not self.api_key:
                raise Exception("Youtube API Key Not Found in config")
        except Exception as e:
            self.logger.error("Error initializing Youtube API")
            self.logger.exception(e)
            raise e

    def extract_video_id(self, url):
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


    def get_video_len(self, audio_url_youtube):
        try:
            video_id = self.extract_video_id(audio_url_youtube)
            url = f"https://www.googleapis.com/youtube/v3/videos"
            params = {
                'part' : 'contentDetails', 
                'id' : video_id, 
                'key' : self.api_key
            }
            response = requests.get(url = url, params=params)
            resp = response.json()
            if not len(resp.get("items", [])):
                raise Exception("Error fetching video details")
            duration_iso = resp['items'][0]['contentDetails']['duration']
            total_seconds = iso8601_duration_to_seconds_iso(duration_iso)
            return total_seconds
        except Exception as e:
            self.logger.exception(e)
            return None
    
    def search_youtube(self, search_query, max_results=1):
        try:
            api_url = "https://www.googleapis.com/youtube/v3/search"
            params = {  
                'part': "id", 
                'q': search_query,
                'type': "video",
                'key': self.api_key, 
                'maxResults': max_results
            }
            response = requests.get(url=api_url, params=params)
            resp = response.json()

            video_urls = []
            if response.status_code == 200 and len(resp.get('items', [])):
                for item in resp.get('items', []):
                    video_id = item['id'].get('videoId')
                    if video_id:
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        video_urls.append(url)
                        
            return video_urls
        except Exception as e:
            print(e)
            return []

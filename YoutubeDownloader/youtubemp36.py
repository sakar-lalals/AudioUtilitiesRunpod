import os
import sys 
sys.path.append(os.path.basename(''))

from utils.logger import get_logger
from utils.redisUtils import RedisHelper
import uuid
from YoutubeDownloader.YoutubeAPI import YoutubeAPI
import requests
import time
import uuid



class YoutubeMp36():
    def __init__(self):
        try:
            self.logger = get_logger("YoutubeMP36Downloader")
            self.youtube_api = YoutubeAPI()
            self.redisHelper = RedisHelper()
            self.download_format = "wav"
            self.api_key_ytmp36 = None 
            self.wait_time = 1
        except Exception as e:
            self.logger.exception(e)
            raise 

    def _get_api_key_ytmp36(self):
        return self.redisHelper._get_random_value("ytmp36-api-keys")

    def _get_api_key(self):
        """
        Tries up to 5 times to get a valid api key.
        """
        for _ in range(5):
            api_key = self._get_api_key_ytmp36()
            if api_key != self.api_key_ytmp36:
                self.api_key_ytmp36 = api_key
                break
        if not api_key:
            raise Exception("Could not find a valid youtube downloader api key")
    
    def _get_header(self):
        self._get_api_key()
        header = {
            "x-rapidapi-key": f"{self.api_key_ytmp36}",
            "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
        }
        return header

    def download_audio_file(self, download_url, download_path):
        """
        Downloads the file from the provided download URL and saves it to the specified path.
        """
        response = requests.get(download_url)
        if response.status_code == 200:
            # Write the content of the response to the specified file path
            with open(download_path, 'wb') as file:
                file.write(response.content)
            self.logger.debug("File downloaded successfully.")
            return True, download_path
        else:
            self.logger.error(f"Failed to download file. Status Code: {response.status_code}")
            return False, download_path

    def get_video_link(self, video_id):
        try:
            url = "https://ytstream-download-youtube-videos.p.rapidapi.com/dl"
            querystring = {"id":video_id}
            headers = self._get_header()
            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 200:
                data = response.json()
                if data["msg"] == "success":
                    return data['link'], data['title']  
            return None, None  
        except:
            return None, None
    
    def _get_audio_length(self, url):
        return self.youtube_api.get_video_len(url)

    def run(self, url, max_length = 8):
        try:
            audio_length = self._get_audio_length(url)
 
            if audio_length > max_length * 60:
                raise Exception(f"Audio length {audio_length} exceeds max length {max_length}")
            video_id = self.youtube_api.extract_video_id(url)
            if not video_id:
                raise Exception("Error fetching file info")
            download_link, title = self.get_video_link(video_id)

            if not download_link or not title:
                raise Exception("The file cannot be downloaded")
            
            download_path = f"/tmp/{uuid.uuid4()}.wav"
            success, download_path = self.download_audio_file(download_link, download_path)
            if not success:
                self.logger.debug(f"Error downloading file : {url}")
                raise Exception("Error downloading file")
            self.logger.debug(f"File : {title} sucessfully downloaded")
            return title, download_path, audio_length
        except Exception as e:
            self.logger.exception(e)
            raise

if __name__ == "__main__":
    ytdl = YoutubeMp36()
    title, download_path, audio_length = ytdl.run("https://www.youtube.com/watch?v=InD68CDGT9Q")
    print(title, download_path, audio_length)
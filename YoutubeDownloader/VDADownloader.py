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

class VDADownloader():
    def __init__(self):
        try:
            self.logger = get_logger("VDADownloader")
            self.youtube_api = YoutubeAPI()
            self.redisHelper = RedisHelper()
            self.download_format = "wav"
            self.api_key_vda = None 
            self.wait_time = 1
        except Exception as e:
            self.logger.exception(e)
            raise 
    
    def _get_api_key_vda(self):
        return self.redisHelper._get_random_value("video-downloader-api-keys")

    def _get_api_key(self):
        """
        Tries up to 5 times to get a valid api key.
        """
        for _ in range(5):
            api_key = self._get_api_key_vda()
            if api_key != self.api_key_vda:
                self.api_key_vda = api_key
                break
        if not api_key:
            raise Exception("Could not find a valid youtube downloader api key")

    def _get_file_info(self, url):
        """
        Get file id and title from oceansaver
        """
        try:
            info_url = f"https://p.oceansaver.in/ajax/download.php?copyright=0&format={self.download_format}&url={url}&api={self.api_key_vda}"
            for _ in range(3):
                response = requests.get(info_url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        file_id = data.get("id")
                        title = data.get("title")
                        return file_id, title
                else:
                    self.logger.error(f"Error fetching file info, status code: {response.status_code} Retrying in {self.wait_time} sec")
                    time.sleep(self.wait_time)
            return None, None
        except Exception as e:
            self.logger.exception(e)
            raise Exception("Error fetching file info")
    
    def _get_download_url(self, file_id, timeout : int = 90):
        """
        Gets the download url from oceansaver conversion
        """
        try:
            progress_url = f"https://p.oceansaver.in/ajax/progress.php?id={file_id}"
            start_time = time.perf_counter()

            while True:
                progress_response = requests.get(progress_url)
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    
                    if progress_data.get('success') == 1:
                        download_url = progress_data.get('download_url')
                        if not download_url:
                            return None
                        print(f"url {download_url} generation complete downloading now!")
                        return download_url
                    else:
                        progress = progress_data.get('progress', 0)
                        print(f"Progress: {progress}%... waiting {self.wait_time} seconds.")
                else:
                    print("Error in checking progress.")
                    return None
                
                # Check if the timeout period has been exceeded
                elapsed_time = time.perf_counter() - start_time
                if elapsed_time > timeout:
                    print(f"Timeout reached ({timeout} seconds). The download process took too long.")
                    return None
                
                time.sleep(self.wait_time)  # Wait before checking progress again
        except Exception as e:
            self.logger.exception(e)
            raise 

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

    def _get_file_id_title_with_retry(self, url):
        for _ in range(3):
            self._get_api_key()
            file_id, title = self._get_file_info(url)
            if file_id:
                return file_id, title
            else:
                self.logger.error(f"Error fetching file info, Retrying in {self.wait_time} sec")
                time.sleep(self.wait_time)
        return None, None
    
    def _get_audio_length(self, url):
        return self.youtube_api.get_video_len(url)

    def run(self, url, max_length = 8):
        try:
            audio_length = self._get_audio_length(url)
            if audio_length > max_length * 60:
                raise Exception(f"Audio length {audio_length} exceeds max length {max_length}")
            file_id, title = self._get_file_id_title_with_retry(url)
            self.logger.debug(f"File ID: {file_id}, Title: {title}")
            if not file_id:
                raise Exception("Error fetching file info")
            download_url = self._get_download_url(file_id)
            if not download_url:
                raise Exception("Error fetching download url")
            download_path = f"/tmp/{uuid.uuid4()}.wav"
            success, download_path = self.download_audio_file(download_url, download_path)
            if not success:
                raise Exception("Error downloading file")
            return title, download_path, audio_length
        except Exception as e:
            self.logger.exception(e)
            raise

if __name__ == "__main__":
    vda = VDADownloader()
    title, download_path, audio_length = vda.run("https://www.youtube.com/watch?v=D61BvxAOxm0")
    print(title, download_path, audio_length)
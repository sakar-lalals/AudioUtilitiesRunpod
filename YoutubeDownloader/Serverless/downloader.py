import os 
import sys 
sys.path.append(os.path.basename(''))

import runpod
from utils.s3Utils import S3Helper
from utils.response_utils import success, error
from utils.logger import get_logger
from utils.redisUtils import RedisHelper
from utils.stringUtils import validate_youtube_audio_url
import uuid

from YoutubeDownloader.YoutubeAPI import YoutubeAPI
from YoutubeDownloader.VDADownloader import VDADownloader
from YoutubeDownloader.YTDLPDownloader import YTDLPDownloader

aws_access_key = os.environ.get("aws_access_key")
aws_secret_key = os.environ.get("aws_secret_key")
aws_region = os.environ.get("aws_region", "us-east-1")
aws_bucket_name = "lalals"

concurrency_modifier = int(os.environ.get("CONCURRENCY_MODIFIER", 3))

def adjust_concurrency(current_concurrency):
    return concurrency_modifier


class AudioDownloaderPipeline():
    def __init__(self):
        try:
            self.logger = get_logger("AudioDownloaderPipeline")
            self.s3Helper = S3Helper(aws_access_key, aws_secret_key, aws_region)
            self.vdaDownloader = VDADownloader()
            self.ytdlpDownloader = YTDLPDownloader()
        except Exception as e:
            self.logger.exception(e)
            raise 

    def _get_s3_key(self, download_path: str) -> str:
        """Construct S3 key from download path.
        
        Args:
            download_path: Full path to file (URL or path string)
            
        Returns:
            S3 key in format 'files/{filename}'
            
        Raises:
            ValueError: If path doesn't contain valid filename
        """
        try:
            if '/' not in download_path:
                raise ValueError(f"Invalid path format: {download_path}")
                
            filename = download_path.rsplit('/', 1)[1]
            if not filename:
                raise ValueError(f"No filename found in path: {download_path}")
                
            return f"files/{filename}"
            
        except IndexError as e:
            error_msg = f"Path parsing failed: {download_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error processing path: {download_path}"
            self.logger.error(f"{error_msg} - {str(e)}")
            raise RuntimeError(error_msg) from e

    def _upload_to_s3(self, output_path, s3_key):
        try:
            self.s3Helper.upload_file(output_path, s3_key, aws_bucket_name)
        except Exception as e:
            self.logger.error("Error uploading to S3")
            raise e    
    
    def _delete_file(self, file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            self.logger.error(e)
            self.logger.error("Error deleting file")

    def run(self, url):
        try:
            if validate_youtube_audio_url(url):
                ## use vdaDownloader for youtube links 
                self.logger.debug(f"Youtube link detected, using vda...")
                title, download_path, audio_length = self.vdaDownloader.run(url)
            else:
                self.logger.debug(f"Non youtube link detected, using ytdlp...")
                ## use ytdlp for other links
                title, download_path, audio_length = self.ytdlpDownloader.run(url)
            if not title or not download_path:
                raise Exception("Error downloading audio")
            s3_key = self._get_s3_key(download_path)
            self._upload_to_s3(download_path, s3_key)
            self._delete_file(download_path)
            out_obj = {
                'audio_length' : audio_length, 
                'title' : title,
                's3_path' : s3_key, 
                'message' : 'Audio Download Successful'
            }
            return success(out_obj)
        except Exception as e:
            self.logger.error(e)
            out_obj = {
                'audio_length' : 0,
                's3_path' : '',
                'title' : '',
                'message' : str(e)
            }
            return error(out_obj)
    
    def handler(self, event):
        try:
            audio_url = event['input']['arguments']['url']
            return self.run(audio_url)
        except Exception as e:
            self.logger.error(e)
            out_obj = {
                'audio_length' : 0,
                's3_path' : '',
                'title' : '',
                'message' : str(e)
            }
            return error(out_obj)
        
if __name__ == "__main__":
    pipeline = AudioDownloaderPipeline()
    runpod.serverless.start({
        "handler": pipeline.handler, 
        "concurrency_modifier" : adjust_concurrency

    })
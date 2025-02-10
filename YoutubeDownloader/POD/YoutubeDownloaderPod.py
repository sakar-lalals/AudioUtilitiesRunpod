import os 
import sys

sys.path.append(os.path.basename(''))
from utils.s3Utils import S3Helper
from utils.response_utils import success, error
from utils.logger import get_logger
import uuid
import yt_dlp

aws_access_key = os.environ.get("aws_access_key")
aws_secret_key = os.environ.get("aws_secret_key")
aws_region = os.environ.get("aws_region", "us-east-1")
aws_bucket_name = "lalals"

def duration_filter_factory(max_minutes):
    """
    Returns a filter function to restrict video downloads based on a maximum duration in minutes.
    """
    def filter_function(info, *, incomplete):
        duration = info.get('duration')
        if duration and duration > max_minutes * 60:  # Convert minutes to seconds
            raise Exception(f"Video too long. Max allowed is {max_minutes} minutes.")
    return filter_function

class YoutubeDownloader():
    def __init__(self) -> None:
        try:
            self.logger = get_logger("YoutubeDownloader")
            self.s3helper : S3Helper = S3Helper(aws_access_key, aws_secret_key, aws_region)
        except Exception as e:
            self.logger.error("Error initializing Youtube Downloader")
            self.logger.error(e)
            raise e 
    
    def download_audio(self, url, output_path):
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'cachedir' : '/tmp',
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            # 'extractor_args' : 'youtube:player_client=tv',
            'match_filter': duration_filter_factory(8),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            temp_audio_file = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.wav'
            self.logger.debug(f"Downloaded to : {temp_audio_file}")
            os.replace(temp_audio_file, output_path)
            duration = info_dict.get("duration", 0)
            video_title = info_dict.get("title", None)
            return duration, video_title
    
    def handler(self, url):
        try:
            filename = f"{str(uuid.uuid4())}.wav"
            output_path = f"./{filename}"
            try:
                audio_length, title = self.download_audio(url, output_path)
                assert os.path.isfile(output_path)
                self.logger.debug(f"File downloaded successfully")
            except Exception as e:
                self.logger.error(f"Error downloading file")
                raise e
            self.logger.debug(f"Audio Length : {audio_length} seconds")
            s3_key = self.s3helper.upload_original_audio(output_path, "lalals")
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
                'message' : str(e)
            }
            return error(out_obj)

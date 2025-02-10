from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
import os
import uuid
from utils.s3Utils import S3Helper
from utils.response_utils import success, error
from utils.logger import get_logger
import yt_dlp

app = FastAPI()

aws_access_key = os.environ.get("aws_access_key")
aws_secret_key = os.environ.get("aws_secret_key")
aws_region = os.environ.get("aws_region", "us-east-1")
aws_bucket_name = "lalals"

logger = get_logger("YoutubeDownloader")

# Initialize S3 Helper
s3helper = S3Helper(aws_access_key, aws_secret_key, aws_region)


def duration_filter_factory(max_minutes):
    """
    Returns a filter function to restrict video downloads based on a maximum duration in minutes.
    """
    def filter_function(info, *, incomplete):
        duration = info.get('duration')
        if duration and duration > max_minutes * 60:  # Convert minutes to seconds
            raise Exception(f"Video too long. Max allowed is {max_minutes} minutes.")
    return filter_function


class YoutubeDownloader:
    @staticmethod
    def download_audio(url, output_path):
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'cachedir': '/tmp',
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'match_filter': duration_filter_factory(8),  # Max 8 minutes
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            temp_audio_file = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.wav'
            logger.debug(f"Downloaded to: {temp_audio_file}")
            os.replace(temp_audio_file, output_path)
            duration = info_dict.get("duration", 0)
            video_title = info_dict.get("title", None)
            return duration, video_title


class YoutubeDownloadRequest(BaseModel):
    url: str


@app.post("/download-audio", summary="Download audio from YouTube")
async def download_audio(
    url: str = Form(..., description="YouTube URL for the audio to download")
):
    """
    Download audio from a YouTube URL, save it locally, and upload it to S3.

    - **url**: YouTube video URL to download the audio.
    """
    try:
        # Generate unique filename
        filename = f"{str(uuid.uuid4())}.wav"
        output_path = f"/tmp/{filename}"

        # Download audio
        try:
            downloader = YoutubeDownloader()
            audio_length, title = downloader.download_audio(url, output_path)
            logger.debug("File downloaded successfully")
        except Exception as e:
            logger.error("Error downloading file")
            raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

        # Upload to S3
        try:
            s3_key = s3helper.upload_original_audio(output_path, aws_bucket_name)
        except Exception as e:
            logger.error("Error uploading to S3")
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

        response = {
            "audio_length": audio_length,
            "title": title,
            "s3_path": s3_key,
            "message": "Audio download successful",
        }
        return success(response)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="INTERNAL SERVER ERROR")
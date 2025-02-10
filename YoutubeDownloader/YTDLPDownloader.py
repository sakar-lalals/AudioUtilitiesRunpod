
import os
import sys 
sys.path.append(os.path.basename(""))
import uuid
import yt_dlp
from pydub import AudioSegment
from utils.logger import get_logger


def duration_filter_factory(max_minutes):
    """
    Returns a filter function to restrict video downloads based on a maximum duration in minutes.
    """
    def filter_function(info, *, incomplete):
        duration = info.get('duration')
        max_duration = max_minutes * 60  # Convert minutes to seconds
        if duration and duration > max_duration:  # Convert minutes to seconds
            raise yt_dlp.utils.DownloadError(f"Audio length {duration} exceeds max length {max_duration}")

    return filter_function


class YTDLPDownloader:
    def __init__(self):
        try:
            self.logger = get_logger("YTDLPDownloader")
        except Exception as e:
            raise RuntimeError("Error initializing YTDLPDownloader") from e

    def download_audio(self, url, output_path, max_length):
        """
        Downloads audio from the provided URL and saves it to the output path.

        :param url: Public URL of the video/audio.
        :param output_path: Path to save the downloaded audio file.
        :param max_length: Maximum allowed duration of the media in minutes.
        :return: Duration of the audio in seconds and the title of the video.
        """
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'cachedir': '/tmp',
            'outtmpl': '/tmp/%(id)s.%(ext)s',
            'match_filter': duration_filter_factory(max_length),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                temp_audio_file = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.wav'

                if not os.path.exists(temp_audio_file):
                    raise FileNotFoundError("Temporary audio file not found after download.")

                self.logger.debug(f"Downloaded temporary file: {temp_audio_file}")
                os.replace(temp_audio_file, output_path)

                duration = info_dict.get("duration", self._get_audio_length_local(output_path))
                video_title = info_dict.get("title", "Unknown Title")

                return duration, video_title

        except Exception as e:
            self.logger.error(f"Error during download: {e}")
            raise
    
    def _get_audio_length_local(self, file_path):
        """
        Helper method to get the length of an audio file using pydub.
        """
        try:
            self.logger.debug(f"Getting audio length for: {file_path} locally")
            audio = AudioSegment.from_file(file_path)
            return audio.duration_seconds
        except Exception as e:
            self.logger.error(f"Error getting audio length: {e}")
            raise

    def run(self, url, max_length=8):
        """
        Orchestrates the download of audio and returns details about the downloaded file.

        :param url: Public URL of the video/audio.
        :param max_length: Maximum allowed duration of the media in minutes.
        :return: Tuple containing title, output path, and audio length in seconds.
        """
        filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join("./", filename)

        try:
            audio_length, title = self.download_audio(url, output_path, max_length)

            if not os.path.isfile(output_path):
                raise FileNotFoundError("Downloaded file not found.")

            self.logger.info(f"Audio downloaded successfully: {output_path}")
            self.logger.info(f"Audio Title: {title}, Duration: {audio_length} seconds")

            return title, output_path, audio_length

        except Exception as e:
            self.logger.error(f"Error in run method: {e}")
            return None, None, None


# Example usage
if __name__ == "__main__":
    downloader = YTDLPDownloader()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url = "https://soundcloud.com/user-720557634/adele-skyfall-official-lyrics-video"
    url = "https://lalals.s3.us-east-1.amazonaws.com/projects/testVoiceConversionNew.wav"
    title, path, duration = downloader.run(url, max_length=8)

    if title and path and duration:
        print(f"Downloaded: {title}")
        print(f"Path: {path}")
        print(f"Duration: {duration} seconds")
    else:
        print("Download failed.")


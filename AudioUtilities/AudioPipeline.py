import os
import sys
sys.path.append(os.path.basename(""))

from typing import List
from beam import function, Volume, Image, task_queue, QueueDepthAutoscaler
from pydub import AudioSegment

# Local module imports
from utils.s3Utils import S3Helper
from utils.response_utils import success, error
from utils.logger import get_logger
from utils.AudioSeparator import AudioSeparator
from utils.Elevenlabs import SoundEffectCreator

from AudioUtilities.Context import AudioProcessingContext
from AudioUtilities.Config import AudioPipelineConfig
from AudioUtilities.Processor import *

# Constants and configuration
VALID_MODES = [
    "vocal_extractor", "instrumental_extractor", "lead_back_vocal_extractor",
    "vocal_instrumental_extractor", "de_reverb", "de_noise", "de_echo",
    "stem_extractor", "sound_creator"
]

VALID_AUDIO_FORMATS = ["wav", "flac", "mp3", "aac", "ogg", "m4a", "wma", "aiff", "alac", "webm"]



class AudioPipeline:
    """Main audio processing pipeline"""
    
    def __init__(self, config: AudioPipelineConfig):
        self.config = config
        self.logger = get_logger("AudioPipeline")
        self.s3_helper = S3Helper(
            config.aws_access_key,
            config.aws_secret_key,
            config.aws_region
        )
        self.separator = self._initialize_audio_separator()

    def _initialize_audio_separator(self) -> AudioSeparator:
        """Initialize audio separator with proper configuration"""
        os.makedirs(self.config.model_dir, exist_ok=True)
        return AudioSeparator(
            output_dir=self.config.output_dir,
            model_file_dir=self.config.model_dir,
            output_format=self.config.output_format
        )

    def _get_conversion_duration(self, file_path : str) -> float:
        """ Get the length of passed audio"""
        try:
            audio = AudioSegment.from_file(file_path)
            duration = audio.duration_seconds
            return duration 
        except Exception as e:
            self.logger.exception("Error fetching audio duration")
            return None

    def _download_input(self, s3_path: str, task_id: str) -> str:
        """Download input file from S3"""
        file_ext = os.path.splitext(s3_path)[1][1:]
        local_path = os.path.join("/tmp", f"{task_id}.{file_ext}")
        self.s3_helper.download_file(
            self.config.aws_bucket, s3_path, local_path
        )
        return local_path

    def _convert_to_wav(self, file_path: str) -> str:
        """Convert any audio file to WAV format"""
        audio = AudioSegment.from_file(file_path)
        wav_path = os.path.splitext(file_path)[0] + ".wav"
        audio.export(wav_path, format="wav")
        return wav_path

    def _convert_to_mp3(self, file_path: str, output_path: str):
        """Convert audio file to MP3 format"""
        try:
            audio = AudioSegment.from_file(file_path)
            audio.export(output_path, format="mp3")
            return output_path
        except Exception as e:
            self.logger.exception(f"Error converting to mp3: {str(e)}")
            return file_path

    def _create_context(self, task_id: str, input_path: str, mode: str, input_prompt: str, audio_length: int) -> AudioProcessingContext:
        """Create processing context"""
        return AudioProcessingContext(
            task_id=task_id,
            input_path=input_path,
            mode=mode,
            config=self.config,
            separator=self.separator,
            s3_helper=self.s3_helper, 
            input_prompt=input_prompt, 
            audio_length=audio_length
        )
    
    def _delete_file_if_exists(self, file_path : str):
        """ Delete file if exists """
        try:
            if os.path.isfile(file_path):
                os.remove(file_path) 
        except Exception as e:
            self.logger.exception(e)

    def _determine_output_key(self, file_path: str, context: AudioProcessingContext) -> str:
        """Determine output key based on file naming conventions"""
        filename = os.path.basename(file_path)
        return filename.replace(f"{context.task_id}_", "").split(".")[0]

    def _get_full_file_path(self, file_path : str, context : AudioProcessingContext):
        """
        Get full file path from the output filename
        """
        return os.path.join(context.config.output_dir, file_path)
    
    def _get_mp3_file_path(self, file_path : str) -> str:
        """
        Get the file path mp3
        """
        return os.path.splitext(file_path)[0] + ".mp3"


    def execute_pipeline(self, task_id: str, mode: str, s3_input_path: str, input_prompt: str, audio_length:int = None) -> dict:
        """Main pipeline execution flow"""
        try:
            # Input validation
            if mode not in VALID_MODES:
                raise ValueError(f"Invalid processing mode: {mode}")

            wav_path, local_path = "", ""
            if s3_input_path:
                # Download and prepare input if s3 input path is given
                local_path = self._download_input(s3_input_path, task_id)
                wav_path = self._convert_to_wav(local_path)

            # Create processing context
            context = self._create_context(task_id, wav_path, mode, input_prompt, audio_length)

            # Get processing strategy
            processor_class = ProcessingStrategyRegistry.get_strategy(mode)
            processor = processor_class()

            # Execute processing
            output_files = processor.process(context)

            # Handle output and upload
            response = self._handle_outputs(output_files, context)

            self._delete_file_if_exists(local_path)

            return response

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return {"task_id": task_id, "success" : False, "error": str(e)}

    def _handle_outputs(self, output_files: List[str], context: AudioProcessingContext) -> dict:
        """Handle output files and upload to S3"""
        self.logger.debug(f"Got output files : {output_files}")
        results = {}
        conversion_duration = 0
        for file_path in output_files:
            key = self._determine_output_key(file_path, context)
            s3_path_wav = f"conversions/{context.task_id}_{key}.wav"
            s3_path_mp3 = f"conversions/{context.task_id}_{key}.mp3"
            file_path = self._get_full_file_path(file_path, context)
            file_path_mp3 = self._get_mp3_file_path(file_path)
            file_path_mp3 = self._convert_to_mp3(file_path, file_path_mp3)
            if not conversion_duration:
                conversion_duration = self._get_conversion_duration(file_path)
            self.s3_helper.upload_file(file_path, s3_path_wav, self.config.aws_bucket)
            self.s3_helper.upload_file(file_path_mp3, s3_path_mp3, self.config.aws_bucket)
            self._delete_file_if_exists(file_path)
            self._delete_file_if_exists(file_path_mp3)
            results[key] = s3_path_mp3
            results[f"{key}_wav"] = s3_path_wav
        return {"task_id" : context.task_id, "success" : True, "conversion_duration" : conversion_duration,  **results}




import os 
import sys 
sys.path.append(os.path.basename(''))

from pydantic.dataclasses import dataclass
from utils.AudioSeparator import AudioSeparator
from utils.s3Utils import S3Helper
from .Config import AudioPipelineConfig
from typing import Dict, Optional, List, Union


@dataclass
class AudioProcessingContext:
    """Context object encapsulating processing state"""
    
    task_id: str
    input_path: str
    mode: str
    config: 'AudioPipelineConfig'
    separator: AudioSeparator
    s3_helper: S3Helper
    output_channels: Optional[int] = None
    input_prompt : str = ''
    audio_length : Union[int, float, None] = None

    def generate_output_names(self, *keys: str) -> Dict[str, str]:
        return {key: f"{self.task_id}_{key.replace(' ', '')}" for key in keys}

from elevenlabs.client import ElevenLabs
from elevenlabs import save
from utils.logger import get_logger

class SoundEffectCreator:
    def __init__(self, api_key):
        try:
            self.logger = get_logger("SoundEffectCreator")
            self.client = ElevenLabs(
                api_key = api_key
            )
        except Exception as e:
            self.logger.exception(e)
            raise 
    
    def _get_out_file_path(self, task_id : str):
        return f"/tmp/{task_id}.mp3"

    def run(self, task_id, input_prompt, audio_length, prompt_strength = 0.3):
        try:
            out_file_path = self._get_out_file_path(task_id)
            resp = self.client.text_to_sound_effects.convert(
                text = input_prompt, 
                duration_seconds=audio_length, 
                prompt_influence=prompt_strength
            )
            save(resp, out_file_path)
            return out_file_path
        except Exception as e:
            self.logger.exception(e)
            raise 

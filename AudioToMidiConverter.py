import sys

print(f"Python version: {sys.version}")
print(f"Version info: {sys.version_info}")

from typing import Optional, Dict, Any
import os 
import sys 
sys.path.append(os.path.basename(""))

from utils.logger import get_logger
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict_and_save
from pydub import AudioSegment
from utils.aws_utils import S3Helper, initialize_s3, get_bucket_name
from utils.response_utils import success, error
import runpod
import time 

class AudioToMidiConverter:
    AUDIO_FORMAT = "wav"
    TEMP_DIR = "/tmp"

    def __init__(self):
        self.output_dir = "/tmp/basic_pitch"
        os.makedirs(self.output_dir, exist_ok=True)
        self.s3_helper : S3Helper = initialize_s3()
        self.s3_bucket_name = get_bucket_name()
        self.logger = get_logger("AudioToMidiConverter")

    def _download_file_from_s3(self, s3_path: str, task_id: str) -> str:
        """
        Checks in the s3 volume mount if file exists, if not
        Downloads a file from S3 and converts it to WAV format if necessary.

        :param s3_path: Path to the S3 file.
        :param task_id: Unique identifier for the project.
        :return: Local path to the downloaded WAV file.
        """
        try:
            s3_path_full = os.path.join("./lalals", s3_path)
            if os.path.isfile(s3_path_full):
                return s3_path_full
            else:
                if not self.s3_helper.validate_file_exists(s3_path, self.s3_bucket_name):
                    raise FileNotFoundError(f"File not found in S3: {s3_path}")
                
                file_ext = os.path.splitext(s3_path)[-1]
                local_path = os.path.join(self.TEMP_DIR, f"{task_id}_input{file_ext}")
                self.s3_helper.download_file(s3_path, local_path, self.s3_bucket_name)
                
                if file_ext.lower() != f".{self.AUDIO_FORMAT}":
                    wav_path = os.path.join(self.TEMP_DIR, f"{task_id}_input.{self.AUDIO_FORMAT}")
                    audio = AudioSegment.from_file(local_path)
                    audio.export(wav_path, format=self.AUDIO_FORMAT)
                    return wav_path
                
                return local_path
        except Exception as e:
            self.logger.exception("Failed to download and process file from S3.")
            raise

    def _get_midi_file_path(self, input_filename):
        """
        Generates the local output file path based on the project ID and conversion type.
        """
        return os.path.join(self.output_dir, f"{input_filename}_basic_pitch.mid")

    def _get_sonify_file_path(self, input_filename):
        """
        Generates the local output file path based on the project ID and conversion type.
        """
        return os.path.join(self.output_dir, f"{input_filename}_basic_pitch.wav")
    
    def _get_notes_file_path(self, input_filename):
        """
        Generates the local output file path based on the project ID and conversion type.
        """
        return os.path.join(self.output_dir, f"{input_filename}_basic_pitch.csv")
    
    def _get_s3_folder_midi_output(self):
        """
        Generates the S3 folder path for the MIDI file based on the project ID and conversion type.
        """
        return "AudioToMidi"

    def _get_midi_s3_key(self, task_id):
        """
        Generates the S3 key for the MIDI file based on the project ID and conversion type.
        """
        return f"{self._get_s3_folder_midi_output()}/{task_id}.mid"

    def _get_sonify_s3_key(self, task_id):
        """
        Generates the S3 key for the sonified MIDI file based on the project ID and conversion type.
        """
        return f"{self._get_s3_folder_midi_output()}/{task_id}.wav"
    
    def _get_notes_s3_key(self, task_id):
        """
        Generates the S3 key for the notes file based on the project ID and conversion type.
        """
        return f"{self._get_s3_folder_midi_output()}/{task_id}.csv"

    def _upload_files_and_create_out_obj(self, task_id, input_filename, sonify_midi, save_notes):
        """
        Uploads files and creates out object for audio to midi
        """
        try:
            out_obj = {}
            midi_file_path = self._get_midi_file_path(input_filename)
            if not os.path.exists(midi_file_path):
                raise FileNotFoundError(f"MIDI file not found: {midi_file_path}")
            
            #### check and upload midi file 
            midi_s3_key = self._get_midi_s3_key(task_id)
            self.s3_helper.upload_file(midi_file_path, midi_s3_key, self.s3_bucket_name)
            out_obj['midi_file_path'] = midi_s3_key
            out_obj['success'] = True

            if sonify_midi:
                sonify_file_path = self._get_sonify_file_path(input_filename)
                if not os.path.exists(sonify_file_path):
                    raise FileNotFoundError(f"Sonify file not found: {sonify_file_path}")

                sonify_s3_key = self._get_sonify_s3_key(task_id)
                self.s3_helper.upload_file(sonify_file_path, sonify_s3_key, self.s3_bucket_name)
                out_obj['sonify_file_path'] = sonify_s3_key

            if save_notes:
                notes_file_path = self._get_notes_file_path(input_filename)
                if not os.path.exists(notes_file_path):
                    raise FileNotFoundError(f"Notes file not found: {notes_file_path}")

                notes_s3_key = self._get_notes_s3_key(task_id)
                self.s3_helper.upload_file(notes_file_path, notes_s3_key, self.s3_bucket_name)
                out_obj['notes_file_path'] = notes_s3_key
            
            return out_obj

        except Exception as e:
            self.logger.exception("Failed to upload files and create out object.")
            return {'success' : False, 'error' : f'Error during audio to midi conversion: {str(e)}'}
        

    def run(self, task_id, input_audio, sonify_midi, save_notes):
        try:

            input_file = self._download_file_from_s3(input_audio, task_id)
            input_filename = input_file.split("/")[-1].split(".")[0]

            # run basic pitch prediction
            predict_and_save(
                [input_file], 
                self.output_dir, 
                True, 
                sonify_midi, 
                False, 
                save_notes, 
                ICASSP_2022_MODEL_PATH
            )

            return self._upload_files_and_create_out_obj(task_id, input_filename, sonify_midi, save_notes)
        except Exception as e:
            self.logger.exception("Failed to run audio to midi conversion.")
            return {'success' : False, 'error' : f'Error during audio to midi conversion: {str(e)}'}

class AudioToMidiRunpod():
    def __init__(self):
        self.audioToMidi = AudioToMidiConverter()
        self.logger = get_logger("AudioToMidiRunpod")
    
    def handler(self, event):
        try:
            arguments = event['input']['arguments']
            task_id = arguments['task_id']
            audio_path = arguments['audio_path']
            sonify_midi = arguments.get('sonify_midi', False)
            save_notes = arguments.get('save_notes', False)

            out_obj = self.audioToMidi.run(task_id, audio_path, sonify_midi, save_notes)
            out_obj['task_id'] = task_id
            return success(out_obj)
        except Exception as e:
            self.logger.exception(e)
            out_obj = {'task_id' : task_id, 'error' : str(e)}
            return error(out_obj)

def main():
    pipeline = AudioToMidiRunpod()
    runpod.serverless.start({"handler": pipeline.handler})

if __name__ == "__main__":
    main()
    # converter = AudioToMidiConverter()
    # converter.run("1234", "conversions/25bb9290-1bd7-4901-9edf-c6cd0ff040a0.wav")
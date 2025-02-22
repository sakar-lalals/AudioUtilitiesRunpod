import os 
import sys

sys.path.append(os.path.basename(''))

import runpod
from utils.s3Utils import S3Helper
from utils.response_utils import success, error
from utils.logger import get_logger
from utils.AudioSeparator import AudioSeparator
from pydub import AudioSegment
from utils.Elevenlabs import SoundEffectCreator
# from audiocraft.models import AudioGen
# from audiocraft.data.audio import audio_write

aws_access_key = os.environ.get("aws_access_key")
aws_secret_key = os.environ.get("aws_secret_key")
aws_region = os.environ.get("aws_region", "us-east-1")
aws_bucket_name = "lalals"

vocal_extractor_model_name = os.environ.get("vocal_extractor_model", "Kim_Vocal_2.onnx")
instrumental_extractor_model_name = os.environ.get("instrumental_extractor_model", "model_bs_roformer_ep_317_sdr_12.9755.ckpt")
reverb_extractor_model_name = os.environ.get("reverb_extractor_model", "deverb_bs_roformer_8_384dim_10depth.ckpt")
stem_extractor_model_name = os.environ.get("stem_extraction_model", "htdemucs_6s.yaml")
front_back_vocal_extractor_model_name = os.environ.get("front_back_vocal_extraction_model", "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt")
de_echo_model_name = os.environ.get("de_echo_model", "UVR-De-Echo-Aggressive.pth")
de_noise_model_name = os.environ.get("de_noise_model", "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt")
deecho_dereverb_model_combined = os.environ.get("deecho_dereverb_model_combined", "UVR-DeEcho-DeReverb.pth")
denoise_model_vocal_extractor = os.environ.get("denoise_model_vocal_extractor", "UVR-DeNoise.pth")
elevenlabs_api_key = os.environ.get("elevenlabs_sound_effect")

valid_modes = ["vocal_extractor","instrumental_extractor", "2_step_vocal_extractor", "vocal_instrumental_extractor", "de_reverb", "de_noise", "de_echo", "stem_extractor", "sound_creator"]
valid_audio_formats = ["wav", "flac", "mp3", "aac", "ogg", "m4a", "wma", "aiff", "alac", "webm"]

audiogen_model_cache_dir = "/runpod-volume/audiogen"
os.makedirs(audiogen_model_cache_dir, exist_ok=True)
os.environ["TORCH_HOME"] = audiogen_model_cache_dir  # For PyTorch
os.environ["HF_HOME"] = audiogen_model_cache_dir     # For Hugging Face

concurrency_modifier = int(os.environ.get("CONCURRENCY_MODIFIER", 3))

def adjust_concurrency(current_concurrency):
    return concurrency_modifier



class AudioUtiltiesServerlessPipeline():
    def __init__(self):
        try:
            self.logger = get_logger("AudioUtilitiesPipeline")
            self.s3Helper = S3Helper(aws_access_key, aws_secret_key, aws_region)
            self.output_dir = "/tmp/outputs"
            self.model_dir = "/runpod-volume/audio-separator-models"
            os.makedirs(self.model_dir, exist_ok=True)
            os.makedirs(self.output_dir, exist_ok=True)
            self.output_format = "wav"
            self.orig_audio_channel = None
            self.output_audio_channels = None
            self.separator = AudioSeparator(output_dir=self.output_dir, model_file_dir=self.model_dir, output_format=self.output_format)
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Error initializing the pipeline")
            raise 
        
    def _download_input_audio(self, audio_path, task_id):
        """
        Download input audio from s3
        """
        try:
            fileext = self._get_file_ext(audio_path)
            download_path = os.path.join("/tmp", f"{task_id}.{fileext}")
            self.s3Helper.download_file(aws_bucket_name, audio_path, download_path )
            return download_path
        except Exception:
            self.logger.error(f"Error downloading input audio from s3")
            raise 

    def run_extractor(self, model_name, input_filepath, return_vocal_only = False, custom_output_names = None):
        try:
            self.separator.load_model(model_name)
            out_filepaths = self.separator.run(input_filepath, custom_output_names = custom_output_names)
            if return_vocal_only:
                out_filepaths = [out_filepaths[0]]
            return out_filepaths
        except Exception as e:
            self.logger.error(f"Error processing {input_filepath} for vocal extractor")
            self.logger.error(e)
            raise e 
        
    def get_vocal_extractor_model(self, model_args : dict):
        ## if vocal extractor model passed through argument
        ## use that, else use default
        vocal_extractor_arg = model_args.get("vocal_extractor")
        vocal_extractor = vocal_extractor_arg if vocal_extractor_arg else vocal_extractor_model_name
        return vocal_extractor

    def get_instrumental_extractor_model(self, model_args : dict):
        ## if instrumental extractor model passed through argument
        ## use that, else use default
        instrumental_extractor_arg = model_args.get("instrumental_extractor")
        instrumental_extractor = instrumental_extractor_arg if instrumental_extractor_arg else instrumental_extractor_model_name
        return instrumental_extractor
    
    def get_front_back_vocal_extractor_model(self, model_args: dict):
        front_back_vocal_extractor_arg = model_args.get("front_back_vocal_extractor")
        front_back_vocal_extractor = front_back_vocal_extractor_arg if front_back_vocal_extractor_arg else front_back_vocal_extractor_model_name
        return front_back_vocal_extractor
        
    def get_reverb_extractor_model(self, model_args : dict):
        ## if reverb extractor model passed through argument
        ## use that else use default
        reverb_extractor_arg = model_args.get('de_reverb')
        reverb_extractor = reverb_extractor_arg if reverb_extractor_arg else reverb_extractor_model_name
        return reverb_extractor

    def get_stem_extractor_model(self, model_args : dict):
        ## if stem extractor model passed through argument 
        ## use that else use default
        stem_extractor_arg = model_args.get("stem_extractor")
        stem_extractor = stem_extractor_arg if stem_extractor_arg else stem_extractor_model_name
        return stem_extractor

    def get_de_echo_model(self, model_args : dict):
        ##if de echo model passed through argument, use that 
        ## else use default 
        de_echo_arg = model_args.get("de_echo")
        de_echo = de_echo_arg if de_echo_arg else de_echo_model_name
        return de_echo

    def get_de_noise_model(self, model_args : dict):
        ## if de noise model passed through argument, use that 
        ## else use default
        de_noise_arg = model_args.get("de_noise")
        de_noise = de_noise_arg if de_noise_arg else de_noise_model_name
        return de_noise

    def get_full_file_path(self, file_path : str):
        return os.path.join(self.output_dir, file_path)

    def _convert_audio_channels(self, file_path : str, num_channels : int = 0):
        """
        Convert given audio to mono
        """
        try:
            if not num_channels:
                num_channels = self.output_audio_channels or self.orig_audio_channel or 2
            if num_channels not in (1,2):
                raise ValueError("Invalid channel type")
            audio = AudioSegment.from_file(file_path)
            audio.set_channels(num_channels)
            audio.export(file_path, format=self.output_format)
        except Exception as e:
            self.logger.exception(e)
            raise 
    
    def _audio_cleanup(self, input_filepath : str):
        """Performs dereverb, deecho and denoise on given input audio"""
        try:
            self.logger.debug(f"Cleaning up audio for {input_filepath}")
            input_filename = input_filepath.split("/")[-1].split(".")[0]
            # clean the audio using UVR_Decho_Denoise_Model
            custom_output_names = {
                'no reverb' : input_filename
            }
            output_filepaths_ = self.run_extractor(deecho_dereverb_model_combined, input_filepath, custom_output_names = custom_output_names)
            self.logger.debug(f"Echo reverb removal output filepaths : {output_filepaths_}")
            # denoise the audi using UVR_Denoise model
            custom_output_names = {
                'no noise' : input_filename
            }
            output_filepaths_ = self.run_extractor(denoise_model_vocal_extractor, input_filepath, custom_output_names=custom_output_names)
            self.logger.debug(f"Denoise output filepaths : {output_filepaths_}")
        except Exception as e:
            self.logger.exception(e)
            return 

    def process_audio(self, input_filepath, mode, model_args, task_id: str) -> list:
        try:
            self.logger.debug(f"Processing audio with mode: {mode}, model_args: {model_args}")

            # Define output names for common modes
            def generate_output_names(task_id, *keys):
                return {key: f"{task_id}_{key.replace(' ','')}" for key in keys}

            # Helper to clean and convert audio channels
            def clean_and_convert(audio_path, channels=0):
                self._audio_cleanup(self.get_full_file_path(audio_path))
                self._convert_audio_channels(self.get_full_file_path(audio_path), channels)

            # Mode handlers
            if mode == "vocal_extractor":
                output_names = generate_output_names(task_id, "vocals", "instrumental")
                extractor = self.get_vocal_extractor_model(model_args)

                self.logger.debug(f"Running vocal extractor with model: {extractor}")
                extracted_files = self.run_extractor(extractor, input_filepath, custom_output_names=output_names)

                vocal_path = f"{task_id}_vocals.wav"
                assert vocal_path in extracted_files, "Error extracting vocal stem"

                clean_and_convert(vocal_path)
                return extracted_files

            elif mode == "instrumental_extractor":
                output_names = generate_output_names(task_id, "vocals", "instrumental")
                extractor = self.get_instrumental_extractor_model(model_args)

                self.logger.debug(f"Running instrumental extractor with model: {extractor}")
                extracted_files = self.run_extractor(extractor, input_filepath, custom_output_names=output_names)

                instrumental_path = f"{task_id}_instrumental.wav"
                assert instrumental_path in extracted_files, "Error extracting instrumental stem"

                # clean_and_convert(instrumental_path)
                self.logger.debug(f"Extracted files : {extracted_files}")
                return extracted_files

            elif mode == "vocal_instrumental_extractor":
                output_names = generate_output_names(task_id, "vocals", "instrumental")
                vocal_extractor = self.get_vocal_extractor_model(model_args)

                self.logger.debug(f"Running vocal extractor with model: {vocal_extractor}")
                extracted_files = self.run_extractor(vocal_extractor, input_filepath, custom_output_names=output_names)

                vocal_path = f"{task_id}_vocals.wav"
                assert vocal_path in extracted_files, "Error extracting vocal stem"

                # Re-run for instrumental extraction
                output_names = generate_output_names(task_id, "instrumental")
                instrumental_extractor = self.get_instrumental_extractor_model(model_args)

                self.logger.debug(f"Running instrumental extractor with model: {instrumental_extractor}")
                extracted_files += self.run_extractor(instrumental_extractor, input_filepath, custom_output_names=output_names)

                instrumental_path = f"{task_id}_instrumental.wav"
                assert instrumental_path in extracted_files, "Error extracting instrumental stem"

                clean_and_convert(vocal_path)
                clean_and_convert(instrumental_path)
                self.logger.debug(f"Extracted files : {extracted_files}")
                return extracted_files

            elif mode == "2_step_vocal_extractor":
                # Step 1: Separate vocal and instrumental
                output_names = generate_output_names(task_id, "vocals", "instrumental")
                vocal_extractor = self.get_vocal_extractor_model(model_args)
                extracted_files = self.run_extractor(vocal_extractor, input_filepath, custom_output_names=output_names)

                vocal_path = f"{task_id}_vocals.wav"
                assert vocal_path in extracted_files, "Error extracting vocal stem"

                # Step 2: Separate front and back vocals
                input_filename = self.get_full_file_path(vocal_path)
                output_names = generate_output_names(task_id, "vocal_front", "vocal_back")
                front_back_extractor = self.get_front_back_vocal_extractor_model(model_args)
                second_stage_files = self.run_extractor(front_back_extractor, input_filename, custom_output_names=output_names)

                clean_and_convert(f"{task_id}_vocal_front.wav")
                self.logger.debug(f"Extracted files : {extracted_files}")
                return extracted_files + second_stage_files

            elif mode in ["de_reverb", "de_echo", "de_noise"]:
                extractor_map = {
                    "de_reverb": self.get_reverb_extractor_model,
                    "de_echo": self.get_de_echo_model,
                    "de_noise": self.get_de_noise_model
                }

                extractor = extractor_map[mode](model_args)
                output_keys = {"de_reverb": ["no reverb", "reverb", "noreverb"],
                            "de_echo": ["no echo", "echo"],
                            "de_noise": ["dry", "noise", "other", "no noise"]}
                output_names = generate_output_names(task_id, *output_keys[mode])

                self.logger.debug(f"Running {mode} extractor with model: {extractor}")
                return self.run_extractor(extractor, input_filepath, custom_output_names=output_names)

            elif mode == "stem_extractor":
                stem_extractor = self.get_stem_extractor_model(model_args)

                self.logger.debug(f"Running stem extractor with model: {stem_extractor}")
                return self.run_extractor(stem_extractor, input_filepath)

            else:
                raise ValueError(f"Invalid mode provided: {mode}")

        except Exception as e:
            self.logger.error(f"Error processing file: {input_filepath}")
            self.logger.exception(e)
            raise
    
    def _get_file_ext(self, filename : str):
        return filename.split(".")[-1].lower()

    def convert_file_to_wav(self, filename : str):
        try:
            """Converts any given file to wav, using AudioSegment"""
            self.logger.debug(f"Converting {filename} to wav")
            audio = AudioSegment.from_file(filename)
            self.orig_audio_channel = audio.channels
            wav_filename = filename.split(".")[0] + ".wav"
            audio.export(wav_filename, format="wav")
            return wav_filename
        except Exception as e:
            self.logger.exception(e)
            raise e
        
    # def _save_audio_locally_audiogen(self, audio, file_name):
    #     local_path = f"{self.output_dir}/{file_name}"
    #     audio_write(local_path, audio.cpu(), self.audiogen_model.sample_rate, strategy="loudness", loudness_compressor=True)
    #     return local_path + ".wav"

    def _upload_to_s3(self, local_path, file_name, s3_key : str = ''):
        if not s3_key:
            s3_key = f"conversions/{file_name}.wav"
        self.s3Helper.upload_file(local_path, s3_key, aws_bucket_name)
        return s3_key

    def _get_audio_duration(self, local_path):
        return AudioSegment.from_file(local_path).duration_seconds


    def _save_and_upload_audiogen_audio(self, task_id, audio_outputs):
        """Save generated audio files and upload them to S3."""
        output_files = []

        try:
            for idx, one_wav in enumerate(audio_outputs):
                file_name = f"{task_id}_{idx}"

                # Save audio locally
                local_path = self._save_audio_locally_audiogen(one_wav, file_name)

                self.logger.debug(f"Outputs : {os.listdir(self.output_dir)}")
                if not os.path.exists(local_path):
                    raise Exception("Error saving audio locally")
                # Upload to S3
                s3_key = self._upload_to_s3(local_path, file_name)

                # Get conversion duration
                conversion_duration = self._get_audio_duration(local_path)

                output_files.append({
                    "local_path": local_path,
                    "conversion_path": s3_key,
                    "conversion_duration": conversion_duration
                })

                self.logger.info(f"Uploaded {file_name} to S3 at {s3_key}")

            return output_files

        except Exception as e:
            self.logger.exception(f"Error saving or uploading audio: {e}")
            raise    


    def process_sound_creator(self, input_prompt : str, task_id : str):
        try:
            self.logger.debug(f"Got input prompt : {input_prompt}")
            desccriptions = [input_prompt]
            audio_outputs = self.audiogen_model.generate(desccriptions)
            uploaded_files = self._save_and_upload_audiogen_audio(task_id, audio_outputs)
            return uploaded_files
        except Exception as e:
            self.logger.error("Error during sound creation")
            self.logger.error(e)
            raise e


    def run(self, task_id : str, arguments : dict):
        try:
            mode = arguments.get("mode")
            assert mode in valid_modes

            if mode == "sound_creator":
                """
                Process Sound Creator
                """
                input_prompt = arguments['prompt']
                audio_length = int(arguments.get("audio_length", 5))


                ## initialize and run elevenlabs
                el_ = SoundEffectCreator(api_key=elevenlabs_api_key)
                output_filepath = el_.run(task_id, input_prompt, audio_length)
                assert os.path.exists(output_filepath), "Error generating sound"

                file_ext = self._get_file_ext(output_filepath)
                file_name = f"{task_id}"
                file_name_s3 = f"conversions/{task_id}.{file_ext}"
                file_name_s3 = self._upload_to_s3(output_filepath, file_name, file_name_s3)
                conversion_duration = self._get_audio_duration(output_filepath)
                os.remove(output_filepath)
                out_obj = {
                    'local_path' : output_filepath, 
                    'conversion_path' : file_name_s3,
                    'conversion_duration' : conversion_duration
                           }
                output_filepaths = [out_obj]
                # initialize audiogen model for sound creator only
                # self.audiogen_model = AudioGen.get_pretrained('facebook/audiogen-medium')
                # self.audiogen_model.set_generation_params(audio_length)
                # output_filepaths = self.process_sound_creator(input_prompt, task_id)
            else:
                """
                Process for audio cleanup tasks
                """
                
                audio_path_s3 : str = arguments['audio_path_s3']
                model_args = arguments.get("models", {})
                output_channels = arguments.get("output_audio_channels", None)
                if output_channels:
                    self.output_audio_channels = int(output_channels)
                assert audio_path_s3.endswith(tuple(valid_audio_formats)), "Invalid input audio path"
                input_filepath = self._download_input_audio(audio_path_s3, task_id)
                if not os.path.exists(input_filepath):
                    raise Exception("Invalid Input File Provided")
                # converting all audio files to wav before processing
                input_filepath = self.convert_file_to_wav(input_filepath)
                output_filepaths = self.process_audio(input_filepath, mode, model_args, task_id)
            out_obj = self.create_output_obj(output_filepaths, mode, task_id)
            return out_obj
        except Exception as e:
            self.logger.error("Error during audio processing")
            self.logger.error(e)
            raise e 
    
    def create_output_obj(self, output_filepaths : list, mode : str, task_id : str):
        try:
            out_obj = {}
            self.logger.debug(f"Got output filepaths : {output_filepaths}")
            ## if not pipline, it should be either of the individual extractor
            if mode == "sound_creator": 
                out_obj = {
                    'status' : "success", 
                    'generated_files' : output_filepaths
                }
            elif mode in ["vocal_extractor", "instrumental_extractor", "vocal_instrumental_extractor"]:
                output_vocal, output_instrumental = '', ''
                conversion_length = 0
                if not len(output_filepaths):
                    raise Exception("Output files not found")
                else:
                    primary_output_name = f"{task_id}_vocals"
                    secondary_output_name = f"{task_id}_instrumental"
                    for file_path in output_filepaths:
                        file_path = self.get_full_file_path(file_path)
                        file_ext = file_path.split(".")[-1]
                        if primary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_vocal.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_vocal = s3_key
                            # get length from vocal stem 
                            conversion_length = AudioSegment.from_file(file_path).duration_seconds
                        elif secondary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_instrumental.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_instrumental = s3_key
                        else:
                            ## file not required
                            pass
                        if output_vocal and output_instrumental:
                            break
                    out_obj = {
                        'vocal' : output_vocal, 
                        'instrumental' : output_instrumental, 
                        'conversion_duration' : conversion_length
                    }
            elif mode == "2_step_vocal_extractor":
                output_vocal, output_instrumental = '', ''
                output_back_vocal = ''
                conversion_length = 0
                if not len(output_filepaths):
                    raise Exception("Output files not found")
                else:
                    primary_output_name = f"{task_id}_vocal_front"
                    secondary_output_name = f"{task_id}_instrumental"
                    back_vocal_output_name = f"{task_id}_vocal_back"
                    for file_path in output_filepaths:
                        file_path = self.get_full_file_path(file_path)
                        file_ext = file_path.split(".")[-1]
                        if primary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_vocal.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_vocal = s3_key
                            # get conversion length from  main vocal track
                            conversion_length = AudioSegment.from_file(file_path).duration_seconds
                        elif secondary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_instrumental.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_instrumental = s3_key
                        elif back_vocal_output_name in file_path:
                            s3_key = f"conversions/{task_id}_vocal_back.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_back_vocal = s3_key
                        else:
                            ## file not required
                            pass
                    out_obj = {
                        'vocal' : output_vocal, 
                        'instrumental' : output_instrumental, 
                        'back_vocal' : output_back_vocal, 
                        'conversion_length' : conversion_length
                    }
            elif mode == "de_reverb":
                output_reverb, output_noreverb = '', ''
                conversion_length = 0
                if not len(output_filepaths):
                    raise Exception("Output files not found")
                else:
                    primary_output_name = f"{task_id}_noreverb"
                    secondary_output_name = f"{task_id}_reverb"
                    for file_path in output_filepaths:
                        file_path = self.get_full_file_path(file_path)
                        file_ext = file_path.split(".")[-1]
                        if primary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_noreverb.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_noreverb = s3_key
                            conversion_length = AudioSegment.from_file(file_path).duration_seconds
                        elif secondary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_reverb.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_reverb = s3_key
                        else:
                            pass
                    out_obj = {
                        'reverb' : output_reverb, 
                        'noreverb' : output_noreverb, 
                        'conversion_duration' : conversion_length
                    }
            elif mode == "de_echo":
                output_no_echo, output_echo = '', ''
                conversion_length = 0
                if not len(output_filepaths):
                    raise Exception("Output files not found")
                else:
                    primary_output_name = f"{task_id}_noecho"
                    secondary_output_name = f"{task_id}_echo"
                    for file_path in output_filepaths:
                        file_path = self.get_full_file_path(file_path)
                        file_ext = file_path.split(".")[-1]
                        if primary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_no_echo.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_no_echo = s3_key
                            conversion_length = AudioSegment.from_file(file_path).duration_seconds
                        elif secondary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_echo.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_echo = s3_key
                        else:
                            pass
                    out_obj = {
                        'no_echo' : output_no_echo, 
                        'echo' : output_echo, 
                        'conversion_duration' : conversion_length
                    }
            elif mode == "de_noise":
                output_no_noise, output_noise = '', ''
                conversion_length = 0
                if not len(output_filepaths):
                    raise Exception("Output files not found")
                else:
                    primary_output_name = f"{task_id}_dry"
                    secondary_output_name = f"{task_id}_other"
                    for file_path in output_filepaths:
                        file_path = self.get_full_file_path(file_path)
                        file_ext = file_path.split(".")[-1]
                        if primary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_no_noise.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_no_noise = s3_key
                            conversion_length = AudioSegment.from_file(file_path).duration_seconds
                        elif secondary_output_name in file_path:
                            s3_key = f"conversions/{task_id}_noise.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            output_noise = s3_key
                        else:
                            pass
                    out_obj = {
                        'no_noise' : output_no_noise, 
                        'noise' : output_noise, 
                        'conversion_duration' : conversion_length
                    }

            elif mode == "stem_extractor":
                if not output_filepaths:
                    raise Exception("Output files not found")

                # Initialize a dictionary to store file paths
                out_obj = {
                    "bass": "",
                    "drums": "",
                    "guitar": "",
                    "other": "",
                    "piano": "",
                    "vocals": "", 
                }
                conversion_length = 0
                # Categorize files dynamically
                for file_path in output_filepaths:
                    file_path = self.get_full_file_path(file_path)
                    if not conversion_length:
                        conversion_length = AudioSegment.from_file(file_path).duration_seconds
                        out_obj['conversion_duration'] = conversion_length
                    self.logger.debug(f"Got file path : {file_path}")
                    file_ext = file_path.split(".")[-1]
                    for key in out_obj.keys():
                        if key.capitalize() in file_path:
                            s3_key = f"conversions/{task_id}_{key}.{file_ext}"
                            self.s3Helper.upload_file(file_path, s3_key, "lalals")
                            out_obj[key] = s3_key
                            break
            return out_obj
        except Exception as e:
            self.logger.exception(e)
            raise e

    
    def handler(self, event):
        global valid_modes
        try:
            arguments = event['input']['arguments']
            task_id = arguments['task_id']
            out_obj = self.run(task_id, arguments)
            out_obj['task_id'] = task_id
            return success(out_obj)
        except Exception as e:
            self.logger.exception(e)
            out_obj = {
                'task_id' : task_id
            }
            return error(out_obj)




def main():
    pipeline = AudioUtiltiesServerlessPipeline()
    runpod.serverless.start({
        "handler": pipeline.handler,
        "concurrency_modifier" : adjust_concurrency
    })
    
if __name__ == "__main__":
    main()

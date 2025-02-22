from audio_separator.separator import Separator
from utils.logger import get_logger
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import List

class AudioSeparator():
    def __init__(self, output_dir = "/tmp/outputs", model_file_dir = "/runpod-volume/audio-separator-models", output_format = "WAV") -> None:
        try:
            self.logger = get_logger("AudioSeparator")

            mdx_params={"hop_length": 1024, "segment_size": 256, "overlap": 0.25, "batch_size": 1, "enable_denoise": False}
            vr_params={"batch_size": 1, "window_size": 1024, "aggression": 5, "enable_tta": True, "enable_post_process": True, "post_process_threshold": 0.2, "high_end_process": False}
            demucs_params={"segment_size": "Default", "shifts": 4, "overlap": 0.9, "segments_enabled": True}
            mdxc_params={"segment_size": 512, "override_model_segment_size": True, "batch_size": 1, "overlap": 25, "pitch_shift": 0}
            self.separator = Separator(output_dir=output_dir, model_file_dir=model_file_dir, output_format = output_format, mdx_params=mdx_params, vr_params=vr_params, demucs_params=demucs_params, mdxc_params=mdxc_params )

            # self.separator = Separator(output_dir=output_dir, model_file_dir=model_file_dir, output_format=output_format)
            self.logger.info("Audio Separator Initialized Successfully")
        except Exception as e:
            self.logger.error(e)
            raise e 

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.is_instance_schema(cls)

    def load_model(self, model_name : str):
        try:
            self.separator.load_model(model_name)
        except Exception as e:
            self.logger.error(e)
            raise e 
    
    def run(self, file_path : str, custom_output_names = None):
        try:
            out_filepaths = self.separator.separate(file_path, custom_output_names=custom_output_names)
            return out_filepaths
        except Exception as e:
            self.logger.error(e)
            raise e

    def run_extractor(self, model_name : str, file_path : str, custom_output_names = None) -> List[str]:
        try:
            self.load_model(model_name)
            out_filepaths = self.separator.separate(file_path, custom_output_names=custom_output_names)
            return out_filepaths
        except Exception as e:
            self.logger.error(e)
            raise e
        


if __name__ == "__main__":
    sep = AudioSeparator(model_file_dir='/tmp/audio-separator-models/')
    # sep.load_model("deverb_bs_roformer_8_384dim_10depth.ckpt")
    sep.load_model("model_bs_roformer_ep_317_sdr_12.9755.ckpt")
    # file_path = "/Users/sakarghimire/LALALS/RVCAudioPreprocessor/12259a96-97b6-4c2a-bbd9-9489b0e37bbe.mp3"
    file_path = "outputs/testERror123456_(Vocals)_UVR_MDXNET_KARA_2.wav"
    
    primary_output_name = "1_reverb"
    secondary_output_name = "1_noreverb"
    out_files = sep.run(file_path, primary_output_name=primary_output_name, secondary_output_name=secondary_output_name)
    # out_files = sep.remove_reverb(file_path)
    # out_files = sep2.run(file_path)
    print(out_files)
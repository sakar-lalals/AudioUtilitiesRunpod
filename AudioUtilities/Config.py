import os 
from pydantic.dataclasses import dataclass

@dataclass
class AudioConfig:
    aws_access_key: str
    aws_secret_key: str
    aws_region: str
    aws_bucket: str
    model_dir: str
    output_dir: str
    elevenlabs_api_key : str
    output_format: str = "wav"



class AudioPipelineConfig(AudioConfig):
    """Runtime configuration loader extending base AudioConfig"""
    def __init__(self, model_args : dict):
        super().__init__(
            aws_access_key=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_key=os.getenv("AWS_SECRET_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_bucket=os.getenv("AWS_BUCKET", "lalals"),
            model_dir="./audio-separator-models",
            output_dir="/tmp/outputs",
            output_format="wav", 
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY")
        )        
        # Model configurations
        self.vocal_extractor_model = (
            model_args.get("vocal_extractor") or
            os.getenv("VOCAL_EXTRACTOR_MODEL", "Kim_Vocal_2.onnx")
        )

        self.instrumental_extractor_model = (
            model_args.get("instrumental_extractor") or
            os.getenv("INSTRUMENTAL_EXTRACTOR_MODEL", "MDX23C-8KFFT-InstVoc_HQ_2.ckpt")
        )

        self.lead_back_splitter = (
            model_args.get("lead_back_splitter") or
            os.getenv("LEAD_BACK_SPLITTER_MODEL", "UVR-BVE-4B_SN-44100-1.pth")
        )

        self.de_echo_model = (
            model_args.get("de_echo") or
            os.getenv("DE_ECHO_MODEL", "UVR-De-Echo-Aggressive.pth")
        )

        self.de_reverb_model = (
            model_args.get("de_reverb") or
            os.getenv("DE_REVERB_MODEL", "deverb_bs_roformer_8_384dim_10depth.ckpt")
        )

        self.de_noise_model = (
            model_args.get("de_noise") or
            os.getenv("DE_NOISE_MODEL", "UVR-DeNoise.pth")
        )

        self.deecho_dereverb_model_combined = (
            model_args.get("deecho_dereverb_combined") or
            os.getenv("DE_ECHO_DE_REVERB_MODEL", "UVR-DeEcho-DeReverb.pth")
        )

        self.stem_extractor_model = (
            model_args.get("stem_extractor") or
            os.getenv("STEM_EXTRACTOR_MODEL", "htdemucs_6s.yaml")
        )

OUTPUT_NAME_CONFIG = {
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt": ("vocals", "instrumental"),
    "Kim_Vocal_2.onnx" : ("vocals", "instrumental"),
    "model_bs_roformer_ep_937_sdr_10.5309.ckpt": ("vocals", "instrumental"),
    "MDX23C-8KFFT-InstVoc_HQ_2.ckpt" : ("vocals", "instrumental"),
    "UVR-BVE-4B_SN-44100-1.pth" : ("vocals", "instrumental"),
    "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt" : ("vocals", "instrumental"),
    "UVR-De-Echo-Aggressive.pth" : ("no echo", "echo"), 
    "UVR-DeNoise.pth" : ("noise", "no noise"),
    "deverb_bs_roformer_8_384dim_10depth.ckpt": ("noreverb", "reverb"),
    "htdemucs_6s.yaml" : ("vocals", "drums", "bass", "guitar", "piano", "other"), 
    "htdemucs_ft.yaml" : ("vocals", "drums", "bass", "other"), 
}
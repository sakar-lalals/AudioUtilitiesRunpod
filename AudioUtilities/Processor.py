import os 
import sys
sys.path.append(os.path.basename(''))

from abc import ABC, abstractmethod
from .Context import AudioProcessingContext
from .Config import OUTPUT_NAME_CONFIG
from typing import List, Dict, Type
from utils.exceptions import OutputNameConfigNotFoundException
from utils.Elevenlabs import SoundEffectCreator

class AudioProcessor(ABC):
    """Abstract base class for audio processing strategies"""
    
    @abstractmethod
    def process(self, context: 'AudioProcessingContext') -> List[str]:
        pass

class BaseExtractorProcessor(AudioProcessor):
    """Base class for all extractors that use output names"""
    
    def get_model_name(self, context: 'AudioProcessingContext') -> str:
        """Override this method in child classes to specify the model name"""
        raise NotImplementedError("Subclasses must implement get_model_name()")

    def _determine_output_key(self, file_path: str, context: AudioProcessingContext) -> str:
        """Determine output key based on file naming conventions"""
        filename = os.path.basename(file_path)
        return filename.replace(f"{context.task_id}_", "").split(".")[0]

    def _get_full_file_path(self, file_path : str, context : AudioProcessingContext) -> str:
        """ Returns the full file path, respective to the output director"""
        return os.path.join(context.config.output_dir, file_path)

    def _filter_outputs(self, output_files, output_stems, context : AudioProcessingContext):
        """
        Filter the outputs. Only returns the output_files for the respective output_stems
        """
        filtered_outputs = []
        for file_path in output_files:
            output_key = self._determine_output_key(file_path, context)
            if output_key in output_stems:
                filtered_outputs.append(file_path)
            else:
                # its an unexpected files: remove it 
                file_path = self._get_full_file_path(file_path, context)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        return filtered_outputs

    def process(self, context: 'AudioProcessingContext') -> List[str]:
        # Get model name from the specific processor
        model_name = self.get_model_name(context)
        output_stems_ = OUTPUT_NAME_CONFIG.get(model_name)
        if not output_stems_:
            raise OutputNameConfigNotFoundException(
                f"Output name config not found for model: {model_name}"
            )
        output_names = context.generate_output_names(*output_stems_)
        out_files =  context.separator.run_extractor(
            model_name, context.input_path, custom_output_names=output_names
        )
        return out_files

class VocalExtractorProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.vocal_extractor_model

class InstrumentalExtractorProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.instrumental_extractor_model

class VocalInstrumentalExtractor(BaseExtractorProcessor):
    def process(self, context: 'AudioProcessingContext') -> List[str]:
        # Run the vocal extractor first
        model_name = context.config.vocal_extractor_model
        output_stems_ = ("vocals",)
        output_names = context.generate_output_names(*output_stems_)
        vocal_files = context.separator.run_extractor(
            model_name, context.input_path, custom_output_names=output_names
        )
        vocal_files = self._filter_outputs(vocal_files, output_stems_, context)

        # Run instrumental extractor
        output_stems_ = ("instrumental",)
        output_names = context.generate_output_names(*output_stems_)
        # Run the instrumental extractor on the same input
        instrumental_files = context.separator.run_extractor(
            context.config.instrumental_extractor_model, context.input_path, output_names
        )
        instrumental_files = self._filter_outputs(instrumental_files, output_stems_, context)
        # Combine the results
        return vocal_files + instrumental_files
    
class LeadBackVocalExtractor(BaseExtractorProcessor):
    def process(self, context: 'AudioProcessingContext') -> List[str]:
        # Run the vocal extractor first
        model_name = context.config.vocal_extractor_model
        output_stems_ = ("vocals", "instrumental")
        output_names = context.generate_output_names(*output_stems_)
        vocal_files = context.separator.run_extractor(
            model_name, context.input_path, custom_output_names=output_names
        )
        # Run Back Vocal Extractor on the extracted vocals
        vocal_files = self._filter_outputs(vocal_files, output_stems_, context)

        vocal_filepath = f"{context.task_id}_vocals.wav"
        instrumental_filepath = f"{context.task_id}_instrumental.wav"
        assert instrumental_filepath in vocal_files, "Error extracting instrumental stems"
        assert vocal_filepath in vocal_files, "Error extracting vocal stems"

        input_filename = self._get_full_file_path(vocal_filepath, context)
        output_stems_ = ("vocal_front", "vocal_back")

        ## use a custom output name format for the lead back splitter
        output_names = {
            'vocals' : 'vocal_back', 
            'instrumental' : 'vocal_front'
        }
        model_name = context.config.lead_back_splitter
        output_files = context.separator.run_extractor(
            model_name, input_filename, output_names
        )
        # appending instrumental stem to output files
        output_files.append(instrumental_filepath)
        return output_files

class DeNoiseProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.de_noise_model

class DeEchoProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.de_echo_model

class DeReverbProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.de_reverb_model

class StemExtractorProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.stem_extractor_model

class StemExtractorProcessor(BaseExtractorProcessor):
    def get_model_name(self, context : 'AudioProcessingContext') -> str:
        return context.config.stem_extractor_model

class SoundCreatorProcessor(BaseExtractorProcessor):
    def process(self, context : 'AudioProcessingContext') -> str:
        output_filename = self._get_sound_creator_output_filename(context)
        output_filepath = self._get_full_file_path(output_filename, context)
        el_ = SoundEffectCreator(api_key=context.config.elevenlabs_api_key)
        output_filepath = el_.run(context.task_id, context.input_prompt, context.audio_length, out_file_path=output_filepath)
        assert os.path.isfile(output_filepath), "Error creating sound"
        # return the base filename to be in sync with the downstream processing
        return [output_filename] 

    def _get_sound_creator_output_filename(self, context : 'AudioProcessingContext'):
        return f"{context.task_id}_sound.wav"




class ProcessingStrategyRegistry:
    """Registry pattern for audio processing strategies"""
    
    _strategies: Dict[str, Type[AudioProcessor]] = {
        "vocal_extractor": VocalExtractorProcessor,
        "vocal_instrumental_extractor" : VocalInstrumentalExtractor,
        "lead_back_vocal_extractor" : LeadBackVocalExtractor,
        "instrumental_extractor": InstrumentalExtractorProcessor,
        "stem_extractor": StemExtractorProcessor,
        "de_reverb" : DeReverbProcessor, 
        "de_echo": DeEchoProcessor, 
        "de_noise": DeNoiseProcessor, 
        "sound_creator": SoundCreatorProcessor
    }

    @classmethod
    def get_strategy(cls, mode: str) -> Type[AudioProcessor]:
        strategy = cls._strategies.get(mode)
        if not strategy:
            raise ValueError(f"Unsupported processing mode: {mode}")
        return strategy

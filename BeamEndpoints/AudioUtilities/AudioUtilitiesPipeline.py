from beam import function, task_queue, QueueDepthAutoscaler, Image, Volume
import os 
import sys 
sys.path.append(os.path.basename(''))

from AudioUtilities.AudioPipeline import AudioPipelineConfig, AudioPipeline

@task_queue(
    cpu = 12, 
    workers = 2,
    memory = "32Gi",
    gpu = "RTX4090",
    autoscaler=QueueDepthAutoscaler(min_containers=1, max_containers=5, tasks_per_container=3),
    image=Image(
            base_image="nvidia/cuda:12.8.0-cudnn-devel-ubuntu20.04",
            python_version="python3.10", 
            python_packages="requirements_audioutilities.txt", 
            commands= ['apt-get update -y && apt-get install ffmpeg -y \
                       && pip install numpy>=1.21.6 \
                       && pip install elevenlabs==1.50.5 \
                       && pip install onnxruntime-gpu \
                       && pip install audio-separator==0.28.5']),
    volumes=[
        Volume(mount_path="./audio-separator-models", name="audio-separator-models"),
    ],
    secrets=["AWS_ACCESS_KEY", "AWS_SECRET_KEY", "AWS_REGION", "AWS_BUCKET_NAME", "ELEVENLABS_API_KEY"])

def audio_utilities_processor(**inputs):
    model_args = inputs.get("models", {})
    config = AudioPipelineConfig(model_args)
    pipeline = AudioPipeline(config)
    task_id = inputs['task_id']
    mode = inputs['mode']
    s3_path = inputs.get("audio_path_s3")
    input_prompt = inputs.get("input_prompt", "")
    audio_length = inputs.get("audio_length")
    return pipeline.execute_pipeline(task_id, mode, s3_path, input_prompt, audio_length)



if __name__ == "__main__":
    inputs = {
        'task_id' : 'test_task', 
        'mode' : 'sound_creator', 
        # 'audio_path_s3' : "files/9546d8c7-6e39-403a-a9af-53ba9604818a.wav",
        'input_prompt': 'sad sound echo for movie background in emotional scene', 
        'audio_length' : None
    }
    resp = audio_utilities_processor(**inputs)
    print(resp)
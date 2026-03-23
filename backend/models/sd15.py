import torch
from diffusers import StableDiffusionPipeline
from config.settings import settings

_pipe = None

def get_sd15_pipe():
    global _pipe
    if _pipe is None:
        _pipe = StableDiffusionPipeline.from_pretrained(
            settings.SD15_MODEL,
            torch_dtype=torch.float32,   # float32 on CPU
            safety_checker=None,
        )
        if settings.ENABLE_CPU_OFFLOAD:
            _pipe.enable_sequential_cpu_offload()
        _pipe.enable_attention_slicing()
    return _pipe

def generate_image(prompt: str, negative_prompt: str = "", steps: int = None):
    pipe = get_sd15_pipe()
    steps = steps or settings.MAX_STEPS_SD15
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        guidance_scale=7.5,
    )
    return result.images[0]
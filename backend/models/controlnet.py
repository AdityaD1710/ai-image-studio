import torch
import numpy as np
from PIL import Image
import cv2
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel
from config.settings import settings

_cn_pipe = None

def get_controlnet_pipe():
    global _cn_pipe
    if _cn_pipe is None:
        controlnet = ControlNetModel.from_pretrained(
            settings.CONTROLNET_MODEL,
            torch_dtype=torch.float32,
        )
        _cn_pipe = StableDiffusionControlNetPipeline.from_pretrained(
            settings.SD15_MODEL,
            controlnet=controlnet,
            torch_dtype=torch.float32,
            safety_checker=None,
        )
        if settings.ENABLE_CPU_OFFLOAD:
            _cn_pipe.enable_sequential_cpu_offload()
        _cn_pipe.enable_attention_slicing()
    return _cn_pipe

def _canny_edges(pil_image: Image.Image) -> Image.Image:
    gray = np.array(pil_image.convert("L"))
    edges = cv2.Canny(gray, 100, 200)
    return Image.fromarray(edges).convert("RGB")

def edit_with_controlnet(
    pil_image: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    steps: int = None,
) -> Image.Image:
    pipe = get_controlnet_pipe()
    control_image = _canny_edges(pil_image)
    steps = steps or settings.MAX_STEPS_SD15

    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=control_image,
        num_inference_steps=steps,
        guidance_scale=7.5,
        controlnet_conditioning_scale=0.8,
    )
    return result.images[0]
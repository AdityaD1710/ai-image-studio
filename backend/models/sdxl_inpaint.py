import torch
from PIL import Image
from diffusers import StableDiffusionXLInpaintPipeline, ControlNetModel
from config.settings import settings
import numpy as np
import cv2

_sdxl_pipe = None

def get_sdxl_inpaint_pipe():
    global _sdxl_pipe
    if _sdxl_pipe is None:
        controlnet = ControlNetModel.from_pretrained(
            settings.CONTROLNET_SDXL_MODEL,
            torch_dtype=torch.float32,
        )
        _sdxl_pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            settings.SDXL_MODEL,
            controlnet=controlnet,
            torch_dtype=torch.float32,
        )
        if settings.ENABLE_CPU_OFFLOAD:
            _sdxl_pipe.enable_sequential_cpu_offload()
        _sdxl_pipe.enable_attention_slicing()
    return _sdxl_pipe

def inpaint(
    pil_image: Image.Image,
    mask_pil: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    steps: int = None,
) -> Image.Image:
    pipe = get_sdxl_inpaint_pipe()
    steps = steps or settings.MAX_STEPS_SDXL

    # Canny on original for ControlNet guidance
    gray = np.array(pil_image.convert("L"))
    edges = cv2.Canny(gray, 100, 200)
    control_image = Image.fromarray(edges).convert("RGB")

    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=pil_image,
        mask_image=mask_pil,
        control_image=control_image,
        num_inference_steps=steps,
        guidance_scale=8.0,
        strength=0.99,
    )
    return result.images[0]
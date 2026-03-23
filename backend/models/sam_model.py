import numpy as np
import torch
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
from config.settings import settings
from PIL import Image

_sam = None
_mask_gen = None

def get_mask_generator():
    global _sam, _mask_gen
    if _mask_gen is None:
        _sam = sam_model_registry[settings.SAM_MODEL_TYPE](
            checkpoint=settings.SAM_CHECKPOINT
        )
        _sam.to(settings.DEVICE)
        _mask_gen = SamAutomaticMaskGenerator(
            _sam,
            points_per_side=16,       # reduced for CPU speed
            pred_iou_thresh=0.88,
            stability_score_thresh=0.95,
        )
    return _mask_gen

def segment_image(pil_image: Image.Image) -> list[dict]:
    generator = get_mask_generator()
    img_array = np.array(pil_image.convert("RGB"))
    masks = generator.generate(img_array)
    # Sort by area desc, return top 10 to stay manageable
    masks.sort(key=lambda x: x["area"], reverse=True)
    return masks[:10]
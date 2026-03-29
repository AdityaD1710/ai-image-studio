import uuid
import base64
from io import BytesIO
from PIL import Image
import numpy as np

from models.sd15 import generate_image
from models.sam_model import segment_image
from models.clip_model import label_segments
from models.controlnet import edit_with_controlnet
from models.sdxl_inpaint import inpaint

def pil_to_b64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def b64_to_pil(b64: str) -> Image.Image:
    data = base64.b64decode(b64)
    return Image.open(BytesIO(data)).convert("RGB")


def _pick_inpaint_segment(labeled_masks: list[dict]) -> dict | None:
    if not labeled_masks:
        return None

    preferred_labels = {
        "furniture",
        "sofa",
        "armchair",
        "vase",
        "chair",
        "coffee table",
        "dining table",
        "side table",
        "table",
        "bed",
        "lamp",
        "cabinet",
        "shelf",
        "bookshelf",
        "tv stand",
        "nightstand",
        "rug",
        "curtain",
        "window",
        "door",
        "wall art",
        "mirror",
        "ceiling light",
        "decor",
        "indoor plant",
    }

    preferred = [m for m in labeled_masks if m.get("label", "").lower() in preferred_labels]
    if preferred:
        return preferred[0]
    return labeled_masks[0]

def run_full_pipeline(payload: dict) -> dict:
    """
    Full pipeline:
    1. SD1.5 → generate base image
    2. SAM  → segment
    3. CLIP → label segments
    4. ControlNet → edge-guided edit
    5. Optional SDXL + ControlNet → inpaint masked region after regeneration
    """
    prompt = payload["prompt"]
    negative_prompt = payload.get("negative_prompt", "")
    mask_b64 = payload.get("mask_b64")
    inpaint_prompt = payload.get("inpaint_prompt", prompt)
    enable_inpaint = bool(payload.get("enable_inpaint", False))
    room_type = payload.get("room_type", "generic")
    steps_sd15 = payload.get("steps_sd15")
    steps_sdxl = payload.get("steps_sdxl")

    # Step 1 – Generate
    base_img = generate_image(prompt, negative_prompt, steps=steps_sd15)

    # Step 2 – Segment
    masks = segment_image(base_img)

    # Step 3 – Label
    labeled_masks = label_segments(base_img, masks, room_type=room_type)

    # Step 4 – Regenerate/edit with ControlNet
    edited_img = edit_with_controlnet(base_img, prompt, negative_prompt, steps=steps_sd15)

    final_img = edited_img
    inpaint_applied = False

    # Step 5 – Optional inpaint after regeneration
    if enable_inpaint:
        if mask_b64:
            mask_pil = b64_to_pil(mask_b64).convert("L")
        else:
            selected = _pick_inpaint_segment(labeled_masks)
            if selected is not None:
                mask_arr = (np.array(selected["segmentation"]) * 255).astype("uint8")
                mask_pil = Image.fromarray(mask_arr)
            else:
                # Empty fallback mask (no SAM segments found)
                mask_pil = Image.new("L", edited_img.size, 0)

        final_img = inpaint(
            edited_img,
            mask_pil,
            inpaint_prompt,
            negative_prompt,
            steps=steps_sdxl,
        )
        inpaint_applied = True

    return {
        "job_id": str(uuid.uuid4()),
        "base_image": pil_to_b64(base_img),
        "edited_image": pil_to_b64(edited_img),
        "final_image": pil_to_b64(final_img),
        "inpaint_applied": inpaint_applied,
        "room_type": room_type,
        "segments": [
            {"label": m["label"], "confidence": round(m["confidence"], 3), "bbox": m["bbox"]}
            for m in labeled_masks
        ],
    }
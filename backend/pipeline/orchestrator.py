import uuid
import base64
from io import BytesIO
from PIL import Image

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

def run_full_pipeline(payload: dict) -> dict:
    """
    Full pipeline:
    1. SD1.5 → generate base image
    2. SAM  → segment
    3. CLIP → label segments
    4. ControlNet → edge-guided edit
    5. SDXL + ControlNet → inpaint masked region
    """
    prompt = payload["prompt"]
    negative_prompt = payload.get("negative_prompt", "")
    mask_b64 = payload.get("mask_b64")          # optional user-drawn mask
    inpaint_prompt = payload.get("inpaint_prompt", prompt)

    # Step 1 – Generate
    base_img = generate_image(prompt, negative_prompt)

    # Step 2 – Segment
    masks = segment_image(base_img)

    # Step 3 – Label
    labeled_masks = label_segments(base_img, masks)

    # Step 4 – ControlNet edit
    edited_img = edit_with_controlnet(base_img, prompt, negative_prompt)

    # Step 5 – Inpaint (use user mask if given, else use largest SAM segment)
    if mask_b64:
        mask_pil = b64_to_pil(mask_b64).convert("L")
    else:
        # Build mask from largest segment
        import numpy as np
        largest = labeled_masks[0]["segmentation"]
        mask_arr = (np.array(largest) * 255).astype("uint8")
        mask_pil = Image.fromarray(mask_arr)

    final_img = inpaint(edited_img, mask_pil, inpaint_prompt, negative_prompt)

    return {
        "job_id": str(uuid.uuid4()),
        "base_image": pil_to_b64(base_img),
        "edited_image": pil_to_b64(edited_img),
        "final_image": pil_to_b64(final_img),
        "segments": [
            {"label": m["label"], "confidence": round(m["confidence"], 3), "bbox": m["bbox"]}
            for m in labeled_masks
        ],
    }
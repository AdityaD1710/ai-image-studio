import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from config.settings import settings

_model = None
_processor = None

CANDIDATE_LABELS = [
    "sky", "person", "tree", "building", "water", "road",
    "car", "animal", "background", "object", "clothing", "face",
    "grass", "mountain", "furniture",
]

def get_clip():
    global _model, _processor
    if _model is None:
        _model = CLIPModel.from_pretrained(settings.CLIP_MODEL)
        _processor = CLIPProcessor.from_pretrained(settings.CLIP_MODEL)
        _model.eval()
    return _model, _processor

def label_segments(pil_image: Image.Image, masks: list[dict]) -> list[dict]:
    model, processor = get_clip()
    labeled = []
    for mask in masks:
        bbox = mask["bbox"]   # [x, y, w, h]
        x, y, w, h = [int(v) for v in bbox]
        crop = pil_image.crop((x, y, x + w, y + h))

        inputs = processor(
            text=CANDIDATE_LABELS,
            images=crop,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]
        best_idx = probs.argmax().item()

        labeled.append({
            **mask,
            "label": CANDIDATE_LABELS[best_idx],
            "confidence": float(probs[best_idx]),
        })
    return labeled
import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from config.settings import settings

_model = None
_processor = None

BASE_CANDIDATE_LABELS = [
    "sofa",
    "armchair",
    "chair",
    "coffee table",
    "dining table",
    "side table",
    "cabinet",
    "bookshelf",
    "tv stand",
    "bed",
    "nightstand",
    "lamp",
    "vase",
    "indoor plant",
    "rug",
    "curtain",
    "window",
    "door",
    "wall art",
    "mirror",
    "ceiling light",
    "decor",
    "furniture",
    "background",
]

ROOM_TYPE_LABELS = {
    "generic": BASE_CANDIDATE_LABELS,
    "living_room": [
        "sofa", "armchair", "coffee table", "side table", "tv stand", "bookshelf",
        "lamp", "vase", "indoor plant", "rug", "curtain", "window", "door",
        "wall art", "mirror", "ceiling light", "decor", "furniture", "background",
    ],
    "bedroom": [
        "bed", "nightstand", "cabinet", "chair", "lamp", "rug", "curtain",
        "window", "door", "mirror", "wall art", "ceiling light", "decor",
        "furniture", "background",
    ],
    "kitchen": [
        "cabinet", "dining table", "chair", "side table", "window", "door",
        "ceiling light", "decor", "furniture", "background",
    ],
    "dining_room": [
        "dining table", "chair", "cabinet", "side table", "lamp", "vase",
        "window", "door", "wall art", "ceiling light", "decor", "furniture", "background",
    ],
    "office": [
        "chair", "side table", "cabinet", "bookshelf", "lamp", "window", "door",
        "wall art", "ceiling light", "decor", "furniture", "background",
    ],
}

INTERIOR_PRIORITY_LABELS = {
    "sofa",
    "armchair",
    "chair",
    "coffee table",
    "dining table",
    "side table",
    "cabinet",
    "bookshelf",
    "tv stand",
    "bed",
    "nightstand",
    "lamp",
    "vase",
    "indoor plant",
    "rug",
    "curtain",
    "window",
    "door",
    "wall art",
    "mirror",
    "ceiling light",
    "decor",
    "furniture",
}


def _normalize_room_type(room_type: str | None) -> str:
    if not room_type:
        return "generic"
    normalized = room_type.strip().lower().replace(" ", "_")
    return normalized if normalized in ROOM_TYPE_LABELS else "generic"


def _candidate_labels_for_room(room_type: str | None) -> list[str]:
    return ROOM_TYPE_LABELS[_normalize_room_type(room_type)]

def get_clip():
    global _model, _processor
    if _model is None:
        _model = CLIPModel.from_pretrained(settings.CLIP_MODEL)
        _processor = CLIPProcessor.from_pretrained(settings.CLIP_MODEL)
        _model.eval()
    return _model, _processor

def label_segments(pil_image: Image.Image, masks: list[dict], room_type: str = "generic") -> list[dict]:
    model, processor = get_clip()
    candidate_labels = _candidate_labels_for_room(room_type)
    labeled = []
    for mask in masks:
        bbox = mask["bbox"]   # [x, y, w, h]
        x, y, w, h = [int(v) for v in bbox]
        if w <= 2 or h <= 2:
            continue

        crop = pil_image.crop((x, y, x + w, y + h))

        inputs = processor(
            text=candidate_labels,
            images=crop,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]
        best_idx = probs.argmax().item()
        label = candidate_labels[best_idx]
        confidence = float(probs[best_idx])

        labeled.append({
            **mask,
            "label": label,
            "confidence": confidence,
        })

    if not labeled:
        return []

    interior = [m for m in labeled if m.get("label", "").lower() in INTERIOR_PRIORITY_LABELS]
    filtered = [
        m
        for m in interior
        if m.get("confidence", 0.0) >= 0.12 and int(m["bbox"][2]) * int(m["bbox"][3]) >= 900
    ]

    if not filtered:
        # Keep best interior candidates if confidence/size thresholds are too strict for a scene.
        filtered = sorted(
            interior,
            key=lambda m: (float(m.get("confidence", 0.0)), float(m.get("area", 0))),
            reverse=True,
        )[:8]

    if filtered:
        return sorted(
            filtered,
            key=lambda m: (float(m.get("confidence", 0.0)), float(m.get("area", 0))),
            reverse=True,
        )[:8]

    # Fallback to strongest predictions if no interior labels were detected.
    return sorted(
        labeled,
        key=lambda m: (float(m.get("confidence", 0.0)), float(m.get("area", 0))),
        reverse=True,
    )[:5]
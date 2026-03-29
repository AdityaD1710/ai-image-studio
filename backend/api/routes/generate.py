import os
import sys
import uuid
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from schemas.requests import GenerateRequest

router = APIRouter()

# Make top-level modules (e.g., scripts/) importable when running from backend/.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def _log_generate_failure(job_id: str, stage: str, error: Exception | str, payload: dict) -> None:
    """Persist backend-side failure context for a job to aid debugging."""
    try:
        out_dir = REPO_ROOT / "storage" / "outputs" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        error_text = str(error)
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "error_type": error.__class__.__name__ if isinstance(error, Exception) else "RuntimeError",
            "error": error_text,
            "job_id": job_id,
            "payload": {
                "prompt": payload.get("prompt", ""),
                "negative_prompt": payload.get("negative_prompt", ""),
                "room_type": payload.get("room_type", "generic"),
                "enable_inpaint": bool(payload.get("enable_inpaint", False)),
                "steps_sd15": payload.get("steps_sd15"),
                "steps_sdxl": payload.get("steps_sdxl"),
                "low_vram": bool(payload.get("low_vram", True)),
                "cache_debug": bool(payload.get("cache_debug", True)),
            },
        }
        with open(out_dir / "backend_error.json", "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=True, indent=2)
    except Exception:
        # Logging must never break request handling.
        return

@router.post("/generate")
async def generate(req: GenerateRequest):
    payload = req.dict()
    payload["job_id"] = str(uuid.uuid4())
    job_id = payload["job_id"]

    loop = asyncio.get_event_loop()
    use_colab = os.getenv("USE_COLAB", "true").lower() == "true"

    if not use_colab:
        raise HTTPException(
            status_code=503,
            detail="Remote generation is disabled. Set USE_COLAB=true to run generation on your Colab server.",
        )

    from scripts.colab_runner import run_on_colab, colab_preflight

    # Fail fast when Colab endpoint is not reachable, before long-running generation starts.
    preflight = await loop.run_in_executor(None, colab_preflight)
    if not preflight.get("ready", False):
        detail = preflight.get("error") or "Colab preflight failed. Check /api/colab/preflight for details."
        _log_generate_failure(job_id, "preflight", detail, payload)
        raise HTTPException(status_code=502, detail=detail)

    request_timeout = int(os.getenv("BACKEND_GENERATE_TIMEOUT_SECONDS", os.getenv("COLAB_TIMEOUT_SECONDS", "3600")))
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, run_on_colab, payload),
            timeout=request_timeout,
        )
    except asyncio.TimeoutError as exc:
        detail = (
            f"Timed out waiting for Colab generation after {request_timeout}s. "
            "Check Colab runtime logs and retry with fewer steps."
        )
        _log_generate_failure(job_id, "generate_timeout", detail, payload)
        raise HTTPException(status_code=504, detail=detail) from exc
    except (EnvironmentError, RuntimeError, ValueError, FileNotFoundError) as exc:
        _log_generate_failure(job_id, "generate", exc, payload)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return result


@router.get("/colab/preflight")
async def colab_preflight_status():
    loop = asyncio.get_event_loop()
    from scripts.colab_runner import colab_preflight

    report = await loop.run_in_executor(None, colab_preflight)
    return report


@router.get("/kaggle/preflight")
async def kaggle_preflight_compat():
    """Backward-compatible endpoint alias after migration to Colab server."""
    loop = asyncio.get_event_loop()
    from scripts.colab_runner import colab_preflight

    report = await loop.run_in_executor(None, colab_preflight)
    report["deprecated_endpoint"] = True
    return report
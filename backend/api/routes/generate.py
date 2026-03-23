import os
import sys
import uuid
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from schemas.requests import GenerateRequest

router = APIRouter()

# Make top-level modules (e.g., scripts/) importable when running from backend/.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

@router.post("/generate")
async def generate(req: GenerateRequest):
    payload = req.dict()
    payload["job_id"] = str(uuid.uuid4())

    loop = asyncio.get_event_loop()
    use_colab = os.getenv("USE_COLAB", "true").lower() == "true"

    if not use_colab:
        raise HTTPException(
            status_code=503,
            detail="Remote generation is disabled. Set USE_COLAB=true to run generation on your Colab server.",
        )

    from scripts.colab_runner import run_on_colab
    try:
        result = await loop.run_in_executor(None, run_on_colab, payload)
    except (EnvironmentError, RuntimeError, ValueError, FileNotFoundError) as exc:
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
"""
scripts/kaggle_runner.py
Automates pushing a notebook to Kaggle, polling until completion,
and downloading outputs back to your local machine.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import tempfile
import base64
import uuid
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

KAGGLE_USERNAME  = os.environ.get("KAGGLE_USERNAME", "")
NOTEBOOK_TITLE   = "ai-image-pipeline"
NOTEBOOK_PATH    = REPO_ROOT / "notebooks" / "pipeline.ipynb"
SCRIPT_PATH      = REPO_ROOT / "notebooks" / "pipeline.py"
OUTPUT_DIR       = REPO_ROOT / "storage" / "outputs"
POLL_INTERVAL    = 30    # seconds between status checks
MAX_WAIT         = 3600  # 1-hour hard timeout


# ── Validation ─────────────────────────────────────────────────────────────

def _validate_env() -> None:
    """Raise early with a clear message if credentials are missing."""
    missing = [k for k in ("KAGGLE_USERNAME", "KAGGLE_KEY") if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Add them to your .env file:\n"
            "  KAGGLE_USERNAME=your_username\n"
            "  KAGGLE_KEY=your_api_key"
        )


def _get_kaggle_base_cmd() -> list[str]:
    """Return a runnable Kaggle command prefix."""
    kaggle_exe = shutil.which("kaggle")
    if kaggle_exe:
        return [kaggle_exe]

    # Fallback: use module entrypoint in the active Python env.
    probe = subprocess.run(
        [sys.executable, "-m", "kaggle.cli", "--help"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "kaggle.cli"]

    raise EnvironmentError(
        "Kaggle CLI was not found. Install it in backend venv311:\n"
        "  python -m pip install kaggle\n"
        "Then ensure KAGGLE_USERNAME and KAGGLE_KEY are set."
    )


def _kaggle_subprocess(args: list[str]) -> subprocess.CompletedProcess:
    """Run Kaggle commands with explicit auth env to avoid stale global config."""
    env = os.environ.copy()
    env["KAGGLE_USERNAME"] = os.environ.get("KAGGLE_USERNAME", "")
    env["KAGGLE_KEY"] = os.environ.get("KAGGLE_KEY", "")
    return subprocess.run(args, capture_output=True, text=True, env=env)


def _raise_for_kaggle_failure(action: str, result: subprocess.CompletedProcess) -> None:
    detail = (result.stderr.strip() or result.stdout.strip())
    lowered = detail.lower()
    if "401" in lowered or "unauthorized" in lowered or "unauthenticated" in lowered:
        raise EnvironmentError(
            "Kaggle authentication failed (401 Unauthorized).\n"
            "Regenerate API token in Kaggle: Account > Create New Token, then update .env:\n"
            "  KAGGLE_USERNAME=<your_kaggle_username>\n"
            "  KAGGLE_KEY=<new_api_key>\n"
            "After updating, restart uvicorn."
        )
    raise RuntimeError(f"{action} failed (exit {result.returncode}):\n{detail}")

def _resolve_pipeline_asset() -> Path:
    """Prefer script pipeline; fall back to notebook for backward compatibility."""
    if SCRIPT_PATH.exists():
        return SCRIPT_PATH
    if NOTEBOOK_PATH.exists():
        return NOTEBOOK_PATH
    raise FileNotFoundError(
        "No Kaggle pipeline asset found.\n"
        f"Expected one of:\n  - {SCRIPT_PATH}\n  - {NOTEBOOK_PATH}"
    )


def _validate_pipeline_asset(asset_path: Path) -> None:
    """Raise early if pipeline asset is missing or unreadable."""
    if not asset_path.exists():
        raise FileNotFoundError(f"Pipeline asset not found at: {asset_path}")

    if asset_path.suffix == ".ipynb":
        try:
            with open(asset_path, encoding="utf-8") as f:
                nb = json.load(f)
            if "cells" not in nb:
                raise ValueError("Notebook JSON is missing a 'cells' key.")
        except json.JSONDecodeError as exc:
            raise ValueError(f"{asset_path.name} is not valid JSON: {exc}") from exc
    elif asset_path.suffix == ".py":
        if not asset_path.read_text(encoding="utf-8").strip():
            raise ValueError(f"{asset_path.name} is empty.")
    else:
        raise ValueError(
            f"Unsupported pipeline asset type: {asset_path.suffix}. Use .py or .ipynb"
        )


# ── Notebook injection ──────────────────────────────────────────────────────

def inject_payload_into_notebook(payload: dict, nb_path: Path) -> Path:
    """
    Return a NamedTemporaryFile path containing a copy of the notebook
    with a new first cell that sets PIPELINE_PAYLOAD as an env variable.
    The temp file is the caller's responsibility to delete.
    """
    with open(nb_path, encoding="utf-8") as f:
        nb = json.load(f)

    # Serialize payload safely — escape any single quotes inside the JSON string
    payload_json = json.dumps(payload).replace("'", "\\'")

    inject_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            f"os.environ['PIPELINE_PAYLOAD'] = '{payload_json}'\n",
            "print('Payload injected successfully')\n",
        ],
    }

    # Insert at position 0 so it runs before everything else
    nb["cells"].insert(0, inject_cell)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".ipynb",
        delete=False,
        mode="w",
        encoding="utf-8",
    )
    json.dump(nb, tmp, ensure_ascii=False)
    tmp.close()
    return Path(tmp.name)


def inject_payload_into_script(payload: dict, script_path: Path) -> Path:
    """Return a temp script path with PIPELINE_PAYLOAD injected at top."""
    payload_json = json.dumps(payload).replace("\\", "\\\\").replace("\"", "\\\"")
    original = script_path.read_text(encoding="utf-8")

    injected = (
        "import os\n"
        f"os.environ['PIPELINE_PAYLOAD'] = \"{payload_json}\"\n"
        "print('Payload injected successfully')\n\n"
        f"{original}"
    )

    tmp = tempfile.NamedTemporaryFile(
        suffix=".py",
        delete=False,
        mode="w",
        encoding="utf-8",
    )
    tmp.write(injected)
    tmp.close()
    return Path(tmp.name)


# ── Kaggle API helpers ──────────────────────────────────────────────────────

def push_notebook(nb_path: Path, title: str) -> str:
    """
    Copy notebook + metadata into a temp dir, push via kaggle CLI.
    Returns the kernel slug  e.g. 'username/ai-image-pipeline'.
    """
    slug = f"{KAGGLE_USERNAME}/{title}"
    kaggle_cmd = _get_kaggle_base_cmd()

    is_notebook = nb_path.suffix == ".ipynb"
    meta = {
        "id":                  slug,
        "title":               title,
        "code_file":           nb_path.name,
        "language":            "python",
        "kernel_type":         "notebook" if is_notebook else "script",
        "is_private":          True,
        "enable_gpu":          True,
        "enable_internet":     True,
        "dataset_sources":     [],
        "competition_sources": [],
        "kernel_sources":      [],
    }

    with tempfile.TemporaryDirectory() as td:
        dest_nb   = Path(td) / nb_path.name
        dest_meta = Path(td) / "kernel-metadata.json"

        shutil.copy(nb_path, dest_nb)
        with open(dest_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        result = _kaggle_subprocess([*kaggle_cmd, "kernels", "push", "-p", td])

    if result.returncode != 0:
        _raise_for_kaggle_failure("kaggle kernels push", result)

    print(f"Notebook pushed → {slug}")
    return slug


def wait_for_completion(slug: str) -> bool:
    """
    Poll `kaggle kernels status` every POLL_INTERVAL seconds.
    Returns True on success, False on failure / timeout.
    """
    print(f"Polling {slug} every {POLL_INTERVAL}s …")
    kaggle_cmd = _get_kaggle_base_cmd()
    deadline = time.time() + MAX_WAIT

    while time.time() < deadline:
        result = _kaggle_subprocess([*kaggle_cmd, "kernels", "status", slug])
        raw = (result.stdout + result.stderr).strip().lower()
        print(f"  [{time.strftime('%H:%M:%S')}] {raw}")

        if "complete" in raw:
            print("Kernel completed successfully.")
            return True
        if any(w in raw for w in ("error", "cancel", "fail")):
            print(f"Kernel ended with a non-success status: {raw}")
            return False

        time.sleep(POLL_INTERVAL)

    print("Timed out waiting for Kaggle kernel.")
    return False


def download_outputs(slug: str, dest: Path) -> None:
    """
    Download all kernel output files into dest/.
    The kaggle CLI places files directly (no extra zip wrapper).
    """
    dest.mkdir(parents=True, exist_ok=True)
    kaggle_cmd = _get_kaggle_base_cmd()

    result = _kaggle_subprocess([*kaggle_cmd, "kernels", "output", slug, "-p", str(dest)])

    if result.returncode != 0:
        _raise_for_kaggle_failure("kaggle kernels output", result)

    print(f"Outputs downloaded to: {dest}")


# ── File reading helpers ────────────────────────────────────────────────────

def _read_image_as_b64(path: Path) -> str:
    """Read a PNG/JPG file and return base64-encoded string."""
    if not path.exists():
        raise FileNotFoundError(
            f"Expected output image not found: {path}\n"
            "The Kaggle notebook may not have saved it correctly."
        )
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def _read_result_json(path: Path) -> dict:
    """Read and parse result.json written by the notebook."""
    if not path.exists():
        raise FileNotFoundError(
            f"result.json not found at: {path}\n"
            "The notebook may have crashed before completing."
        )
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"result.json is not valid JSON: {exc}") from exc


def kaggle_preflight() -> dict:
    """Return readiness diagnostics for Kaggle execution without running generation."""
    report = {
        "use_kaggle": os.getenv("USE_KAGGLE", "true").lower() == "true",
        "env_file": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
        "kaggle_username_set": bool(os.environ.get("KAGGLE_USERNAME")),
        "kaggle_key_set": bool(os.environ.get("KAGGLE_KEY")),
        "pipeline_asset": None,
        "kaggle_command": None,
        "auth_ok": False,
        "ready": False,
        "error": None,
    }

    try:
        _validate_env()
        cmd = _get_kaggle_base_cmd()
        report["kaggle_command"] = " ".join(cmd)

        asset = _resolve_pipeline_asset()
        _validate_pipeline_asset(asset)
        report["pipeline_asset"] = str(asset)

        # Auth-required endpoint to verify token validity.
        result = _kaggle_subprocess([*cmd, "kernels", "list", "--mine", "--page-size", "1"])
        if result.returncode != 0:
            _raise_for_kaggle_failure("kaggle kernels list --mine", result)

        report["auth_ok"] = True
        report["ready"] = report["use_kaggle"] and report["auth_ok"]
    except Exception as exc:
        report["error"] = str(exc)

    return report


# ── Main entry point ────────────────────────────────────────────────────────

def run_on_kaggle(payload: dict) -> dict:
    """
    Full automation flow:
      1. Validate env + notebook
      2. Inject prompt payload into notebook
      3. Push to Kaggle
      4. Poll until done
      5. Download outputs
      6. Return base64 images + segment labels

    Raises RuntimeError / FileNotFoundError / EnvironmentError on failure.
    """
    _validate_env()
    pipeline_asset = _resolve_pipeline_asset()
    _validate_pipeline_asset(pipeline_asset)

    job_id  = payload.get("job_id") or str(uuid.uuid4())
    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    patched_nb: Path | None = None
    try:
        # Step 1 — inject payload
        if pipeline_asset.suffix == ".ipynb":
            patched_nb = inject_payload_into_notebook(payload, pipeline_asset)
        else:
            patched_nb = inject_payload_into_script(payload, pipeline_asset)

        # Step 2 — push
        slug = push_notebook(patched_nb, NOTEBOOK_TITLE)

        # Step 3 — wait
        success = wait_for_completion(slug)
        if not success:
            raise RuntimeError(
                f"Kaggle kernel '{slug}' did not complete successfully. "
                "Check https://www.kaggle.com/code for error details."
            )

        # Step 4 — download
        download_outputs(slug, out_dir)

        # Step 5 — read outputs
        result_data = _read_result_json(out_dir / "result.json")

        return {
            "job_id":       job_id,
            "base_image":   _read_image_as_b64(out_dir / "base.png"),
            "edited_image": _read_image_as_b64(out_dir / "edited.png"),
            "final_image":  _read_image_as_b64(out_dir / "final.png"),
            "segments":     result_data.get("segments", []),
            "execution_mode": result_data.get("execution_mode", "kaggle"),
            "gpu_device": result_data.get("gpu_device", "unknown"),
        }

    finally:
        # Always clean up the temp notebook copy
        if patched_nb and patched_nb.exists():
            try:
                os.unlink(patched_nb)
            except OSError:
                pass


# ── CLI usage (test without FastAPI) ───────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AI image pipeline on Kaggle GPU")
    parser.add_argument("--prompt",          required=True,  help="Main image prompt")
    parser.add_argument("--negative-prompt", default="",     help="Negative prompt")
    parser.add_argument("--inpaint-prompt",  default="",     help="Inpaint prompt (defaults to main prompt)")
    args = parser.parse_args()

    payload = {
        "job_id":          str(uuid.uuid4()),
        "prompt":          args.prompt,
        "negative_prompt": args.negative_prompt,
        "inpaint_prompt":  args.inpaint_prompt or args.prompt,
    }

    print(f"\nStarting Kaggle pipeline for: {args.prompt}\n")
    try:
        result = run_on_kaggle(payload)
        print(f"\nDone! Job ID: {result['job_id']}")
        print(f"Segments detected: {[s['label'] for s in result['segments']]}")
        print(f"Images saved to: {OUTPUT_DIR / result['job_id']}/")

        # Save images locally for quick inspection
        out = OUTPUT_DIR / result["job_id"]
        for key in ("base_image", "edited_image", "final_image"):
            fname = key.replace("_image", "") + ".png"
            with open(out / fname, "wb") as fh:
                fh.write(base64.b64decode(result[key]))
        print("Images written to disk.")

    except (EnvironmentError, FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"\nERROR: {e}")
        raise SystemExit(1)
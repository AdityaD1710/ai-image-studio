"""
scripts/colab_runner.py
Calls a user-hosted Colab web server endpoint for remote generation.
"""

import os
import json
import base64
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Also allow backend/.env for users launching uvicorn from backend directory.
BACKEND_ENV_PATH = REPO_ROOT / "backend" / ".env"
if BACKEND_ENV_PATH.exists():
    load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=False)

OUTPUT_DIR = REPO_ROOT / "storage" / "outputs"
DEFAULT_TIMEOUT = int(os.getenv("COLAB_TIMEOUT_SECONDS", "3600"))


def _refresh_env() -> None:
    """Reload env files so runtime picks up recent .env edits."""
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    if BACKEND_ENV_PATH.exists():
        load_dotenv(dotenv_path=BACKEND_ENV_PATH, override=False)


def _derive_generate_from_health(health_url: str) -> str:
    parsed = urllib.parse.urlparse(health_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/health"):
        path = path[: -len("/health")] + "/generate"
    else:
        path = f"{path}/generate" if path else "/generate"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _validate_env() -> str:
    """Return normalized Colab endpoint URL or raise with setup guidance."""
    _refresh_env()

    candidates = [
        os.getenv("COLAB_SERVER_URL", "").strip(),
        os.getenv("COLAB_API_URL", "").strip(),
        os.getenv("COLAB_ENDPOINT", "").strip(),
        os.getenv("COLAB_URL", "").strip(),
    ]
    endpoint = next((value for value in candidates if value), "")

    if not endpoint:
        health = os.getenv("COLAB_HEALTHCHECK_URL", "").strip()
        if health:
            endpoint = _derive_generate_from_health(health)

    if not endpoint:
        raise EnvironmentError(
            "Missing COLAB_SERVER_URL in .env.\n"
            "VS Code Colab extension gives you a remote notebook kernel, not an API URL by itself.\n"
            "To use this backend flow, expose your Colab runtime as an HTTP endpoint and set:\n"
            "  USE_COLAB=true\n"
            "  COLAB_SERVER_URL=https://<public-colab-url>/generate\n"
            "Optional:\n"
            "  COLAB_HEALTHCHECK_URL=https://<public-colab-url>/health\n"
            "  COLAB_TIMEOUT_SECONDS=3600\n"
            "If you do not want an endpoint-based flow, set USE_COLAB=false and use local execution instead."
        )
    return endpoint.rstrip("/")


def _http_json_request(url: str, payload: dict | None, timeout_seconds: int) -> dict:
    """Perform HTTP request and parse JSON response."""
    data = None
    headers = {
        "Accept": "application/json",
        # Required for ngrok free domains to bypass browser interstitial page.
        "ngrok-skip-browser-warning": "true",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Colab server returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        host = urllib.parse.urlparse(url).netloc.lower()
        if "getaddrinfo failed" in reason.lower() and "trycloudflare.com" in host:
            raise RuntimeError(
                f"Failed to reach Colab server at {url}. Details: {exc.reason}\n"
                "Your local DNS cannot resolve this trycloudflare hostname.\n"
                "Use an ngrok URL instead (set NGROK_AUTHTOKEN in Colab, rerun bridge cell, update COLAB_SERVER_URL)."
            ) from exc
        raise RuntimeError(
            f"Failed to reach Colab server at {url}. Details: {exc.reason}"
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Colab server response is not valid JSON: {exc}") from exc


def _derive_healthcheck_url(generate_url: str) -> str:
    """Infer /health from COLAB_SERVER_URL if no explicit URL is provided."""
    explicit = os.getenv("COLAB_HEALTHCHECK_URL", "").strip()
    if explicit:
        return explicit

    parsed = urllib.parse.urlparse(generate_url)
    if parsed.path.endswith("/generate"):
        path = parsed.path[: -len("/generate")] + "/health"
    else:
        base_path = parsed.path.rstrip("/")
        path = f"{base_path}/health" if base_path else "/health"

    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path, "", "", "")
    )


def _fetch_and_encode_image(url: str, timeout_seconds: int) -> str:
    """Download an image URL from Colab and return base64 string."""
    req = urllib.request.Request(
        url=url,
        headers={
            "Accept": "image/*",
            "ngrok-skip-browser-warning": "true",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Image download failed for {url}: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Image download failed for {url}: {exc.reason}") from exc

    return base64.b64encode(data).decode("utf-8")


def _http_ping(url: str, timeout_seconds: int) -> None:
    """Check endpoint reachability without requiring JSON content."""
    req = urllib.request.Request(
        url=url,
        headers={"ngrok-skip-browser-warning": "true"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds):
            return
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Colab healthcheck returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        host = urllib.parse.urlparse(url).netloc.lower()
        if "getaddrinfo failed" in reason.lower() and "trycloudflare.com" in host:
            raise RuntimeError(
                f"Failed to reach Colab healthcheck at {url}: {exc.reason}\n"
                "Your local DNS cannot resolve this trycloudflare hostname.\n"
                "Use an ngrok URL instead (set NGROK_AUTHTOKEN in Colab, rerun bridge cell, update COLAB_SERVER_URL)."
            ) from exc
        raise RuntimeError(f"Failed to reach Colab healthcheck at {url}: {exc.reason}") from exc


def _normalize_response(payload: dict, response: dict, timeout_seconds: int) -> dict:
    """Ensure frontend-compatible output shape."""
    base_image = response.get("base_image")
    edited_image = response.get("edited_image")
    final_image = response.get("final_image")

    if not base_image and response.get("base_image_url"):
        base_image = _fetch_and_encode_image(response["base_image_url"], timeout_seconds)
    if not edited_image and response.get("edited_image_url"):
        edited_image = _fetch_and_encode_image(response["edited_image_url"], timeout_seconds)
    if not final_image and response.get("final_image_url"):
        final_image = _fetch_and_encode_image(response["final_image_url"], timeout_seconds)

    missing = [
        name
        for name, value in (
            ("base_image", base_image),
            ("edited_image", edited_image),
            ("final_image", final_image),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            "Colab response is missing required image fields: "
            + ", ".join(missing)
            + ". Expected base64 fields or *_url variants."
        )

    return {
        "job_id": response.get("job_id", payload.get("job_id", str(uuid.uuid4()))),
        "base_image": base_image,
        "edited_image": edited_image,
        "final_image": final_image,
        "segments": response.get("segments", []),
        "execution_mode": response.get("execution_mode", "colab"),
        "gpu_device": response.get("gpu_device", "unknown"),
    }


def colab_preflight() -> dict:
    """Return readiness diagnostics for Colab execution."""
    _refresh_env()

    report = {
        "use_colab": os.getenv("USE_COLAB", "true").lower() == "true",
        "env_file": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
        "colab_server_url": None,
        "colab_healthcheck_url": None,
        "reachable": False,
        "ready": False,
        "error": None,
    }

    try:
        endpoint = _validate_env()
        health_url = _derive_healthcheck_url(endpoint)
        report["colab_server_url"] = endpoint
        report["colab_healthcheck_url"] = health_url

        _http_ping(health_url, timeout_seconds=30)
        report["reachable"] = True
        report["ready"] = report["use_colab"] and report["reachable"]
    except Exception as exc:
        report["error"] = str(exc)

    return report


def run_on_colab(payload: dict) -> dict:
    """Run remote generation on Colab server and normalize response shape."""
    endpoint = _validate_env()
    timeout_seconds = int(os.getenv("COLAB_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT)))

    response = _http_json_request(endpoint, payload=payload, timeout_seconds=timeout_seconds)
    result = _normalize_response(payload, response, timeout_seconds=timeout_seconds)

    # Persist raw response for debugging each job.
    job_id = result["job_id"]
    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "colab_result.json", "w", encoding="utf-8") as f:
        json.dump(response, f)

    return result

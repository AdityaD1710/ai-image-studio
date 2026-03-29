# AI Image Studio

Professional-grade AI image generation and editing platform with a remote GPU backend.

## Prerequisites

- **Python 3.11** (Required for Windows compatibility with `Pillow==10.3.0`)
- **Google Colab** (Free or Pro) or a local machine with 12GB+ VRAM.
- **Ngrok Account** (For the bridge tunnel).

## Workspace Setup

### 1. Backend
```bash
cd backend
python3.11 -m venv venv311
.\venv311\Scripts\activate  # Windows
# or: source venv311/bin/activate  # Unix
pip install -r requirements.txt
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Running with Colab Backend (Recommended)

To avoid local hardware limitations, use the `pipeline.ipynb` in Google Colab.

### Execution Sequence (CRITICAL)
1. **Cell 1**: Install system dependencies.
2. **Cell 2**: Load the optimized pipeline and "Pre-warm" models. Wait for `All models ready`.
3. **Cell 4**: Paste your **Ngrok Authtoken**.
4. **Cell 5**: Start the Bridge Server.
5. **Local .env**: Copy the generated `Public base URL` into your local `.env` file and restart `main.py`.

## Troubleshooting & Best Practices

### 1. Kernel Died / Out of Memory (OOM)
If the Colab kernel crashes during generation:
- **Use the Optimized Cell 2**: Ensure you are using the version with `low_cpu_mem_usage=True` and `points_per_side=8` for SAM.
- **Pre-loading**: Always run the `load_all_models()` function (included in Cell 2) before starting the server.
- **Restart Session**: If memory is fragmented, go to `Runtime -> Restart session` and re-run cells 1, 2, 4, 5.

### 2. "404 Not Found" (VS Code Colab Extension)
If the VS Code extension fails to restart the kernel:
- **Connection Loss**: This happens when the remote session idles. Disconnect and Reconnect to Google Colab via the VS Code status bar.
- **Browser Fallback**: If the extension is unstable, open the notebook directly in the browser at [colab.research.google.com](https://colab.research.google.com).

### 3. "503 Service Unavailable"
- This means the API server (Cell 5) is running, but the models (Cell 2) are not loaded in that specific kernel instance. **Re-run Cell 2**, then restart Cell 5.

### 4. "500 Internal Server Error" (JSON Serialization)
- **Problem**: The backend tried to send a raw NumPy array to the browser.
- **Fix**: Use the `_json_safe()` helper in the notebook to convert all NumPy types to standard Python floats/lists before returning the response.

## Configuration (.env)

```env
USE_COLAB=true
COLAB_SERVER_URL=https://<your-ngrok-url>.ngrok-free.dev/generate
COLAB_HEALTHCHECK_URL=https://<your-ngrok-url>.ngrok-free.dev/health
COLAB_TIMEOUT_SECONDS=3600
```

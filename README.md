# AI Image Studio

## Prerequisites

- **Python 3.11** (required for `Pillow==10.3.0` compatibility on Windows)
- Docker and Docker Compose (for local services)

## Setup

### Backend

```bash
cd backend

# Create and activate Python 3.11 virtual environment
python3.11 -m venv venv311
.\venv311\Scripts\activate  # On Windows
# or: source venv311/bin/activate  # On Linux/macOS

# Upgrade pip and install dependencies
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Running the Application

### Configure Remote GPU (Colab Server)

Create/update `.env` in the repository root:

```env
USE_COLAB=true
COLAB_SERVER_URL=https://<your-colab-host>/generate
COLAB_HEALTHCHECK_URL=https://<your-colab-host>/health
COLAB_TIMEOUT_SECONDS=3600
```

The backend will call `COLAB_SERVER_URL` for generation and expects JSON with
`base_image`, `edited_image`, `final_image` (base64 strings) and optional
`segments`, `job_id`, `execution_mode`, `gpu_device`.

### Start Services

```bash
docker-compose up -d
```

### Run Backend

```bash
cd backend
.\venv311\Scripts\activate
# reinstall deps if you are migrating from an older Kaggle-based setup
pip install -r requirements.txt
python main.py
```

### Run Frontend

```bash
cd frontend
npm run dev
```

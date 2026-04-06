# CONFIT Backend

AI-powered backend services for the CONFIT fashion e-commerce platform.

## Services

| Service | Endpoint | Description |
|---------|----------|-------------|
| Virtual Try-On | `POST /api/tryon` | Photorealistic garment try-on using IDM-VTON |
| Virtual Stylist | `POST /api/stylist/chat` | AI fashion styling chat assistant |
| Health Check | `GET /api/health` | System health status |

## Quick Start

### 1. Install Python Dependencies

```bash
cd backend
py -3.12 -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Recommended on Windows: use Python 3.12 for this project.  
> If `python` resolves to 3.14 and `pip`/`venv` errors appear, recreate `.venv` with `py -3.12`.

### 1b. Database migrations (Alembic)

The `alembic` console command is often **not** on your PATH after `pip install`. Use the module form instead:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Or from the **repository root**:

```powershell
npm run migrate:backend
```

Shortcuts inside `backend\`: `.\run_migrations.ps1` or `run_migrations.bat`.

### 2. Configure Environment (Optional)

```bash
# Copy the example and edit as needed
copy .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | No | Enables AI-powered stylist chat ([Get free key](https://console.groq.com/keys)) |
| `HF_TOKEN` | No | Priority queue for HuggingFace Spaces ([Get free token](https://huggingface.co/settings/tokens)) |

### 3. Start the Server

```bash
python main.py
```

The server starts at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

## API Reference

### Virtual Try-On

```http
POST /api/tryon
Content-Type: application/json

{
  "userImageBase64": "data:image/jpeg;base64,...",
  "garmentImageUrl": "https://example.com/garment.jpg",
  "garmentName": "Classic White T-Shirt"
}
```

### Virtual Stylist

```http
POST /api/stylist/chat
Content-Type: application/json

{
  "message": "I need an outfit for a wedding",
  "occasion": "formal",
  "budget": "$500"
}
```

## Architecture

```
backend/
├── main.py                  # FastAPI entry point
├── requirements.txt         # Dependencies
├── routers/                 # API route handlers
│   ├── virtual_tryon.py     # Try-on endpoints
│   └── virtual_stylist.py   # Stylist chat endpoints
├── services/                # Business logic
│   ├── tryon_service.py     # IDM-VTON integration
│   └── stylist_service.py   # Groq AI + rule-based fallback
└── utils/                   # Shared utilities
    └── image_utils.py       # Image processing helpers
```

## Adding New Backend Services

1. Create a new service in `services/`
2. Create a new router in `routers/`
3. Register the router in `main.py` with `app.include_router()`

## Try-On Runtime Modes

### CPU-only mode
- `POST /api/tryon/preview/live` is available for instant preview.
- `POST /api/tryon/render` returns `503 FINAL_RENDER_UNAVAILABLE` unless a neural backend is available.
- This is intentional: no fake "final quality" output on unsupported hardware.

### GPU mode (local self-hosted)
- Set `TRYON_LOCAL_MODEL_PATH` to local CatVTON/IDM-VTON weights path.
- With CUDA + model path available, final neural render can be enabled through `/api/tryon/render`.

### Remote backend mode (self-managed)
- Set `TRYON_REMOTE_URL` to your own neural render endpoint.
- Backend enqueues final jobs and polls via `/api/tryon/jobs/{job_id}`.

### Why HF Space quota issue is removed from runtime flow
- The production runtime flow now uses `/api/tryon/preview/live` + `/api/tryon/render` and capability gating.
- It does not require HuggingFace Spaces runtime execution or FASHN API key to function in preview mode.
- Final render is offered only when capability is truly available.

## Local Mock Remote GPU (free e2e test)

You can test final-render flow without paid services by running a local mock remote server:

1) Start mock remote server (separate terminal):

```bash
cd backend
python mock_remote_gpu_server.py
```

2) Configure backend `.env`:

```env
TRYON_REMOTE_URL=http://127.0.0.1:8011/render
TRYON_REMOTE_HEALTH_URL=http://127.0.0.1:8011/health
# Optional auth (if enabled)
# TRYON_REMOTE_API_KEY=your_key
```

3) Restart backend and verify:
- `GET /api/tryon/capabilities` -> `remoteProbe.healthy=true`
- `POST /api/tryon/render` should enqueue and complete jobs through remote path.

# CONFIT Remote GPU Backend Setup

## Supported Scenarios
1. Another GPU machine on same LAN.
2. Cloud GPU VM/container (RunPod, Vast.ai, Modal, Paperspace).
3. Temporary experimentation (Colab/Kaggle + tunnel) - non-production only.

## Required Endpoints
- `GET /health`
- `POST /render` (Bearer auth)

`POST /render` request:
```json
{
  "userImageBase64": "...",
  "garmentImageUrl": "...",
  "garmentName": "...",
  "garmentCategory": "tops"
}
```

Response:
```json
{
  "resultImage": "data:image/png;base64,...",
  "quality_score": 0.9
}
```

## Backend Env
```env
TRYON_REMOTE_URL=https://your-remote-host/render
TRYON_REMOTE_API_KEY=replace_me
TRYON_REMOTE_TIMEOUT_SEC=180
TRYON_HEALTHCHECK_TIMEOUT_SEC=5
```

## Production Notes
- Keep GPU model weights cached locally on remote node.
- Warm model at startup.
- Protect endpoints with bearer key and network ACL.
- Enable retries + timeout from CONFIT runtime (already implemented).

## Non-Production (Colab/Kaggle)
Use only for testing. Sessions are transient, quota-limited, and not reliable for production.


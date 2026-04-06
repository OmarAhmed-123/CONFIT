# CONFIT Local GPU Try-On Setup (Windows + NVIDIA)

## 1) Prerequisites
- Install latest NVIDIA driver.
- Install Python 3.10+.
- Create venv and install backend deps.

```powershell
cd E:\CONFIT\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Install CUDA-enabled PyTorch build from [pytorch.org](https://pytorch.org/get-started/locally/), then verify:

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO GPU')"
```

## 2) Model Weights Layout
Set `TRYON_LOCAL_MODELS_DIR` and place model directories:

```text
E:/CONFIT/backend/models/
  catvton/
    (weights + config files)
  idm-vton/
    (weights + config files)
```

## 3) Required Environment Variables
Use backend `.env`:

```env
TRYON_BACKEND_PRIORITY=local_catvton,local_idmvton,remote_gpu,replicate,fashn,huggingface_space,preview_only
TRYON_LOCAL_MODELS_DIR=E:/CONFIT/backend/models
TRYON_REMOTE_URL=
TRYON_REMOTE_API_KEY=
TRYON_ENABLE_PREVIEW=1
TRYON_ENABLE_FINAL=1
TRYON_REQUEST_TIMEOUT_SEC=180
TRYON_PREVIEW_TIMEOUT_SEC=20
TRYON_REMOTE_TIMEOUT_SEC=180
TRYON_HEALTHCHECK_TIMEOUT_SEC=5
TRYON_MAX_IMAGE_MB=12
```

## 4) Verification
1. Start backend:
```powershell
cd E:\CONFIT\backend
.\.venv\Scripts\Activate.ps1
python main.py
```
2. Check health:
```powershell
curl http://127.0.0.1:8000/api/health
```
3. Check diagnostics:
```powershell
curl http://127.0.0.1:8000/api/virtual-tryon/diagnostics
```
4. Run GPU verification helper:
```powershell
python E:\CONFIT\scripts\verify_tryon_gpu.py
```


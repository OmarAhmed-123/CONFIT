# Mock Infrastructure Development Guide
# ======================================
# Complete guide for developing without GPU while preparing for production.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT MODE (Current)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend (React)          Backend (FastAPI)                     │
│  ┌─────────────┐          ┌─────────────────────────────────┐   │
│  │ TryOnViewer │─────────▶│ /api/virtual-tryon/process      │   │
│  └─────────────┘          │         │                        │   │
│                           │         ▼                        │   │
│                           │  ┌─────────────────────┐        │   │
│                           │  │ Mock Inference      │        │   │
│                           │  │ Service             │        │   │
│                           │  │ (simulated delays,  │        │   │
│                           │  │  fake results)      │        │   │
│                           │  └─────────────────────┘        │   │
│                           └─────────────────────────────────┘   │
│                                                                  │
│  Environment: INFERENCE_MODE=mock                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION MODE (Future)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend (React)          Backend (FastAPI + Celery)            │
│  ┌─────────────┐          ┌─────────────────────────────────┐   │
│  │ TryOnViewer │─────────▶│ /api/virtual-tryon/process      │   │
│  └─────────────┘          │         │                        │   │
│                           │         ▼                        │   │
│                           │  ┌─────────────────────┐        │   │
│                           │  │ Celery Queue        │        │   │
│                           │  └──────────┬──────────┘        │   │
│                           │             │                    │   │
│                           │             ▼                    │   │
│                           │  ┌─────────────────────┐        │   │
│                           │  │ GPU Worker          │        │   │
│                           │  │ (IDM-VTON, SAM)     │        │   │
│                           │  └─────────────────────┘        │   │
│                           └─────────────────────────────────┘   │
│                                                                  │
│  Environment: INFERENCE_MODE=gpu                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Folder Structure

```
backend/
├── app/                          # Main application
│   ├── routers/
│   │   └── virtual_tryon.py      # API endpoints
│   ├── controllers/
│   │   └── tryon_controller.py  # Request orchestration
│   └── services/
│       └── inference/
│           ├── __init__.py       # Mode selector
│           ├── base.py           # Abstract interface
│           ├── mock_service.py   # DEVELOPMENT (active)
│           └── gpu_service.py    # PRODUCTION (inactive)
│
├── mock_services/                # Mock infrastructure
│   ├── __init__.py
│   ├── mock_inference.py         # Fake AI inference
│   ├── mock_pose_detection.py    # Fake pose detection
│   ├── mock_segmentation.py      # Fake segmentation
│   ├── mock_data_generator.py    # Generate fake results
│   └── data/
│       ├── sample_garments/      # Sample garment images
│       ├── sample_results/       # Pre-generated try-on results
│       └── mock_responses.json   # Cached mock responses
│
├── gpu_production/               # PRODUCTION (INACTIVE)
│   ├── Dockerfile.gpu            # GPU Docker image
│   ├── docker-compose.gpu.yml    # GPU deployment
│   ├── models/
│   │   ├── idm_vton.py           # Model definition
│   │   └── model_loader.py       # Model loading
│   ├── workers/
│   │   ├── celery_app.py         # Celery config
│   │   └── tryon_worker.py       # GPU worker
│   └── configs/
│       └── model_config.yaml     # Model configuration
│
├── models_placeholder/           # Placeholder weights
│   └── README.md                 # Instructions for real weights
│
├── configs/
│   ├── dev.env                   # Development config
│   └── prod.env.example          # Production config template
│
└── requirements.txt              # Core dependencies (no GPU)
```

## Environment Variables

### Development (.env)
```bash
# Inference Mode
INFERENCE_MODE=mock

# Mock Settings
MOCK_DELAY_MIN=2.0
MOCK_DELAY_MAX=5.0
MOCK_QUALITY_SCORE_MIN=0.7
MOCK_QUALITY_SCORE_MAX=0.95

# No GPU settings needed
```

### Production (prod.env)
```bash
# Inference Mode
INFERENCE_MODE=gpu

# GPU Settings
CUDA_VISIBLE_DEVICES=0
GPU_MEMORY_FRACTION=0.8

# Model Paths
MODEL_WEIGHTS_PATH=/app/weights
IDM_VTON_PATH=/app/weights/idm_vton

# Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
```

## Switching Guide

### Development → Production

1. **Set Environment Variable**
   ```bash
   export INFERENCE_MODE=gpu
   ```

2. **Start GPU Infrastructure**
   ```bash
   cd backend/gpu_production
   docker-compose -f docker-compose.gpu.yml up -d
   ```

3. **Verify GPU Connection**
   ```bash
   curl http://localhost:8000/api/virtual-tryon/health
   ```

4. **Monitor GPU Usage**
   ```bash
   nvidia-smi -l 1
   ```

### Production → Development

1. **Stop GPU Services**
   ```bash
   docker-compose -f docker-compose.gpu.yml down
   ```

2. **Set Environment Variable**
   ```bash
   export INFERENCE_MODE=mock
   ```

3. **Restart Application**
   ```bash
   uvicorn main:app --reload
   ```

## Safety Checks

The system includes automatic fallback:

1. If `INFERENCE_MODE=gpu` but GPU unavailable → Falls back to mock
2. If model weights missing → Falls back to mock
3. If CUDA error occurs → Falls back to mock with warning

## Recommended Mock Datasets

### Public Fashion Datasets

1. **DeepFashion** (CVPR 2016)
   - 800,000+ fashion images
   - Category labels, landmarks
   - URL: http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html

2. **VITON Dataset**
   - 16,253 image pairs
   - Front-view person + garment
   - URL: https://github.com/chenyuntc/simple-AE

3. **Dress Code Dataset**
   - 1,024 high-resolution images
   - Paired try-on results
   - URL: https://github.com/aimagelab/dress-code

4. **FashionAI Dataset** (Alibaba)
   - 50,000+ images
   - Attribute labels
   - URL: https://tianchi.aliyun.com/dataset

### Mock Data Generation

Use the provided `mock_data_generator.py` to create:
- Fake pose keypoints
- Fake segmentation masks
- Fake try-on results
- Realistic quality scores

# GPU Production Activation Guide
# ================================
# Step-by-step guide to enable GPU inference.

## Prerequisites Checklist

Before activating GPU inference, ensure:

- [ ] NVIDIA GPU available (8GB+ VRAM)
- [ ] CUDA 12.1+ installed
- [ ] cuDNN 8.9+ installed
- [ ] Docker with NVIDIA Container Toolkit (if using Docker)
- [ ] Model weights downloaded (see models_placeholder/README.md)
- [ ] Redis server running (for Celery)

## Activation Steps

### Step 1: Download Model Weights

```bash
cd backend

# Create weights directory
mkdir -p weights/idm_vton weights/viton_hd

# Download IDM-VTON
pip install huggingface-hub
huggingface-cli download IDM-VTON/IDM-VTON --local-dir weights/idm_vton

# Download SAM
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth -O weights/sam_vit_h.pth
```

### Step 2: Configure Environment

```bash
# Copy production config
cp configs/prod.env.example configs/prod.env

# Edit and set required values
nano configs/prod.env
```

Set these critical values:
```bash
INFERENCE_MODE=gpu
CUDA_VISIBLE_DEVICES=0
MODEL_WEIGHTS_PATH=/app/weights
```

### Step 3: Start Redis

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or using local installation
redis-server
```

### Step 4: Start Celery Worker

```bash
# Start GPU worker
cd backend
celery -A gpu_production.workers.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=gpu,cpu
```

### Step 5: Start FastAPI with GPU Config

```bash
# Load production environment
export $(cat configs/prod.env | xargs)

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 6: Verify GPU Activation

```bash
# Check health endpoint
curl http://localhost:8000/api/virtual-tryon/health

# Expected response:
# {
#   "status": "healthy",
#   "mode": "gpu",
#   "available": true,
#   "gpu": {
#     "device_name": "NVIDIA GeForce RTX 3080",
#     "memory_total_gb": 10.0
#   }
# }
```

### Step 7: Test Inference

```bash
# Run test request
curl -X POST http://localhost:8000/api/virtual-tryon/process \
    -H "Content-Type: application/json" \
    -d '{
        "userImageBase64": "...",
        "garmentId": "shirt-001",
        "garmentImageBase64": "..."
    }'
```

## Docker Deployment

### Build GPU Image

```bash
cd backend
docker build -f Dockerfile.gpu -t confit-backend:gpu .
```

### Run with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.gpu.yml up -d

# Check logs
docker-compose -f docker-compose.gpu.yml logs -f celery-worker
```

### Verify GPU Access in Container

```bash
docker exec -it confit-celery-worker nvidia-smi
```

## Monitoring

### GPU Utilization

```bash
# Watch GPU usage
watch -n 1 nvidia-smi

# Or using Python
python -c "
import torch
while True:
    print(f'GPU Memory: {torch.cuda.memory_allocated(0)/1024**3:.2f}GB / {torch.cuda.get_device_properties(0).total_memory/1024**3:.2f}GB')
    import time; time.sleep(1)
"
```

### Celery Tasks

```bash
# Start Flower monitoring
celery -A gpu_production.workers.celery_app flower --port=5555

# Open http://localhost:5555
```

## Rollback to Mock Mode

If issues occur, quickly rollback:

```bash
# Stop GPU services
docker-compose -f docker-compose.gpu.yml down

# Set mock mode
export INFERENCE_MODE=mock

# Restart application
uvicorn main:app --reload
```

## Troubleshooting

### CUDA Out of Memory

```bash
# Reduce batch size in model_config.yaml
# Or reduce concurrent workers
celery -A ... worker --concurrency=1
```

### Model Not Found

```bash
# Verify weights exist
ls -la weights/idm_vton/

# Check MODEL_WEIGHTS_PATH in .env
echo $MODEL_WEIGHTS_PATH
```

### Slow Inference

```bash
# Check GPU is actually being used
python -c "import torch; print(torch.cuda.is_available())"

# Should print: True
```

## Performance Benchmarks

Expected performance with RTX 3080:

| Model | Resolution | Time | GPU Memory |
|-------|------------|------|------------|
| IDM-VTON | 512x384 | ~8s | 6GB |
| VITON-HD | 512x384 | ~3s | 4GB |
| SAM | 1024x1024 | ~2s | 3GB |

## Security Notes

- Never commit weights to git
- Never expose GPU server to public internet
- Use API keys in production
- Enable rate limiting

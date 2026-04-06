# Virtual Try-On Implementation Guide

## Step 1: Frontend Dependencies Setup

### 1.1 Install Dependencies

Run these commands in your terminal:

```bash
# Core 3D rendering
npm install three @react-three/fiber @react-three/drei

# Type definitions for three.js
npm install -D @types/three

# MediaPipe for pose detection
npm install @mediapipe/pose @mediapipe/camera_utils @mediapipe/drawing_utils
```

### 1.2 Folder Structure

```
src/
├── components/
│   ├── 3d/
│   │   ├── GarmentViewer3D.tsx      # Main 3D viewer
│   │   ├── Scene.tsx                 # Canvas wrapper
│   │   ├── Lighting.tsx              # HDR lighting
│   │   └── index.ts
│   │
│   └── try-on/
│       ├── PoseGuideOverlay.tsx      # Pose guidance
│       ├── PhotoCapture.tsx          # Camera capture
│       └── TryOnViewer.tsx           # Result viewer
│
├── hooks/
│   ├── usePoseDetection.ts           # MediaPipe integration
│   ├── useGarment3D.ts               # 3D model loading
│   └── useTryOn.ts                   # Try-on session
│
├── services/
│   ├── tryOnApi.ts                   # Backend API
│   └── modelLoader.ts                # glTF utilities
│
└── public/
    └── draco/                        # Draco decoder
        ├── draco_decoder.js
        ├── draco_decoder.wasm
        └── draco_wasm_wrapper.js
```

### 1.3 Vite Configuration

Update `vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    include: ['three', '@react-three/fiber', '@react-three/drei'],
    esbuildOptions: {
      target: 'es2020',
    },
  },
  build: {
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          'react-three': ['@react-three/fiber', '@react-three/drei'],
        },
      },
    },
  },
});
```

---

## Step 2: GPU Infrastructure Deployment

### 2.1 Server Specifications

**Minimum Requirements:**
- GPU: NVIDIA T4 (16GB) or RTX 3080 (10GB)
- CPU: 8 cores
- RAM: 32GB
- Storage: 100GB SSD

**Recommended (Production):**
- GPU: NVIDIA A100 (40GB) or RTX 4090 (24GB)
- CPU: 16 cores
- RAM: 64GB
- Storage: 500GB NVMe SSD

### 2.2 Docker Setup

Create `backend/Dockerfile.gpu`:

```dockerfile
FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Set working directory
WORKDIR /app

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir \
    torch==2.1.0+cu121 \
    torchvision==0.16.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.3 Docker Compose

Create `docker-compose.gpu.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.gpu
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - model-cache:/root/.cache
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=0
      - REDIS_URL=redis://redis:6379/0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.gpu
    command: celery -A services.workers.celery_app worker --loglevel=info --concurrency=2
    volumes:
      - ./backend:/app
      - model-cache:/root/.cache
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=0
      - REDIS_URL=redis://redis:6379/0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - redis

volumes:
  redis-data:
  model-cache:
```

### 2.4 GPU Verification Commands

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA version
nvcc --version

# Check PyTorch GPU access
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count()}'); print(f'Device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# Run container with GPU
docker run --gpus all -it nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
```

---

## Step 3: Async Processing System

### 3.1 Install Redis (Windows)

**Option A: Use WSL2 + Docker (Recommended)**
```bash
# In WSL2
docker run -d -p 6379:6379 redis:7-alpine
```

**Option B: Use Memurai (Windows Native)**
```powershell
# Download from https://www.memurai.com/
# Or use Chocolatey
choco install memurai
```

### 3.2 Backend Dependencies

Add to `backend/requirements.txt`:

```text
celery==5.3.4
redis==5.0.1
flower==2.0.1
```

### 3.3 Celery Configuration

Create `backend/services/workers/celery_app.py`:

```python
from celery import Celery
from celery.signals import task_prerun, task_postrun
import os

app = Celery('confit_tryon')

# Configuration
app.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'services.workers.tryon_worker.*': {'queue': 'gpu'},
        'services.workers.preprocessing_worker.*': {'queue': 'cpu'},
    },
    
    # Time limits
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=2,  # Limit concurrent GPU tasks
)

@task_prerun.connect
def init_gpu_context(*args, **kwargs):
    """Initialize GPU before task."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.init()
    except Exception:
        pass

@task_postrun.connect
def cleanup_gpu_context(*args, **kwargs):
    """Cleanup GPU after task."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass
```

### 3.4 Try-On Worker

Create `backend/services/workers/tryon_worker.py`:

```python
import logging
import asyncio
from services.workers.celery_app import app
from models.tryon_models import TryOnRequest
from services.tryon.orchestrator import TryOnOrchestrator

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_tryon(self, request_data: dict):
    """
    Async task for processing virtual try-on.
    
    Retries:
    - GPU OOM: Retry with smaller image
    - Model error: Retry with fallback model
    - Timeout: Fail immediately
    """
    try:
        orchestrator = TryOnOrchestrator()
        request = TryOnRequest(**request_data)
        
        # Run async orchestrator in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(orchestrator.process(request))
        finally:
            loop.close()
        
        return result.dict()
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Try-on task failed: {error_msg}", exc_info=True)
        
        # Check for recoverable errors
        if 'out of memory' in error_msg.lower():
            # Retry with reduced resolution
            request_data['options'] = request_data.get('options', {})
            request_data['options']['resolution'] = 'medium'
            raise self.retry(exc=e, countdown=10)
        
        raise


@app.task
def health_check():
    """Health check task."""
    try:
        import torch
        return {
            'status': 'healthy',
            'cuda_available': torch.cuda.is_available(),
            'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}
```

### 3.5 FastAPI Integration

Update `backend/main.py` to include Celery:

```python
from fastapi import FastAPI, BackgroundTasks
from services.workers.tryon_worker import process_tryon, health_check

# ... existing code ...

@app.post("/api/virtual-tryon/async")
async def tryon_async(request: TryOnRequest, background_tasks: BackgroundTasks):
    """Submit async try-on job."""
    task = process_tryon.delay(request.dict())
    return {
        "job_id": task.id,
        "status": "queued",
        "estimated_time_seconds": 8
    }


@app.get("/api/virtual-tryon/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status."""
    from celery.result import AsyncResult
    from services.workers.celery_app import app as celery_app
    
    task = AsyncResult(job_id, app=celery_app)
    
    return {
        "job_id": job_id,
        "status": task.state,
        "result": task.result if task.ready() else None,
        "error": str(task.info) if task.failed() else None,
    }
```

---

## Step 4: Model Integration

### 4.1 Folder Structure

```
backend/
├── models/
│   ├── __init__.py
│   ├── idm_vton.py
│   ├── viton_hd.py
│   └── cloth_warping.py
│
├── weights/
│   ├── idm_vton/
│   │   ├── encoder.pth
│   │   ├── decoder.pth
│   │   └── config.json
│   │
│   └── viton_hd/
│       └── model.pth
│
├── services/
│   └── tryon/
│       └── neural_tryon.py
│
└── configs/
    └── model_config.yaml
```

### 4.2 Model Configuration

Create `backend/configs/model_config.yaml`:

```yaml
tryon:
  default_model: idm_vton
  
  models:
    idm_vton:
      path: weights/idm_vton
      device: cuda
      precision: fp16
      image_size: [512, 384]
      inference_time_ms: 8000
      
    viton_hd:
      path: weights/viton_hd
      device: cuda
      precision: fp16
      image_size: [512, 384]
      inference_time_ms: 3000
      
    huggingface:
      model_id: "IDM-VTON/IDM-VTON"
      api_token: ${HUGGINGFACE_TOKEN}
      timeout_seconds: 30

pose_detection:
  model: mediapipe
  complexity: 1  # 0, 1, or 2
  min_confidence: 0.5

segmentation:
  model: sam
  variant: vit_h
  checkpoint: weights/sam_vit_h.pth
```

### 4.3 Model Loading Strategy

Create `backend/models/model_loader.py`:

```python
import torch
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loads and manages ML models with caching and error handling.
    """
    
    _instance = None
    _models: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config = self._load_config()
        self.device = self._get_device()
    
    def _load_config(self) -> Dict:
        """Load model configuration."""
        config_path = Path(__file__).parent.parent / 'configs' / 'model_config.yaml'
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {'tryon': {'default_model': 'idm_vton'}}
    
    def _get_device(self) -> torch.device:
        """Get compute device."""
        if torch.cuda.is_available():
            return torch.device('cuda')
        return torch.device('cpu')
    
    def load_tryon_model(self, model_name: Optional[str] = None):
        """
        Load try-on model.
        
        Args:
            model_name: Model to load (idm_vton, viton_hd, or huggingface)
            
        Returns:
            Loaded model instance
        """
        model_name = model_name or self.config.get('tryon', {}).get('default_model', 'idm_vton')
        
        # Check cache
        if model_name in self._models:
            logger.info(f"Using cached {model_name} model")
            return self._models[model_name]
        
        # Load model
        if model_name == 'idm_vton':
            model = self._load_idm_vton()
        elif model_name == 'viton_hd':
            model = self._load_viton_hd()
        elif model_name == 'huggingface':
            model = self._load_huggingface()
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        self._models[model_name] = model
        return model
    
    def _load_idm_vton(self):
        """Load IDM-VTON model."""
        try:
            from models.idm_vton import IDMVTON
            
            config = self.config.get('tryon', {}).get('models', {}).get('idm_vton', {})
            weights_path = Path(config.get('path', 'weights/idm_vton'))
            
            model = IDMVTON()
            
            # Load weights
            if weights_path.exists():
                checkpoint = torch.load(
                    weights_path / 'model.pth',
                    map_location=self.device
                )
                model.load_state_dict(checkpoint)
                logger.info(f"IDM-VTON loaded from {weights_path}")
            else:
                logger.warning(f"Weights not found at {weights_path}, using random weights")
            
            model.to(self.device)
            model.eval()
            
            # Use FP16 if configured
            if config.get('precision') == 'fp16' and self.device.type == 'cuda':
                model = model.half()
            
            return model
            
        except ImportError as e:
            logger.error(f"Failed to import IDM-VTON: {e}")
            return None
    
    def _load_viton_hd(self):
        """Load VITON-HD model."""
        try:
            from models.viton_hd import VITONHD
            
            config = self.config.get('tryon', {}).get('models', {}).get('viton_hd', {})
            weights_path = Path(config.get('path', 'weights/viton_hd'))
            
            model = VITONHD()
            
            if weights_path.exists():
                checkpoint = torch.load(
                    weights_path / 'model.pth',
                    map_location=self.device
                )
                model.load_state_dict(checkpoint)
                logger.info(f"VITON-HD loaded from {weights_path}")
            
            model.to(self.device)
            model.eval()
            
            return model
            
        except ImportError as e:
            logger.error(f"Failed to import VITON-HD: {e}")
            return None
    
    def _load_huggingface(self):
        """Load model via HuggingFace API."""
        from services.tryon.huggingface_client import HuggingFaceTryOn
        
        config = self.config.get('tryon', {}).get('models', {}).get('huggingface', {})
        
        return HuggingFaceTryOn(
            model_id=config.get('model_id', 'IDM-VTON/IDM-VTON'),
            api_token=config.get('api_token'),
            timeout=config.get('timeout_seconds', 30)
        )
    
    def clear_cache(self):
        """Clear model cache and free GPU memory."""
        self._models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")


# Singleton instance
model_loader = ModelLoader()
```

### 4.4 HuggingFace Client (Fallback)

Create `backend/services/tryon/huggingface_client.py`:

```python
import requests
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HuggingFaceTryOn:
    """
    HuggingFace API client for virtual try-on.
    Used as fallback when local model is unavailable.
    """
    
    def __init__(
        self,
        model_id: str = "IDM-VTON/IDM-VTON",
        api_token: Optional[str] = None,
        timeout: int = 30
    ):
        self.model_id = model_id
        self.api_token = api_token or os.getenv('HUGGINGFACE_TOKEN')
        self.timeout = timeout
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    async def inference(
        self,
        person_image: str,  # base64
        garment_image: str,  # base64 or URL
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run inference via HuggingFace API.
        
        Args:
            person_image: Base64-encoded person image
            garment_image: Base64-encoded garment image
            
        Returns:
            Dict with result image and metadata
        """
        if not self.api_token:
            raise ValueError("HuggingFace API token required")
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "inputs": {
                "person_image": person_image,
                "garment_image": garment_image,
            },
            "parameters": kwargs
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 503:
                # Model loading
                return {
                    'success': False,
                    'error': 'Model is loading, please retry in 30 seconds',
                    'estimated_time': 30
                }
            
            if response.status_code == 429:
                # Rate limited
                return {
                    'success': False,
                    'error': 'Rate limited, please retry later',
                    'retry_after': int(response.headers.get('Retry-After', 60))
                }
            
            if not response.ok:
                logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }
            
            result = response.json()
            
            return {
                'success': True,
                'result_image': result.get('output'),
                'processing_time_ms': result.get('processing_time', 0)
            }
            
        except requests.Timeout:
            return {
                'success': False,
                'error': 'Request timed out'
            }
        except Exception as e:
            logger.error(f"HuggingFace inference failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
```

### 4.5 API Endpoint

Create `backend/routers/tryon_inference.py`:

```python
"""
CONFIT Backend — Try-On Inference Router
========================================
Production-ready inference endpoint with error handling.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from models.tryon_models import TryOnRequest, TryOnResponse
from services.workers.tryon_worker import process_tryon

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/virtual-tryon", tags=["Virtual Try-On"])


@router.post("/process", response_model=TryOnResponse)
async def process_sync(request: TryOnRequest):
    """
    Synchronous try-on processing (for small images).
    
    Timeout: 30 seconds
    Use async endpoint for production workloads.
    """
    try:
        from services.tryon.orchestrator import TryOnOrchestrator
        import asyncio
        
        orchestrator = TryOnOrchestrator()
        
        # Run with timeout
        result = await asyncio.wait_for(
            orchestrator.process(request),
            timeout=30.0
        )
        
        return result
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Processing timed out. Use /process-async for large images."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Try-on failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Processing failed. Please try again."
        )


@router.post("/process-async")
async def process_async(request: TryOnRequest):
    """
    Asynchronous try-on processing.
    
    Returns job ID for status polling.
    """
    task = process_tryon.delay(request.dict())
    
    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "status_url": f"/api/virtual-tryon/status/{task.id}",
        "estimated_time_seconds": 8
    }


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get job status."""
    from celery.result import AsyncResult
    from services.workers.celery_app import app as celery_app
    
    task = AsyncResult(job_id, app=celery_app)
    
    response = {
        "job_id": job_id,
        "status": task.state,
    }
    
    if task.ready():
        if task.successful():
            response["result"] = task.result
        else:
            response["error"] = str(task.info)
    
    return response


@router.get("/health")
async def health():
    """Service health check."""
    from services.workers.tryon_worker import health_check
    
    # Run health check
    result = health_check.delay()
    
    try:
        result.wait(timeout=5)
        return result.result
    except Exception:
        return {
            "status": "degraded",
            "message": "Worker not responding"
        }
```

---

## Step 5: 3D Garment Assets Pipeline

### 5.1 Export Pipeline from 3D Tools

**Blender Export Workflow:**

1. **Prepare Model:**
   - Apply modifiers (especially Subdivision Surface)
   - Triangulate mesh (optional, but recommended)
   - Apply transforms (Ctrl+A → Apply All)
   - Center model at origin

2. **Export glTF:**
   ```
   File → Export → glTF 2.0 (.glb)
   
   Settings:
   - Format: glTF Binary (.glb)
   - Include: ✓ Apply Modifiers
   - Transform: +Y Up
   - Mesh: ✓ Apply Modifiers, ☐ Tangents
   - Compression: ✓ Draco (see below)
   ```

3. **Draco Compression:**
   - Install glTF-Blender-IO-Draco addon
   - Or use command-line tool:
   ```bash
   # Install
   npm install -g gltf-pipeline
   
   # Compress
   gltf-pipeline -i input.glb -o output.glb --draco.compressMeshes --draco.compressionLevel 10
   ```

### 5.2 Draco Decoder Setup

Download Draco decoder files:

```bash
# Create public/draco directory
mkdir -p public/draco

# Download from Three.js examples
# Copy these files from node_modules/three/examples/jsm/libs/draco/:
# - draco_decoder.js
# - draco_decoder.wasm
# - draco_wasm_wrapper.js
```

Or download from: https://github.com/google/draco/tree/master/javascript

### 5.3 Model Loading Service

Create `src/services/modelLoader.ts`:

```typescript
/**
 * Model Loader Service
 * Handles glTF loading with Draco compression
 */

import * as THREE from 'three';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

// Configure Draco loader
const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('/draco/');
dracoLoader.setDecoderConfig({ type: 'js' });

// Configure glTF loader
const gltfLoader = new GLTFLoader();
gltfLoader.setDRACOLoader(dracoLoader);

export interface LoadedModel {
  scene: THREE.Group;
  animations: THREE.AnimationClip[];
  cameras: THREE.Camera[];
  asset: { [key: string]: any };
}

export interface ModelLoadOptions {
  onProgress?: (progress: number) => void;
  castShadow?: boolean;
  receiveShadow?: boolean;
  center?: boolean;
  scale?: number;
}

/**
 * Load glTF model with error handling
 */
export async function loadGLTFModel(
  url: string,
  options: ModelLoadOptions = {}
): Promise<LoadedModel> {
  return new Promise((resolve, reject) => {
    gltfLoader.load(
      url,
      (gltf) => {
        const { scene, animations, cameras, asset } = gltf;
        
        // Configure scene
        if (options.castShadow !== false) {
          scene.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.castShadow = true;
            }
          });
        }
        
        if (options.receiveShadow !== false) {
          scene.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.receiveShadow = true;
            }
          });
        }
        
        // Center model
        if (options.center !== false) {
          const box = new THREE.Box3().setFromObject(scene);
          const center = box.getCenter(new THREE.Vector3());
          scene.position.sub(center);
        }
        
        // Auto-scale
        if (options.scale === 'auto') {
          const box = new THREE.Box3().setFromObject(scene);
          const size = box.getSize(new THREE.Vector3());
          const maxDim = Math.max(size.x, size.y, size.z);
          const scale = 1.5 / maxDim;
          scene.scale.setScalar(scale);
        } else if (typeof options.scale === 'number') {
          scene.scale.setScalar(options.scale);
        }
        
        resolve({ scene, animations, cameras, asset });
      },
      (progress) => {
        if (options.onProgress && progress.total > 0) {
          const percent = (progress.loaded / progress.total) * 100;
          options.onProgress(percent);
        }
      },
      (error) => {
        reject(new Error(`Failed to load model: ${error.message}`));
      }
    );
  });
}

/**
 * Preload models for faster switching
 */
const preloadCache = new Map<string, Promise<LoadedModel>>();

export function preloadModel(url: string): Promise<LoadedModel> {
  if (!preloadCache.has(url)) {
    preloadCache.set(url, loadGLTFModel(url));
  }
  return preloadCache.get(url)!;
}

/**
 * Clear preload cache
 */
export function clearModelCache(): void {
  preloadCache.clear();
  dracoLoader.dispose();
}

/**
 * Get model info without full loading
 */
export async function getModelInfo(url: string): Promise<{
  hasAnimations: boolean;
  vertexCount: number;
  meshCount: number;
}> {
  const { scene, animations } = await loadGLTFModel(url);
  
  let vertexCount = 0;
  let meshCount = 0;
  
  scene.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      meshCount++;
      const geometry = child.geometry;
      if (geometry.attributes.position) {
        vertexCount += geometry.attributes.position.count;
      }
    }
  });
  
  return {
    hasAnimations: animations.length > 0,
    vertexCount,
    meshCount,
  };
}
```

### 5.4 Asset Optimization Script

Create `scripts/optimize-models.js`:

```javascript
/**
 * Model Optimization Script
 * Compresses glTF files with Draco
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const MODELS_DIR = path.join(__dirname, '../public/models');
const OUTPUT_DIR = path.join(__dirname, '../public/models/optimized');

// Compression levels
const COMPRESSION_LEVEL = 10; // Max compression

function optimizeModels() {
  console.log('Optimizing 3D models...\n');
  
  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
  
  // Find all glTF files
  const files = fs.readdirSync(MODELS_DIR)
    .filter(f => f.endsWith('.glb') || f.endsWith('.gltf'));
  
  let totalSaved = 0;
  
  for (const file of files) {
    const inputPath = path.join(MODELS_DIR, file);
    const outputPath = path.join(OUTPUT_DIR, file);
    
    const inputSize = fs.statSync(inputPath).size;
    
    console.log(`Processing: ${file}`);
    console.log(`  Input: ${(inputSize / 1024).toFixed(1)} KB`);
    
    try {
      // Run gltf-pipeline
      execSync(
        `gltf-pipeline -i "${inputPath}" -o "${outputPath}" ` +
        `--draco.compressMeshes ` +
        `--draco.compressionLevel ${COMPRESSION_LEVEL}`,
        { stdio: 'inherit' }
      );
      
      const outputSize = fs.statSync(outputPath).size;
      const saved = inputSize - outputSize;
      const percent = ((saved / inputSize) * 100).toFixed(1);
      
      console.log(`  Output: ${(outputSize / 1024).toFixed(1)} KB`);
      console.log(`  Saved: ${percent}%\n`);
      
      totalSaved += saved;
    } catch (error) {
      console.error(`  Error: ${error.message}\n`);
    }
  }
  
  console.log(`Total saved: ${(totalSaved / 1024).toFixed(1)} KB`);
}

optimizeModels();
```

### 5.5 Asset Manifest

Create `public/models/manifest.json`:

```json
{
  "version": "1.0",
  "models": {
    "shirt-001": {
      "name": "Classic Cotton Shirt",
      "category": "tops",
      "files": {
        "lod0": "/models/optimized/shirt-001-lod0.glb",
        "lod1": "/models/optimized/shirt-001-lod1.glb",
        "lod2": "/models/optimized/shirt-001-lod2.glb",
        "preview": "/models/previews/shirt-001.jpg"
      },
      "vertexCounts": {
        "lod0": 50000,
        "lod1": 25000,
        "lod2": 10000
      },
      "colors": [
        { "name": "White", "hex": "#FFFFFF" },
        { "name": "Black", "hex": "#000000" },
        { "name": "Navy", "hex": "#1B2838" }
      ],
      "boundingBox": {
        "min": [-0.5, -0.8, -0.2],
        "max": [0.5, 0.8, 0.2]
      }
    },
    "pants-001": {
      "name": "Slim Fit Chinos",
      "category": "pants",
      "files": {
        "lod0": "/models/optimized/pants-001-lod0.glb",
        "lod1": "/models/optimized/pants-001-lod1.glb",
        "lod2": "/models/optimized/pants-001-lod2.glb",
        "preview": "/models/previews/pants-001.jpg"
      },
      "vertexCounts": {
        "lod0": 40000,
        "lod1": 20000,
        "lod2": 8000
      },
      "colors": [
        { "name": "Khaki", "hex": "#C3B091" },
        { "name": "Black", "hex": "#000000" }
      ]
    }
  }
}
```

---

## Common Mistakes & Solutions

### 1. Three.js Memory Leaks
**Problem:** Models not disposed, causing memory buildup.
**Solution:**
```typescript
// Always dispose on unmount
useEffect(() => {
  return () => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose();
        if (child.material instanceof THREE.Material) {
          child.material.dispose();
        }
      }
    });
  };
}, []);
```

### 2. GPU OOM Errors
**Problem:** Multiple models loaded simultaneously exhaust GPU memory.
**Solution:**
```python
# Use context manager for GPU tasks
with GPUManager().inference_context() as device:
    result = model.inference(input_data)
# Memory automatically cleared
```

### 3. Celery Task Deadlocks
**Problem:** Tasks stuck in "PENDING" state.
**Solution:**
```python
# Always set result_expires
app.conf.result_expires = 3600  # 1 hour

# Use task acknowledgment
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
```

### 4. Draco Loading Failures
**Problem:** "DRACO decoder not found" errors.
**Solution:**
```typescript
// Ensure decoder path is correct
dracoLoader.setDecoderPath('/draco/');  // Must end with /

// Or use CDN
dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
```

### 5. CORS Issues with Models
**Problem:** Models fail to load from different origin.
**Solution:**
```python
# FastAPI CORS configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

---

## Quick Start Commands

```bash
# 1. Install frontend dependencies
npm install three @react-three/fiber @react-three/drei @types/three
npm install @mediapipe/pose @mediapipe/camera_utils @mediapipe/drawing_utils

# 2. Install backend dependencies
cd backend
pip install celery redis flower torch torchvision

# 3. Start Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# 4. Start Celery worker
celery -A services.workers.celery_app worker --loglevel=info

# 5. Start Flower (monitoring)
celery -A services.workers.celery_app flower --port=5555

# 6. Start FastAPI
uvicorn main:app --reload

# 7. Start frontend
npm run dev
```

---

## Verification Checklist

- [ ] `npm list three @react-three/fiber @react-three/drei` shows installed
- [ ] `nvidia-smi` shows GPU info
- [ ] `python -c "import torch; print(torch.cuda.is_available())"` returns True
- [ ] `redis-cli ping` returns PONG
- [ ] Celery worker shows "ready" status
- [ ] Flower dashboard accessible at http://localhost:5555
- [ ] 3D model loads in browser without errors
- [ ] Try-on API returns result within 10 seconds

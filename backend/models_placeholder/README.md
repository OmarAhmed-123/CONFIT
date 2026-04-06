# Model Weights Placeholder
# ========================
# This directory is a placeholder for model weights.

## Required Weights for GPU Inference

When you're ready to enable GPU inference, download the following:

### IDM-VTON (Primary Try-On Model)
```bash
# Create directory
mkdir -p weights/idm_vton

# Download from HuggingFace
# Option 1: Use huggingface-cli
pip install huggingface-hub
huggingface-cli download IDM-VTON/IDM-VTON --local-dir weights/idm_vton

# Option 2: Manual download
# Visit: https://huggingface.co/IDM-VTON/IDM-VTON
# Download all files to weights/idm_vton/
```

### VITON-HD (Fast Fallback)
```bash
mkdir -p weights/viton_hd
# Download from: https://github.com/shadow2479/VITON-HD
```

### SAM (Segment Anything Model)
```bash
# Download SAM ViT-H checkpoint
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth -O weights/sam_vit_h.pth
```

### MediaPipe Pose (Built-in)
```bash
# MediaPipe downloads models automatically on first use
# No manual download required
```

## Directory Structure After Setup

```
weights/
├── idm_vton/
│   ├── encoder.pth          # ~500MB
│   ├── decoder.pth          # ~300MB
│   └── config.json
│
├── viton_hd/
│   └── model.pth            # ~200MB
│
└── sam_vit_h.pth            # ~2.5GB

Total: ~3.5GB
```

## Verification

After downloading, verify with:
```bash
python -c "
from pathlib import Path
weights = Path('weights')
print('IDM-VTON:', (weights / 'idm_vton').exists())
print('VITON-HD:', (weights / 'viton_hd').exists())
print('SAM:', (weights / 'sam_vit_h.pth').exists())
"
```

## GPU Requirements

- NVIDIA GPU with 8GB+ VRAM (16GB+ recommended)
- CUDA 12.1+
- cuDNN 8.9+

## DO NOT

- DO NOT commit weights to git (they are large)
- DO NOT download weights if you don't have a GPU
- DO NOT set INFERENCE_MODE=gpu without weights

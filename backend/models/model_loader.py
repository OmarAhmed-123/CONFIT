"""
CONFIT Backend — Model Loader
=============================
Centralized model loading with caching and GPU management.

Supports:
- Local pretrained weights
- HuggingFace API fallback
- Model caching
- GPU memory optimization
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache
import yaml

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Singleton model loader with caching and error handling.
    
    Usage:
        loader = ModelLoader()
        model = loader.load_tryon_model('idm_vton')
    """
    
    _instance = None
    _models: Dict[str, Any] = {}
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._config = self._load_config()
        self._device = self._get_device()
        self._initialized = True
        
        logger.info(f"ModelLoader initialized on device: {self._device}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from YAML."""
        config_path = Path(__file__).parent.parent / 'configs' / 'model_config.yaml'
        
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        
        # Default config
        return {
            'tryon': {
                'default_model': 'idm_vton',
                'models': {
                    'idm_vton': {
                        'path': 'weights/idm_vton',
                        'device': 'cuda',
                        'precision': 'fp16',
                    },
                    'viton_hd': {
                        'path': 'weights/viton_hd',
                        'device': 'cuda',
                        'precision': 'fp16',
                    },
                    'huggingface': {
                        'model_id': 'IDM-VTON/IDM-VTON',
                        'api_token': os.getenv('HUGGINGFACE_TOKEN'),
                        'timeout_seconds': 30,
                    }
                }
            }
        }
    
    def _get_device(self):
        """Get compute device."""
        try:
            import torch
            if torch.cuda.is_available():
                return torch.device('cuda')
        except ImportError:
            pass
        return 'cpu'
    
    @property
    def device(self):
        return self._device
    
    def load_tryon_model(self, model_name: Optional[str] = None):
        """
        Load try-on model by name.
        
        Args:
            model_name: Model to load (idm_vton, viton_hd, huggingface)
            
        Returns:
            Loaded model instance
        """
        model_name = model_name or self._config.get('tryon', {}).get('default_model', 'idm_vton')
        
        # Check cache
        if model_name in self._models:
            logger.debug(f"Using cached {model_name}")
            return self._models[model_name]
        
        # Load based on type
        if model_name == 'huggingface':
            model = self._load_huggingface()
        elif model_name == 'idm_vton':
            model = self._load_idm_vton()
        elif model_name == 'viton_hd':
            model = self._load_viton_hd()
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        if model is not None:
            self._models[model_name] = model
            
        return model
    
    def _load_idm_vton(self):
        """Load IDM-VTON model."""
        try:
            import torch
            
            config = self._config.get('tryon', {}).get('models', {}).get('idm_vton', {})
            weights_path = Path(config.get('path', 'weights/idm_vton'))
            
            # Try to import model definition
            try:
                from models.idm_vton import IDMVTON
                model = IDMVTON()
            except ImportError:
                logger.warning("IDM-VTON model definition not found, using placeholder")
                return self._create_placeholder_model('idm_vton')
            
            # Load weights
            if weights_path.exists():
                checkpoint_files = list(weights_path.glob('*.pth')) + list(weights_path.glob('*.pt'))
                
                if checkpoint_files:
                    checkpoint_path = checkpoint_files[0]
                    checkpoint = torch.load(
                        checkpoint_path,
                        map_location=self._device
                    )
                    
                    if 'model_state_dict' in checkpoint:
                        model.load_state_dict(checkpoint['model_state_dict'])
                    elif 'state_dict' in checkpoint:
                        model.load_state_dict(checkpoint['state_dict'])
                    else:
                        model.load_state_dict(checkpoint)
                    
                    logger.info(f"IDM-VTON loaded from {checkpoint_path}")
                else:
                    logger.warning(f"No checkpoint found in {weights_path}")
            else:
                logger.warning(f"Weights path not found: {weights_path}")
            
            # Move to device
            if self._device != 'cpu':
                model = model.to(self._device)
            
            # Set to eval mode
            model.eval()
            
            # Use FP16 if configured
            if config.get('precision') == 'fp16' and self._device != 'cpu':
                model = model.half()
                logger.info("Model converted to FP16")
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load IDM-VTON: {e}", exc_info=True)
            return None
    
    def _load_viton_hd(self):
        """Load VITON-HD model."""
        try:
            import torch
            
            config = self._config.get('tryon', {}).get('models', {}).get('viton_hd', {})
            weights_path = Path(config.get('path', 'weights/viton_hd'))
            
            try:
                from models.viton_hd import VITONHD
                model = VITONHD()
            except ImportError:
                logger.warning("VITON-HD model definition not found")
                return self._create_placeholder_model('viton_hd')
            
            if weights_path.exists():
                checkpoint_files = list(weights_path.glob('*.pth')) + list(weights_path.glob('*.pt'))
                
                if checkpoint_files:
                    checkpoint = torch.load(
                        checkpoint_files[0],
                        map_location=self._device
                    )
                    model.load_state_dict(checkpoint)
                    logger.info(f"VITON-HD loaded from {checkpoint_files[0]}")
            
            if self._device != 'cpu':
                model = model.to(self._device)
            
            model.eval()
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load VITON-HD: {e}")
            return None
    
    def _load_huggingface(self):
        """Load HuggingFace API client."""
        try:
            from services.tryon.huggingface_client import HuggingFaceTryOn
            
            config = self._config.get('tryon', {}).get('models', {}).get('huggingface', {})
            
            client = HuggingFaceTryOn(
                model_id=config.get('model_id', 'IDM-VTON/IDM-VTON'),
                api_token=config.get('api_token') or os.getenv('HUGGINGFACE_TOKEN'),
                timeout=config.get('timeout_seconds', 30)
            )
            
            logger.info(f"HuggingFace client initialized for {config.get('model_id')}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace client: {e}")
            return None
    
    def _create_placeholder_model(self, name: str):
        """Create placeholder model for testing."""
        import torch
        import torch.nn as nn
        
        class PlaceholderModel(nn.Module):
            def __init__(self, name):
                super().__init__()
                self.name = name
                self.conv = nn.Conv2d(3, 3, 1)
            
            def forward(self, x):
                return self.conv(x)
        
        model = PlaceholderModel(name)
        if self._device != 'cpu':
            model = model.to(self._device)
        
        logger.warning(f"Using placeholder model for {name}")
        return model
    
    def load_sam(self):
        """Load Segment Anything Model."""
        try:
            import torch
            from segment_anything import sam_model_registry, SamPredictor
            
            config = self._config.get('segmentation', {})
            variant = config.get('variant', 'vit_h')
            checkpoint = config.get('checkpoint', 'weights/sam_vit_h.pth')
            
            if Path(checkpoint).exists():
                sam = sam_model_registry[variant](checkpoint=checkpoint)
                
                if self._device != 'cpu':
                    sam = sam.to(self._device)
                
                predictor = SamPredictor(sam)
                logger.info(f"SAM loaded: {variant}")
                return predictor
            else:
                logger.warning(f"SAM checkpoint not found: {checkpoint}")
                return None
                
        except ImportError:
            logger.warning("segment_anything not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to load SAM: {e}")
            return None
    
    def load_mediapipe_pose(self):
        """Load MediaPipe Pose model."""
        try:
            import mediapipe as mp
            
            pose = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5
            )
            
            logger.info("MediaPipe Pose loaded")
            return pose
            
        except ImportError:
            logger.warning("mediapipe not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to load MediaPipe: {e}")
            return None
    
    def clear_cache(self):
        """Clear model cache and free GPU memory."""
        self._models.clear()
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                logger.info("GPU cache cleared")
        except ImportError:
            pass
    
    def get_loaded_models(self) -> list:
        """Get list of loaded models."""
        return list(self._models.keys())
    
    def is_model_loaded(self, model_name: str) -> bool:
        """Check if model is loaded."""
        return model_name in self._models


# Singleton instance
model_loader = ModelLoader()


def get_model_loader() -> ModelLoader:
    """Get the singleton model loader instance."""
    return model_loader

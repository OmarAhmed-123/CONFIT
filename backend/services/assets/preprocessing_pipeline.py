"""
CONFIT Backend — Garment Preprocessing Pipeline
===============================================
Preprocesses garment images for faster try-on inference.

Generates:
- Multiple resolution variants
- Pre-computed segmentation masks
- Thumbnails
- Color analysis
"""

import io
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    """Result of garment preprocessing."""
    garment_id: str
    variants: Dict[str, bytes]
    thumbnails: Dict[str, bytes]
    metadata: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


class GarmentPreprocessor:
    """
    Preprocesses garment images for virtual try-on.
    
    Usage:
        preprocessor = GarmentPreprocessor()
        result = await preprocessor.preprocess_garment(garment_id, image_bytes)
    """
    
    # Resolution variants
    RESOLUTION_VARIANTS = {
        'original': None,      # Original size
        'high': 1024,          # High quality
        'medium': 512,         # Standard
        'low': 256,            # Thumbnail
    }
    
    # Thumbnail sizes
    THUMBNAIL_SIZES = {
        'large': (400, 400),
        'medium': (200, 200),
        'small': (100, 100),
    }
    
    def __init__(self, output_dir: str = 'preprocessed'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def preprocess_garment(
        self,
        garment_id: str,
        image_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Preprocess garment image.
        
        Args:
            garment_id: Unique garment identifier
            image_bytes: Raw image bytes
            
        Returns:
            Dict with variants and metadata
        """
        logger.info(f"Preprocessing garment: {garment_id}")
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
            
            # Generate variants
            variants = await self._generate_variants(image)
            
            # Generate thumbnails
            thumbnails = await self._generate_thumbnails(image)
            
            # Analyze garment
            metadata = await self._analyze_garment(image)
            
            # Save to disk
            garment_dir = self.output_dir / garment_id
            garment_dir.mkdir(exist_ok=True)
            
            for name, img_bytes in variants.items():
                path = garment_dir / f"{name}.png"
                path.write_bytes(img_bytes)
            
            for name, thumb_bytes in thumbnails.items():
                path = garment_dir / f"thumb_{name}.jpg"
                path.write_bytes(thumb_bytes)
            
            # Save metadata
            import json
            metadata_path = garment_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Preprocessing complete: {garment_id}")
            
            return {
                'garment_id': garment_id,
                'variants': list(variants.keys()),
                'thumbnails': list(thumbnails.keys()),
                'metadata': metadata,
                'success': True,
            }
            
        except Exception as e:
            logger.error(f"Preprocessing failed for {garment_id}: {e}")
            return {
                'garment_id': garment_id,
                'success': False,
                'error': str(e),
            }
    
    async def _generate_variants(self, image: Image.Image) -> Dict[str, bytes]:
        """Generate resolution variants."""
        variants = {}
        
        for name, max_size in self.RESOLUTION_VARIANTS.items():
            if max_size is None:
                # Original size
                variant = image.copy()
            else:
                # Resize maintaining aspect ratio
                variant = self._resize_image(image, max_size)
            
            # Convert to bytes
            buffer = io.BytesIO()
            variant.save(buffer, format='PNG', optimize=True)
            variants[name] = buffer.getvalue()
        
        return variants
    
    async def _generate_thumbnails(self, image: Image.Image) -> Dict[str, bytes]:
        """Generate thumbnails."""
        thumbnails = {}
        
        for name, size in self.THUMBNAIL_SIZES.items():
            thumb = image.copy()
            thumb.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Create white background for RGBA
            if thumb.mode == 'RGBA':
                background = Image.new('RGB', thumb.size, (255, 255, 255))
                background.paste(thumb, mask=thumb.split()[3])
                thumb = background
            
            buffer = io.BytesIO()
            thumb.save(buffer, format='JPEG', quality=85, optimize=True)
            thumbnails[name] = buffer.getvalue()
        
        return thumbnails
    
    async def _analyze_garment(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze garment properties."""
        # Convert to RGB for analysis
        rgb_image = image.convert('RGB')
        img_array = np.array(rgb_image)
        
        # Dominant colors
        colors = self._extract_dominant_colors(img_array)
        
        # Bounding box (for transparent images)
        bbox = image.getbbox()
        
        # Aspect ratio
        width, height = image.size
        aspect_ratio = width / height
        
        # Brightness
        brightness = np.mean(img_array)
        
        # Contrast
        contrast = np.std(img_array)
        
        return {
            'dimensions': {
                'width': width,
                'height': height,
                'aspect_ratio': round(aspect_ratio, 2),
            },
            'bounding_box': {
                'left': bbox[0] if bbox else 0,
                'top': bbox[1] if bbox else 0,
                'right': bbox[2] if bbox else width,
                'bottom': bbox[3] if bbox else height,
            } if bbox else None,
            'colors': {
                'dominant': colors[:3],
                'palette': colors[:6],
            },
            'quality': {
                'brightness': round(float(brightness), 1),
                'contrast': round(float(contrast), 1),
            },
        }
    
    def _resize_image(self, image: Image.Image, max_size: int) -> Image.Image:
        """Resize image maintaining aspect ratio."""
        width, height = image.size
        
        if max(width, height) <= max_size:
            return image.copy()
        
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _extract_dominant_colors(self, img_array: np.ndarray, n_colors: int = 6) -> List[Dict]:
        """Extract dominant colors using k-means clustering."""
        from sklearn.cluster import KMeans
        
        # Reshape to list of pixels
        pixels = img_array.reshape(-1, 3)
        
        # Sample pixels for performance
        if len(pixels) > 10000:
            indices = np.random.choice(len(pixels), 10000, replace=False)
            pixels = pixels[indices]
        
        # K-means clustering
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get colors sorted by frequency
        colors = []
        for i, color in enumerate(kmeans.cluster_centers_):
            colors.append({
                'rgb': [int(c) for c in color],
                'hex': '#{:02x}{:02x}{:02x}'.format(*[int(c) for c in color]),
                'proportion': float(np.sum(kmeans.labels_ == i) / len(kmeans.labels_)),
            })
        
        # Sort by proportion
        colors.sort(key=lambda c: c['proportion'], reverse=True)
        
        return colors
    
    async def generate_pre_warped(
        self,
        garment_id: str,
        pose_templates: List[Dict]
    ) -> Dict[str, bytes]:
        """
        Generate pre-warped variants for common poses.
        
        This speeds up try-on for standard poses.
        """
        # Load original garment
        garment_dir = self.output_dir / garment_id
        original_path = garment_dir / "original.png"
        
        if not original_path.exists():
            logger.warning(f"Original not found for {garment_id}")
            return {}
        
        image = Image.open(original_path)
        pre_warped = {}
        
        for template in pose_templates:
            pose_type = template.get('type', 'default')
            
            # Apply warping based on template
            # This would use the same TPS warping as the main pipeline
            warped = await self._warp_for_pose(image, template)
            
            buffer = io.BytesIO()
            warped.save(buffer, format='PNG')
            pre_warped[f"warped_{pose_type}"] = buffer.getvalue()
        
        return pre_warped
    
    async def _warp_for_pose(self, image: Image.Image, template: Dict) -> Image.Image:
        """Warp garment for specific pose template."""
        # Placeholder - actual implementation would use TPS warping
        return image.copy()


# ===========================================
# Batch Processing
# ===========================================

async def batch_preprocess_garments(
    garment_ids: List[str],
    image_loader: callable
) -> List[Dict[str, Any]]:
    """
    Batch preprocess multiple garments.
    
    Args:
        garment_ids: List of garment IDs
        image_loader: Async function to load image by ID
        
    Returns:
        List of preprocessing results
    """
    preprocessor = GarmentPreprocessor()
    results = []
    
    for garment_id in garment_ids:
        try:
            image_bytes = await image_loader(garment_id)
            result = await preprocessor.preprocess_garment(garment_id, image_bytes)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to preprocess {garment_id}: {e}")
            results.append({
                'garment_id': garment_id,
                'success': False,
                'error': str(e),
            })
    
    return results


# ===========================================
# CLI Entry Point
# ===========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python preprocessing_pipeline.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    garment_id = Path(image_path).stem
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    preprocessor = GarmentPreprocessor()
    result = asyncio.run(preprocessor.preprocess_garment(garment_id, image_bytes))
    
    print(f"Preprocessing result: {result['success']}")
    if result['success']:
        print(f"Variants: {result['variants']}")
        print(f"Metadata: {result['metadata']}")

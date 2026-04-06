"""
CONFIT Backend — Mock Data Generator
===================================
Generates realistic mock data for development.

Creates:
- Fake pose keypoints
- Fake segmentation masks
- Fake try-on results
- Sample garment images
"""

import io
import base64
import json
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance


@dataclass
class MockGarment:
    """Mock garment data."""
    id: str
    name: str
    category: str
    color: str
    color_hex: str
    image_base64: str
    model_3d_url: Optional[str] = None


@dataclass
class MockTryOnResult:
    """Mock try-on result."""
    garment_id: str
    success: bool
    result_image_base64: str
    quality_score: float
    processing_time_ms: float
    pose_detected: bool


class MockDataGenerator:
    """
    Generates realistic mock data for development.
    
    Usage:
        generator = MockDataGenerator()
        
        # Generate sample garments
        garments = generator.generate_garment_set(10)
        
        # Generate try-on result
        result = generator.generate_tryon_result(user_image, garment)
    """
    
    # Garment categories
    CATEGORIES = {
        'tops': ['shirt', 'blouse', 'jacket', 'sweater', 't-shirt', 'hoodie'],
        'pants': ['jeans', 'trousers', 'chinos', 'shorts', 'leggings'],
        'dresses': ['dress', 'skirt', 'jumpsuit'],
    }
    
    # Colors with hex values
    COLORS = {
        'White': '#FFFFFF',
        'Black': '#000000',
        'Navy': '#1B2838',
        'Gray': '#808080',
        'Red': '#E53935',
        'Blue': '#1E88E5',
        'Green': '#43A047',
        'Yellow': '#FDD835',
        'Pink': '#EC407A',
        'Brown': '#795548',
    }
    
    def __init__(self, output_dir: str = 'mock_services/data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / 'sample_garments').mkdir(exist_ok=True)
        (self.output_dir / 'sample_results').mkdir(exist_ok=True)
        (self.output_dir / 'sample_users').mkdir(exist_ok=True)
    
    def generate_garment_set(self, count: int = 20) -> List[MockGarment]:
        """Generate a set of mock garments."""
        garments = []
        
        for i in range(count):
            category = random.choice(list(self.CATEGORIES.keys()))
            garment_type = random.choice(self.CATEGORIES[category])
            color_name = random.choice(list(self.COLORS.keys()))
            color_hex = self.COLORS[color_name]
            
            garment_id = f"{garment_type}-{i+1:03d}"
            name = f"{color_name} {garment_type.title()}"
            
            # Generate garment image
            image = self._generate_garment_image(category, color_hex)
            image_base64 = self._image_to_base64(image)
            
            garment = MockGarment(
                id=garment_id,
                name=name,
                category=category,
                color=color_name,
                color_hex=color_hex,
                image_base64=image_base64,
                model_3d_url=f"/models/{garment_id}.glb",
            )
            
            garments.append(garment)
            
            # Save image
            image.save(self.output_dir / 'sample_garments' / f"{garment_id}.jpg", quality=85)
        
        # Save manifest
        manifest = {
            'version': '1.0',
            'generated_at': self._get_timestamp(),
            'garments': [asdict(g) for g in garments],
        }
        
        with open(self.output_dir / 'garment_manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return garments
    
    def generate_user_images(self, count: int = 5) -> List[str]:
        """Generate mock user photos."""
        images = []
        
        for i in range(count):
            image = self._generate_user_image()
            image_base64 = self._image_to_base64(image)
            images.append(image_base64)
            
            # Save image
            image.save(self.output_dir / 'sample_users' / f"user_{i+1}.jpg", quality=85)
        
        return images
    
    def generate_tryon_results(self, count: int = 10) -> List[MockTryOnResult]:
        """Generate mock try-on results."""
        results = []
        
        for i in range(count):
            result_image = self._generate_result_image()
            result_base64 = self._image_to_base64(result_image)
            
            result = MockTryOnResult(
                garment_id=f"garment-{i+1:03d}",
                success=True,
                result_image_base64=result_base64,
                quality_score=random.uniform(0.70, 0.95),
                processing_time_ms=random.uniform(2000, 5000),
                pose_detected=True,
            )
            
            results.append(result)
            
            # Save image
            result_image.save(
                self.output_dir / 'sample_results' / f"result_{i+1}.jpg",
                quality=85
            )
        
        return results
    
    def generate_pose_keypoints(self) -> Dict[str, Any]:
        """Generate realistic pose keypoints."""
        # MediaPipe 33-keypoint format
        keypoints = []
        
        # Base positions for frontal pose
        positions = self._get_base_pose_positions()
        
        for i, (name, x, y) in enumerate(positions):
            # Add natural variation
            x_var = x + random.uniform(-0.03, 0.03)
            y_var = y + random.uniform(-0.03, 0.03)
            visibility = random.uniform(0.80, 0.99)
            
            keypoints.append({
                'x': max(0, min(1, x_var)),
                'y': max(0, min(1, y_var)),
                'z': random.uniform(-0.15, 0.15),
                'visibility': visibility,
                'name': name,
            })
        
        return {
            'keypoints': keypoints,
            'num_landmarks': len(keypoints),
            'score': random.uniform(0.85, 0.98),
        }
    
    def generate_segmentation_mask(self, width: int = 512, height: int = 640) -> str:
        """Generate a segmentation mask."""
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        
        # Draw person silhouette
        # Head
        draw.ellipse([width*0.35, height*0.02, width*0.65, height*0.15], fill=255)
        
        # Neck
        draw.rectangle([width*0.42, height*0.12, width*0.58, height*0.18], fill=255)
        
        # Torso
        draw.polygon([
            (width*0.30, height*0.18),
            (width*0.70, height*0.18),
            (width*0.72, height*0.55),
            (width*0.28, height*0.55),
        ], fill=255)
        
        # Arms
        draw.polygon([
            (width*0.30, height*0.18),
            (width*0.15, height*0.35),
            (width*0.18, height*0.38),
            (width*0.32, height*0.25),
        ], fill=255)
        draw.polygon([
            (width*0.70, height*0.18),
            (width*0.85, height*0.35),
            (width*0.82, height*0.38),
            (width*0.68, height*0.25),
        ], fill=255)
        
        # Legs
        draw.rectangle([width*0.28, height*0.55, width*0.45, height*0.95], fill=255)
        draw.rectangle([width*0.55, height*0.55, width*0.72, height*0.95], fill=255)
        
        # Smooth edges
        mask = mask.filter(ImageFilter.GaussianBlur(radius=2))
        
        return self._image_to_base64(mask)
    
    # ========================================
    # Image Generation Helpers
    # ========================================
    
    def _generate_garment_image(self, category: str, color_hex: str) -> Image.Image:
        """Generate a mock garment image."""
        if category == 'tops':
            return self._generate_top_image(color_hex)
        elif category == 'pants':
            return self._generate_pants_image(color_hex)
        else:
            return self._generate_dress_image(color_hex)
    
    def _generate_top_image(self, color_hex: str) -> Image.Image:
        """Generate a top/shirt image."""
        img = Image.new('RGBA', (400, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        color = self._hex_to_rgb(color_hex)
        
        # Body
        draw.polygon([
            (100, 50), (300, 50),
            (320, 400), (80, 400)
        ], fill=color + (255,))
        
        # Sleeves
        draw.polygon([
            (100, 50), (40, 150), (60, 170), (100, 100)
        ], fill=color + (255,))
        draw.polygon([
            (300, 50), (360, 150), (340, 170), (300, 100)
        ], fill=color + (255,))
        
        # Collar
        draw.polygon([
            (160, 50), (200, 80), (240, 50)
        ], fill=(255, 255, 255, 255))
        
        # Add texture
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        
        return img.convert('RGB')
    
    def _generate_pants_image(self, color_hex: str) -> Image.Image:
        """Generate pants image."""
        img = Image.new('RGBA', (300, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        color = self._hex_to_rgb(color_hex)
        
        # Waist
        draw.rectangle([50, 0, 250, 50], fill=color + (255,))
        
        # Legs
        draw.polygon([
            (50, 50), (130, 50), (120, 500), (40, 500)
        ], fill=color + (255,))
        draw.polygon([
            (170, 50), (250, 50), (260, 500), (180, 500)
        ], fill=color + (255,))
        
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        
        return img.convert('RGB')
    
    def _generate_dress_image(self, color_hex: str) -> Image.Image:
        """Generate dress image."""
        img = Image.new('RGBA', (350, 550), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        color = self._hex_to_rgb(color_hex)
        
        # Top part
        draw.polygon([
            (100, 30), (250, 30),
            (260, 120), (90, 120)
        ], fill=color + (255,))
        
        # Skirt
        draw.polygon([
            (90, 120), (260, 120),
            (300, 550), (50, 550)
        ], fill=color + (255,))
        
        # Sleeves
        draw.ellipse([60, 30, 100, 80], fill=color + (255,))
        draw.ellipse([250, 30, 290, 80], fill=color + (255,))
        
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        
        return img.convert('RGB')
    
    def _generate_user_image(self) -> Image.Image:
        """Generate a mock user photo placeholder."""
        img = Image.new('RGB', (512, 640), (240, 240, 245))
        draw = ImageDraw.Draw(img)
        
        # Draw person silhouette
        draw.ellipse([180, 30, 332, 130], fill=(200, 180, 170))  # Head
        draw.rectangle([160, 130, 352, 400], fill=(100, 100, 120))  # Torso
        draw.rectangle([160, 400, 240, 620], fill=(60, 60, 80))  # Left leg
        draw.rectangle([272, 400, 352, 620], fill=(60, 60, 80))  # Right leg
        
        # Add text
        draw.text((180, 300), "Sample User Photo", fill=(150, 150, 150))
        
        return img
    
    def _generate_result_image(self) -> Image.Image:
        """Generate a mock try-on result."""
        img = Image.new('RGB', (512, 640), (245, 245, 250))
        draw = ImageDraw.Draw(img)
        
        # Background gradient
        for y in range(640):
            color = int(245 - y * 0.02)
            draw.line([(0, y), (512, y)], fill=(color, color, color + 5))
        
        # Person silhouette
        draw.ellipse([180, 30, 332, 130], fill=(210, 190, 180))  # Head
        draw.rectangle([160, 130, 352, 400], fill=(80, 100, 140))  # Torso (garment)
        draw.rectangle([160, 400, 240, 620], fill=(50, 50, 70))  # Left leg
        draw.rectangle([272, 400, 352, 620], fill=(50, 50, 70))  # Right leg
        
        # Add "result" text
        draw.text((160, 580), "Virtual Try-On Result", fill=(120, 120, 130))
        draw.text((180, 600), "(Mock Mode)", fill=(150, 150, 160))
        
        # Add border
        draw.rectangle([5, 5, 507, 635], outline=(200, 200, 210), width=2)
        
        return img
    
    def _get_base_pose_positions(self) -> List[tuple]:
        """Get base pose positions for frontal stance."""
        return [
            ('nose', 0.5, 0.08),
            ('left_eye_inner', 0.47, 0.06),
            ('left_eye', 0.46, 0.06),
            ('left_eye_outer', 0.45, 0.06),
            ('right_eye_inner', 0.53, 0.06),
            ('right_eye', 0.54, 0.06),
            ('right_eye_outer', 0.55, 0.06),
            ('left_ear', 0.43, 0.07),
            ('right_ear', 0.57, 0.07),
            ('mouth_left', 0.48, 0.09),
            ('mouth_right', 0.52, 0.09),
            ('left_shoulder', 0.38, 0.20),
            ('right_shoulder', 0.62, 0.20),
            ('left_elbow', 0.32, 0.35),
            ('right_elbow', 0.68, 0.35),
            ('left_wrist', 0.28, 0.48),
            ('right_wrist', 0.72, 0.48),
            ('left_pinky', 0.27, 0.50),
            ('right_pinky', 0.73, 0.50),
            ('left_index', 0.26, 0.48),
            ('right_index', 0.74, 0.48),
            ('left_thumb', 0.28, 0.49),
            ('right_thumb', 0.72, 0.49),
            ('left_hip', 0.42, 0.52),
            ('right_hip', 0.58, 0.52),
            ('left_knee', 0.43, 0.72),
            ('right_knee', 0.57, 0.72),
            ('left_ankle', 0.44, 0.92),
            ('right_ankle', 0.56, 0.92),
            ('left_heel', 0.44, 0.94),
            ('right_heel', 0.56, 0.94),
            ('left_foot_index', 0.42, 0.96),
            ('right_foot_index', 0.58, 0.96),
        ]
    
    # ========================================
    # Utility Methods
    # ========================================
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _image_to_base64(self, image: Image.Image, format: str = 'JPEG') -> str:
        """Convert image to base64 string."""
        buffer = io.BytesIO()
        
        if format == 'JPEG':
            image = image.convert('RGB')
        
        image.save(buffer, format=format, quality=85)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# ========================================
# CLI Entry Point
# ========================================

def main():
    """Generate all mock data."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate mock data for development')
    parser.add_argument('--garments', type=int, default=20, help='Number of garments to generate')
    parser.add_argument('--users', type=int, default=5, help='Number of user images to generate')
    parser.add_argument('--results', type=int, default=10, help='Number of results to generate')
    parser.add_argument('--output', type=str, default='mock_services/data', help='Output directory')
    
    args = parser.parse_args()
    
    generator = MockDataGenerator(output_dir=args.output)
    
    print(f"Generating mock data in {args.output}...")
    
    # Generate garments
    garments = generator.generate_garment_set(args.garments)
    print(f"Generated {len(garments)} garments")
    
    # Generate user images
    users = generator.generate_user_images(args.users)
    print(f"Generated {len(users)} user images")
    
    # Generate results
    results = generator.generate_tryon_results(args.results)
    print(f"Generated {len(results)} try-on results")
    
    print("\nMock data generation complete!")
    print(f"Files saved to: {args.output}")


if __name__ == '__main__':
    main()

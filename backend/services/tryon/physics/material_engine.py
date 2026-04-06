"""
Fabric Material Intelligence — classification, property lookup, and light/blend parameters.

Single reusable engine for try-on: texture frequency + wrinkle cues → fabric class →
physics/lighting/blend coefficients. Garment analysis is cached by image fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# --- Cache: one analysis per garment image (process lifetime) ---
_FABRIC_CACHE: Dict[str, Tuple[str, "MaterialProperties", Dict[str, float]]] = {}
_FABRIC_CACHE_ORDER: List[str] = []
_MAX_FABRIC_CACHE = 64


class FabricType(str, Enum):
    COTTON = "cotton"
    DENIM = "denim"
    LEATHER = "leather"
    SILK = "silk"
    WOOL = "wool"
    POLYESTER = "polyester"
    KNIT = "knit"
    UNKNOWN = "unknown"


@dataclass
class MaterialProperties:
    """Numeric + semantic material parameters used by warp, lighting, and edge feather.
    
    CONFIT Fabric Material Intelligence:
    - Detects fabric class from texture patterns
    - Assigns physical properties dynamically
    - Modifies garment simulation per fabric type
    - Adapts shading model for realistic appearance
    """

    fabric: FabricType = FabricType.COTTON
    # Semantic (for JSON / debugging)
    stiffness: str = "medium"  # low | medium | high | very_high
    gravity: str = "normal"  # low | normal | high
    wrinkle: str = "medium"  # low | medium | high
    stretch: str = "medium"  # low | medium | high
    flow: str = "medium"
    reflection: str = "soft"  # soft | medium | sharp
    specular: str = "medium"  # weak | medium | strong
    
    # Numeric drivers (0..1 unless noted)
    bend_stiffness_scale: float = 1.0
    stretch_stiffness_scale: float = 1.0
    shear_scale: float = 1.0
    gravity_scale: float = 1.0
    wrinkle_strength_scale: float = 1.0
    stretch_highlight_scale: float = 1.0
    max_stretch_ratio: float = 1.12  # caps unrealistic extension in PBD
    reflection_soft: float = 0.55
    specular_strength: float = 0.45
    diffuse_lighting: float = 0.55
    edge_feather_px: int = 6
    classification_confidence: float = 0.5
    features: Dict[str, float] = field(default_factory=dict)
    
    # CONFIT Fabric Intelligence - Extended Physics Properties
    fold_frequency: float = 0.5  # 0=flat, 1=many folds (cotton=high, leather=low)
    wrinkle_persistence: float = 0.5  # 0=smooths quickly, 1=holds wrinkles
    fabric_thickness: float = 0.5  # 0=thin silk, 1=thick wool/leather
    elasticity: float = 0.5  # 0=rigid denim, 1=stretchy knit
    drape_coefficient: float = 0.5  # 0=stiff, 1=flowy (silk=high)
    micro_shadow_strength: float = 0.3  # shadow depth in fabric folds
    subsurface_scatter: float = 0.0  # for thin fabrics (silk, chiffon)


def _semantic_db() -> Dict[FabricType, Dict[str, Any]]:
    """Material properties database (Step 2).
    
    CONFIT Fabric Intelligence Properties:
    - stiffness: resistance to bending
    - gravity: how fabric responds to gravity
    - wrinkle: tendency to form wrinkles
    - stretch: elasticity under tension
    - flow: how fabric drapes/moves
    - fold_frequency: number of natural folds
    - wrinkle_persistence: how long wrinkles hold
    - fabric_thickness: visual thickness
    - elasticity: stretch recovery
    - drape_coefficient: how fabric hangs
    """
    return {
        FabricType.COTTON: {
            "stiffness": "medium",
            "gravity": "normal",
            "wrinkle": "high",
            "stretch": "medium",
            "flow": "low",
            "reflection": "diffuse",
            "specular": "weak",
            "bend_stiffness_scale": 0.92,
            "stretch_stiffness_scale": 0.88,
            "shear_scale": 0.9,
            "gravity_scale": 1.0,
            "wrinkle_strength_scale": 1.15,
            "stretch_highlight_scale": 0.85,
            "max_stretch_ratio": 1.14,
            "reflection_soft": 0.35,
            "specular_strength": 0.25,
            "diffuse_lighting": 0.85,
            "edge_feather_px": 7,
            # CONFIT extended properties
            "fold_frequency": 0.75,  # Cotton forms soft folds easily
            "wrinkle_persistence": 0.65,  # Wrinkles hold moderately
            "fabric_thickness": 0.45,  # Medium thickness
            "elasticity": 0.35,  # Low stretch
            "drape_coefficient": 0.35,  # Moderate drape
            "micro_shadow_strength": 0.4,  # Visible shadows in folds
            "subsurface_scatter": 0.05,
        },
        FabricType.DENIM: {
            "stiffness": "high",
            "gravity": "normal",
            "wrinkle": "medium",
            "stretch": "low",
            "flow": "low",
            "reflection": "diffuse",
            "specular": "weak",
            "bend_stiffness_scale": 1.18,
            "stretch_stiffness_scale": 1.12,
            "shear_scale": 1.05,
            "gravity_scale": 1.02,
            "wrinkle_strength_scale": 0.75,
            "stretch_highlight_scale": 0.55,
            "max_stretch_ratio": 1.06,
            "reflection_soft": 0.28,
            "specular_strength": 0.22,
            "diffuse_lighting": 0.7,
            "edge_feather_px": 3,
            # CONFIT extended properties - rigid deformation limits
            "fold_frequency": 0.35,  # Fewer, larger folds
            "wrinkle_persistence": 0.8,  # Wrinkles hold strongly
            "fabric_thickness": 0.7,  # Thick material
            "elasticity": 0.15,  # Very low stretch (rigid)
            "drape_coefficient": 0.2,  # Stiff, doesn't drape much
            "micro_shadow_strength": 0.5,  # Strong shadows in creases
            "subsurface_scatter": 0.0,
        },
        FabricType.SILK: {
            "stiffness": "low",
            "gravity": "normal",
            "wrinkle": "low",
            "stretch": "medium",
            "flow": "high",
            "reflection": "soft",
            "specular": "medium",
            "bend_stiffness_scale": 0.62,
            "stretch_stiffness_scale": 0.72,
            "shear_scale": 0.78,
            "gravity_scale": 1.08,
            "wrinkle_strength_scale": 0.55,
            "stretch_highlight_scale": 1.05,
            "max_stretch_ratio": 1.18,
            "reflection_soft": 0.88,
            "specular_strength": 0.5,
            "diffuse_lighting": 0.45,
            "edge_feather_px": 9,
            # CONFIT extended properties - high flow dynamics
            "fold_frequency": 0.9,  # Many flowing folds
            "wrinkle_persistence": 0.15,  # Wrinkles smooth out quickly
            "fabric_thickness": 0.15,  # Very thin
            "elasticity": 0.45,  # Moderate stretch
            "drape_coefficient": 0.95,  # High drape, flows beautifully
            "micro_shadow_strength": 0.2,  # Subtle shadows
            "subsurface_scatter": 0.25,  # Light passes through
        },
        FabricType.LEATHER: {
            "stiffness": "very_high",
            "gravity": "low",
            "wrinkle": "low",
            "stretch": "low",
            "flow": "low",
            "reflection": "sharp",
            "specular": "strong",
            "bend_stiffness_scale": 1.35,
            "stretch_stiffness_scale": 1.22,
            "shear_scale": 1.12,
            "gravity_scale": 0.88,
            "wrinkle_strength_scale": 0.45,
            "stretch_highlight_scale": 1.2,
            "max_stretch_ratio": 1.04,
            "reflection_soft": 0.2,
            "specular_strength": 0.92,
            "diffuse_lighting": 0.4,
            "edge_feather_px": 4,
            # CONFIT extended properties - minimal folding, strong highlights
            "fold_frequency": 0.15,  # Minimal folds
            "wrinkle_persistence": 0.9,  # Creases hold permanently
            "fabric_thickness": 0.85,  # Thick
            "elasticity": 0.08,  # Almost no stretch
            "drape_coefficient": 0.1,  # Very stiff
            "micro_shadow_strength": 0.6,  # Strong shadows at edges
            "subsurface_scatter": 0.0,
        },
        FabricType.WOOL: {
            "stiffness": "medium",
            "gravity": "normal",
            "wrinkle": "medium",
            "stretch": "medium",
            "flow": "medium",
            "reflection": "diffuse",
            "specular": "weak",
            "bend_stiffness_scale": 0.85,
            "stretch_stiffness_scale": 0.82,
            "shear_scale": 0.88,
            "gravity_scale": 1.05,
            "wrinkle_strength_scale": 0.95,
            "stretch_highlight_scale": 0.75,
            "max_stretch_ratio": 1.1,
            "reflection_soft": 0.42,
            "specular_strength": 0.28,
            "diffuse_lighting": 0.78,
            "edge_feather_px": 8,
            # CONFIT extended properties - volume preservation
            "fold_frequency": 0.55,  # Moderate folds
            "wrinkle_persistence": 0.5,  # Wrinkles hold moderately
            "fabric_thickness": 0.8,  # Thick, voluminous
            "elasticity": 0.4,  # Moderate stretch
            "drape_coefficient": 0.5,  # Moderate drape
            "micro_shadow_strength": 0.35,  # Soft shadows
            "subsurface_scatter": 0.1,
        },
        FabricType.POLYESTER: {
            "stiffness": "medium",
            "gravity": "low",
            "wrinkle": "low",
            "stretch": "high",
            "flow": "medium",
            "reflection": "medium",
            "specular": "medium",
            "bend_stiffness_scale": 0.95,
            "stretch_stiffness_scale": 0.78,
            "shear_scale": 0.85,
            "gravity_scale": 0.95,
            "wrinkle_strength_scale": 0.65,
            "stretch_highlight_scale": 0.95,
            "max_stretch_ratio": 1.2,
            "reflection_soft": 0.55,
            "specular_strength": 0.55,
            "diffuse_lighting": 0.6,
            "edge_feather_px": 5,
            # CONFIT extended properties
            "fold_frequency": 0.4,  # Fewer folds
            "wrinkle_persistence": 0.2,  # Wrinkles smooth out (wrinkle-resistant)
            "fabric_thickness": 0.35,  # Thin to medium
            "elasticity": 0.7,  # High stretch
            "drape_coefficient": 0.55,  # Moderate drape
            "micro_shadow_strength": 0.25,
            "subsurface_scatter": 0.0,
        },
        FabricType.KNIT: {
            "stiffness": "low",
            "gravity": "normal",
            "wrinkle": "medium",
            "stretch": "high",
            "flow": "high",
            "reflection": "diffuse",
            "specular": "weak",
            "bend_stiffness_scale": 0.55,
            "stretch_stiffness_scale": 0.62,
            "shear_scale": 0.68,
            "gravity_scale": 1.0,
            "wrinkle_strength_scale": 0.85,
            "stretch_highlight_scale": 0.72,
            "max_stretch_ratio": 1.22,
            "reflection_soft": 0.48,
            "specular_strength": 0.3,
            "diffuse_lighting": 0.72,
            "edge_feather_px": 11,
            # CONFIT extended properties - soft, stretchy
            "fold_frequency": 0.8,  # Many soft folds
            "wrinkle_persistence": 0.4,  # Wrinkles don't hold long
            "fabric_thickness": 0.5,  # Medium thickness
            "elasticity": 0.85,  # Very stretchy
            "drape_coefficient": 0.7,  # Good drape
            "micro_shadow_strength": 0.3,
            "subsurface_scatter": 0.05,
        },
        FabricType.UNKNOWN: {
            "stiffness": "medium",
            "gravity": "normal",
            "wrinkle": "medium",
            "stretch": "medium",
            "flow": "medium",
            "reflection": "diffuse",
            "specular": "medium",
            "bend_stiffness_scale": 1.0,
            "stretch_stiffness_scale": 1.0,
            "shear_scale": 1.0,
            "gravity_scale": 1.0,
            "wrinkle_strength_scale": 1.0,
            "stretch_highlight_scale": 1.0,
            "max_stretch_ratio": 1.12,
            "reflection_soft": 0.5,
            "specular_strength": 0.45,
            "diffuse_lighting": 0.55,
            "edge_feather_px": 6,
            # CONFIT extended properties - safe defaults
            "fold_frequency": 0.5,
            "wrinkle_persistence": 0.5,
            "fabric_thickness": 0.5,
            "elasticity": 0.5,
            "drape_coefficient": 0.5,
            "micro_shadow_strength": 0.3,
            "subsurface_scatter": 0.0,
        },
    }


def struct_pack_shape(shape: Tuple[int, ...]) -> bytes:
    import struct

    return struct.pack("<" + "I" * len(shape), *tuple(int(x) for x in shape))


def material_from_fabric_type(ft: FabricType, features: Optional[Dict[str, float]] = None) -> MaterialProperties:
    db = _semantic_db()[ft]
    return MaterialProperties(
        fabric=ft,
        stiffness=str(db["stiffness"]),
        gravity=str(db["gravity"]),
        wrinkle=str(db["wrinkle"]),
        stretch=str(db["stretch"]),
        flow=str(db["flow"]),
        reflection=str(db["reflection"]),
        specular=str(db["specular"]),
        bend_stiffness_scale=float(db["bend_stiffness_scale"]),
        stretch_stiffness_scale=float(db["stretch_stiffness_scale"]),
        shear_scale=float(db["shear_scale"]),
        gravity_scale=float(db["gravity_scale"]),
        wrinkle_strength_scale=float(db["wrinkle_strength_scale"]),
        stretch_highlight_scale=float(db["stretch_highlight_scale"]),
        max_stretch_ratio=float(db["max_stretch_ratio"]),
        reflection_soft=float(db["reflection_soft"]),
        specular_strength=float(db["specular_strength"]),
        diffuse_lighting=float(db["diffuse_lighting"]),
        edge_feather_px=int(db["edge_feather_px"]),
        features=dict(features or {}),
    )


def _garment_fingerprint(rgba: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(rgba).tobytes())
    h.update(struct_pack_shape(rgba.shape))
    return h.hexdigest()[:40]


def _masked_region(gray: np.ndarray, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    m = mask.astype(bool)
    if not np.any(m):
        return gray, m
    ys, xs = np.where(m)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    pad = 4
    y0 = max(0, y0 - pad)
    x0 = max(0, x0 - pad)
    y1 = min(gray.shape[0], y1 + pad)
    x1 = min(gray.shape[1], x1 + pad)
    crop_g = gray[y0:y1, x0:x1]
    crop_m = m[y0:y1, x0:x1]
    return crop_g, crop_m


def extract_fabric_features(rgba: np.ndarray) -> Dict[str, float]:
    """
    Texture frequency (Laplacian / FFT) + wrinkle proxy (gradient activity).
    Values are normalized to roughly 0..1 for logging and classification.
    """
    if rgba.ndim != 3 or rgba.shape[2] < 3:
        return {"texture_frequency": 0.5, "wrinkle_pattern": 0.5, "hue_blue_bias": 0.0, "smoothness": 0.5}

    rgb = rgba[:, :, :3]
    a = rgba[:, :, 3] if rgba.shape[2] > 3 else np.ones(rgb.shape[:2], dtype=np.uint8) * 255
    mask = a > 28
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    cg, cm = _masked_region(gray, mask)
    if cg.size < 400 or not np.any(cm):
        return {"texture_frequency": 0.5, "wrinkle_pattern": 0.5, "hue_blue_bias": 0.0, "smoothness": 0.5}

    g = cg.astype(np.float32)
    lap = cv2.Laplacian(g, cv2.CV_32F)
    lap_v = float(np.var(lap[cm]))
    # Normalize lap variance (empirical caps for catalog photos)
    texture_frequency = float(np.clip(lap_v / 1800.0, 0.0, 1.0))

    sox = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    soy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(sox * sox + soy * soy)
    wrinkle_pattern = float(np.clip(np.mean(mag[cm]) / 48.0, 0.0, 1.0))

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hh = hsv[:, :, 0]
    # OpenCV H 0-179; blue-ish ~ 100-130
    blue_mask = (hh > 95) & (hh < 135) & mask
    hue_blue_bias = float(np.sum(blue_mask) / (np.sum(mask) + 1e-6))

    smoothness = float(np.clip(1.0 - 0.65 * texture_frequency - 0.15 * wrinkle_pattern, 0.0, 1.0))

    return {
        "texture_frequency": texture_frequency,
        "wrinkle_pattern": wrinkle_pattern,
        "hue_blue_bias": hue_blue_bias,
        "smoothness": smoothness,
    }


def _name_hints(name: str) -> Dict[FabricType, float]:
    n = (name or "").lower()
    w: Dict[FabricType, float] = {t: 0.0 for t in FabricType if t != FabricType.UNKNOWN}
    if any(k in n for k in ("denim", "jean", "jeans")):
        w[FabricType.DENIM] += 0.45
    if any(k in n for k in ("leather", "pu leather", "faux leather", "vegan leather")):
        w[FabricType.LEATHER] += 0.45
    if any(k in n for k in ("silk", "satin", "chiffon")):
        w[FabricType.SILK] += 0.35
    if any(k in n for k in ("wool", "cashmere", "tweed")):
        w[FabricType.WOOL] += 0.35
    if any(k in n for k in ("knit", "knitted", "sweater", "ribbed", "cable knit")):
        w[FabricType.KNIT] += 0.4
    if any(k in n for k in ("polyester", "nylon", "spandex", "lycra", "athletic")):
        w[FabricType.POLYESTER] += 0.25
    if any(k in n for k in ("cotton", "linen", "chambray")):
        w[FabricType.COTTON] += 0.2
    return w


def classify_fabric(
    rgba: np.ndarray,
    garment_name: str = "",
) -> Tuple[FabricType, float, Dict[str, float]]:
    """
    Step 1 — classify fabric from image features + optional product name.
    Returns (type, confidence, raw features).
    """
    feat = extract_fabric_features(rgba)
    tf = feat["texture_frequency"]
    wp = feat["wrinkle_pattern"]
    hb = feat["hue_blue_bias"]
    sm = feat["smoothness"]

    # Uniform / flat catalog crops — insufficient texture; avoid mislabeling as leather/silk
    if tf < 0.06 and wp < 0.07:
        return FabricType.UNKNOWN, 0.48, feat

    scores: Dict[FabricType, float] = {t: 0.0 for t in FabricType if t != FabricType.UNKNOWN}

    # Vision logits (soft decision boundaries)
    scores[FabricType.KNIT] += 0.55 * tf + 0.15 * wp
    scores[FabricType.DENIM] += 0.5 * tf + 0.35 * hb + 0.1 * wp
    scores[FabricType.SILK] += 0.45 * sm + 0.25 * (1.0 - wp) + 0.1 * (1.0 - tf)
    scores[FabricType.LEATHER] += 0.4 * sm + 0.35 * (1.0 - wp) + 0.15 * (1.0 - tf)
    scores[FabricType.WOOL] += 0.35 * tf + 0.35 * wp + 0.1 * (1.0 - hb)
    scores[FabricType.COTTON] += 0.4 * wp + 0.25 * (1.0 - sm) + 0.1 * tf
    scores[FabricType.POLYESTER] += 0.35 * (1.0 - wp) + 0.25 * sm + 0.2 * tf

    nh = _name_hints(garment_name)
    for t, add in nh.items():
        scores[t] += add

    best = max(scores.items(), key=lambda x: x[1])
    ft, raw = best[0], best[1]
    total = sum(max(0.0, v) for v in scores.values()) + 1e-6
    confidence = float(np.clip(raw / total, 0.25, 0.98))

    # Low separation → unknown bucket (defaults to cotton-like safe params)
    sorted_v = sorted(scores.values(), reverse=True)
    margin = (sorted_v[0] - sorted_v[1]) if len(sorted_v) > 1 else 0.0
    if margin < 0.06 and nh.get(ft, 0) < 0.15:
        ft = FabricType.UNKNOWN
        confidence = max(0.35, confidence * 0.75)

    return ft, confidence, feat


def analyze_garment_material(
    rgba: np.ndarray,
    garment_name: str = "",
    *,
    use_cache: bool = True,
) -> MaterialProperties:
    """
    Full analysis: classify + material row. Cached per garment fingerprint.
    """
    fp = _garment_fingerprint(rgba)
    if use_cache and fp in _FABRIC_CACHE:
        ft_s, mat, _ = _FABRIC_CACHE[fp]
        logger.debug("fabric intelligence cache hit %s (%s)", fp[:12], ft_s)
        return mat

    ft, conf, feat = classify_fabric(rgba, garment_name=garment_name)
    mat = material_from_fabric_type(ft, feat)
    mat.classification_confidence = conf
    mat.features = {**feat, "margin": float(conf)}

    if use_cache:
        if len(_FABRIC_CACHE) >= _MAX_FABRIC_CACHE:
            old = _FABRIC_CACHE_ORDER.pop(0)
            _FABRIC_CACHE.pop(old, None)
        _FABRIC_CACHE[fp] = (ft.value, mat, feat)
        _FABRIC_CACHE_ORDER.append(fp)

    return mat


def to_fabric_type_json(mat: MaterialProperties) -> str:
    """fabric_type.json compatible payload (Step 1 + 2)."""
    db = _semantic_db().get(mat.fabric, _semantic_db()[FabricType.UNKNOWN])
    payload = {
        "version": 2,
        "fabric_type": mat.fabric.value,
        "confidence": round(float(mat.classification_confidence), 4),
        "features": {
            "texture_frequency": round(float(mat.features.get("texture_frequency", 0)), 4),
            "wrinkle_pattern": round(float(mat.features.get("wrinkle_pattern", 0)), 4),
            "hue_blue_bias": round(float(mat.features.get("hue_blue_bias", 0)), 4),
            "smoothness": round(float(mat.features.get("smoothness", 0)), 4),
        },
        "material_properties": {
            "stiffness": db.get("stiffness", mat.stiffness),
            "gravity": db.get("gravity", mat.gravity),
            "wrinkle": db.get("wrinkle", mat.wrinkle),
            "stretch": db.get("stretch", mat.stretch),
            "flow": db.get("flow", mat.flow),
            "reflection": mat.reflection,
            "specular": mat.specular,
        },
        "adaptive_parameters": {
            "bend_stiffness_scale": mat.bend_stiffness_scale,
            "stretch_stiffness_scale": mat.stretch_stiffness_scale,
            "edge_feather_px": mat.edge_feather_px,
            "max_stretch_ratio": mat.max_stretch_ratio,
            "reflection_soft": mat.reflection_soft,
            "specular_strength": mat.specular_strength,
            "diffuse_lighting": mat.diffuse_lighting,
        },
        # CONFIT Fabric Intelligence - Extended Physics Properties
        "fabric_intelligence": {
            "fold_frequency": round(mat.fold_frequency, 4),
            "wrinkle_persistence": round(mat.wrinkle_persistence, 4),
            "fabric_thickness": round(mat.fabric_thickness, 4),
            "elasticity": round(mat.elasticity, 4),
            "drape_coefficient": round(mat.drape_coefficient, 4),
            "micro_shadow_strength": round(mat.micro_shadow_strength, 4),
            "subsurface_scatter": round(mat.subsurface_scatter, 4),
        },
    }
    return json.dumps(payload, indent=2)


def apply_material_lighting_rgb(
    rgb: np.ndarray,
    alpha: np.ndarray,
    mat: MaterialProperties,
) -> np.ndarray:
    """
    Step 4 — light response: adjust highlights/specular/diffuse per fabric.
    Operates on garment RGB with alpha mask.
    
    CONFIT Fabric Intelligence Shading:
    - Adjust specular reflection based on fabric type
    - Apply micro-shadows in fold areas
    - Simulate fabric thickness via edge darkening
    - Subsurface scattering for thin fabrics (silk)
    """
    a = np.clip(alpha.astype(np.float32) / 255.0, 0.0, 1.0)
    if float(np.max(a)) < 0.02:
        return rgb

    out = rgb.astype(np.float32)
    valid = a > 0.06
    if not np.any(valid):
        return rgb

    # Cotton / diffuse: soften highlight contrast in LAB
    if mat.diffuse_lighting > 0.72:
        lab = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
        L = lab[:, :, 0]
        thr_l = float(np.percentile(L[valid], 88))
        hi = ((L > thr_l).astype(np.float32)) * a
        blur = cv2.GaussianBlur(L, (0, 0), sigmaX=2.2, sigmaY=2.2)
        L = L * (1.0 - 0.35 * hi) + blur * (0.35 * hi)
        lab[:, :, 0] = np.clip(L, 0, 255)
        out = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)

    # Silk: soft reflections — bloom on bright regions + subsurface scatter
    if mat.reflection_soft > 0.75:
        gray = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        thr_g = float(np.percentile(gray[valid], 88))
        hi = ((gray > thr_g).astype(np.float32)) * a
        hi_blur = cv2.GaussianBlur(hi, (0, 0), 4.0)
        glow = cv2.GaussianBlur(out, (0, 0), 2.5)
        out = out * (1.0 - 0.22 * hi_blur[:, :, None]) + glow * (0.22 * hi_blur[:, :, None])
        
        # Subsurface scattering for thin fabrics (silk, chiffon)
        if mat.subsurface_scatter > 0.1:
            # Simulate light passing through thin fabric
            scatter = cv2.GaussianBlur(out, (7, 7), 3.0)
            scatter_weight = mat.subsurface_scatter * a[..., None] * 0.15
            out = out * (1.0 - scatter_weight) + scatter * scatter_weight

    # Leather: sharper specular peaks
    if mat.specular_strength > 0.78:
        gray = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        thr_g = float(np.percentile(gray[valid], 88))
        peak = np.clip((gray - thr_g) / 35.0, 0.0, 1.0) * a
        peak = cv2.GaussianBlur(peak, (3, 3), 0)
        for c in range(3):
            out[:, :, c] = np.clip(out[:, :, c] + peak * 28.0 * mat.specular_strength, 0, 255)
    
    # Micro-shadows for fabrics with high fold frequency (cotton, knit)
    if mat.micro_shadow_strength > 0.35 and mat.fold_frequency > 0.6:
        # Add subtle shadow variation in fold areas
        gray = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        # Detect fold-like patterns via local contrast
        local_mean = cv2.GaussianBlur(gray, (15, 15), 0)
        local_contrast = np.abs(gray - local_mean) / 255.0
        shadow_mask = local_contrast * a * mat.micro_shadow_strength * 0.1
        out = out * (1.0 - shadow_mask[..., None])
    
    # Fabric thickness simulation
    if mat.fabric_thickness > 0.7:
        # Thick fabrics (wool, leather) - slightly darker, more saturated
        saturation_boost = 1.0 + (mat.fabric_thickness - 0.7) * 0.1
        hsv = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_boost, 0, 255)
        out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)

    return np.clip(out, 0, 255).astype(np.uint8)


__all__ = [
    "FabricType",
    "MaterialProperties",
    "material_from_fabric_type",
    "analyze_garment_material",
    "to_fabric_type_json",
    "extract_fabric_features",
    "apply_material_lighting_rgb",
]

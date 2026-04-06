"""Physics-based fabric simulation for virtual try-on (PBD + material intelligence)."""

from .fabric_engine import apply_fabric_physics_to_warp
from .material_engine import (
    FabricType,
    MaterialProperties,
    analyze_garment_material,
    apply_material_lighting_rgb,
    to_fabric_type_json,
)

__all__ = [
    "apply_fabric_physics_to_warp",
    "FabricType",
    "MaterialProperties",
    "analyze_garment_material",
    "apply_material_lighting_rgb",
    "to_fabric_type_json",
]

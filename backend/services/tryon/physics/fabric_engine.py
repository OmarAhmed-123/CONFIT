"""
Position-Based Dynamics (PBD) fabric simulation for 2D try-on warping.

Pipeline slot: pose → cloth mesh + body colliders → PBD settle → tension wrinkles → output RGBA.

Designed for CPU (vectorized NumPy). Optional CuPy/torch hooks are not required.
"""

from __future__ import annotations

import hashlib
import logging
import os
import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from services.tryon.vision.pose import PoseResult

if TYPE_CHECKING:
    from services.tryon.physics.material_engine import MaterialProperties

logger = logging.getLogger(__name__)

# Simple mesh cache: key -> last warped rgba (uint8) — avoids recomputation for identical inputs in-process
_MESH_CACHE: Dict[str, np.ndarray] = {}
_MESH_CACHE_ORDER: List[str] = []
_MAX_MESH_CACHE = 16


@dataclass
class FabricConfig:
    """Simulation parameters (full vs lightweight).
    
    CONFIT Fabric Intelligence Parameters:
    - grid_u/v: mesh resolution
    - iterations: PBD solver iterations
    - stretch_stiffness: resistance to stretching
    - bend_stiffness: resistance to bending (folds)
    - shear_stiffness: resistance to diagonal deformation
    - gravity_px: gravity force in pixels
    - drag: velocity damping
    - fabric_mass: mass multiplier
    - collision_margin: body collision padding
    - wrinkle_strength: wrinkle visualization intensity
    - stretch_highlight: highlight intensity on stretched areas
    - fold_frequency: natural fold pattern density
    - wrinkle_persistence: how long wrinkles hold shape
    - fabric_thickness: visual thickness for shading
    - micro_shadow_strength: shadow depth in folds
    """

    grid_u: int = 24
    grid_v: int = 32
    iterations: int = 32
    stretch_stiffness: float = 0.85
    bend_stiffness: float = 0.35
    shear_stiffness: float = 0.45
    gravity_px: float = 0.42
    drag: float = 0.985
    fabric_mass: float = 1.0
    collision_margin: float = 1.25
    wrinkle_strength: float = 0.12
    stretch_highlight: float = 0.06
    # CONFIT extended parameters
    fold_frequency: float = 0.5
    wrinkle_persistence: float = 0.5
    fabric_thickness: float = 0.5
    micro_shadow_strength: float = 0.3

    @classmethod
    def full(cls) -> "FabricConfig":
        return cls(
            grid_u=26,
            grid_v=34,
            iterations=36,
            stretch_stiffness=0.88,
            bend_stiffness=0.38,
            shear_stiffness=0.48,
            gravity_px=0.45,
            drag=0.988,
            fabric_mass=1.0,
            collision_margin=1.2,
            wrinkle_strength=0.14,
            stretch_highlight=0.07,
            fold_frequency=0.5,
            wrinkle_persistence=0.5,
            fabric_thickness=0.5,
            micro_shadow_strength=0.3,
        )

    @classmethod
    def lightweight(cls) -> "FabricConfig":
        return cls(
            grid_u=14,
            grid_v=18,
            iterations=18,
            stretch_stiffness=0.8,
            bend_stiffness=0.28,
            shear_stiffness=0.38,
            gravity_px=0.38,
            drag=0.98,
            fabric_mass=1.05,
            collision_margin=1.35,
            wrinkle_strength=0.09,
            stretch_highlight=0.04,
            fold_frequency=0.5,
            wrinkle_persistence=0.5,
            fabric_thickness=0.5,
            micro_shadow_strength=0.3,
        )


@dataclass
class _Collider:
    kind: str  # "circle" | "capsule"
    a: np.ndarray  # shape (2,)
    b: Optional[np.ndarray] = None  # capsule endpoint
    radius: float = 1.0


def _shoulder_width_px(pose: PoseResult) -> float:
    if not pose.success:
        return 120.0
    ls = pose.landmarks.get("left_shoulder")
    rs = pose.landmarks.get("right_shoulder")
    if not ls or not rs:
        return 120.0
    return float(max(48.0, abs(rs[0] - ls[0])))


def build_body_colliders(pose: PoseResult, w: int, h: int) -> List[_Collider]:
    """
    Simplified 2D colliders: chest capsule, shoulder spheres, arm cylinders (capsules).
    Coordinates match try-on image space (pixels).
    """
    colliders: List[_Collider] = []
    sw = _shoulder_width_px(pose)
    r_torso = max(22.0, sw * 0.24)
    r_shoulder = max(14.0, sw * 0.14)
    r_arm = max(10.0, sw * 0.09)

    if not pose.success or not pose.landmarks:
        cx, cy = w * 0.5, h * 0.42
        colliders.append(_Collider("circle", np.array([cx, cy], dtype=np.float64), None, r_torso * 1.2))
        return colliders

    lm = pose.landmarks
    ls = lm.get("left_shoulder", (w * 0.35, h * 0.25, 1.0))
    rs = lm.get("right_shoulder", (w * 0.65, h * 0.25, 1.0))
    lh = lm.get("left_hip", (w * 0.38, h * 0.56, 1.0))
    rh = lm.get("right_hip", (w * 0.62, h * 0.56, 1.0))
    le = lm.get("left_elbow", (ls[0] - sw * 0.15, ls[1] + sw * 0.35, 0.5))
    re = lm.get("right_elbow", (rs[0] + sw * 0.15, rs[1] + sw * 0.35, 0.5))

    mid_s = np.array([(ls[0] + rs[0]) * 0.5, (ls[1] + rs[1]) * 0.5], dtype=np.float64)
    mid_h = np.array([(lh[0] + rh[0]) * 0.5, (lh[1] + rh[1]) * 0.5], dtype=np.float64)
    colliders.append(_Collider("capsule", mid_s, mid_h, r_torso))

    colliders.append(_Collider("circle", np.array([ls[0], ls[1]], dtype=np.float64), None, r_shoulder))
    colliders.append(_Collider("circle", np.array([rs[0], rs[1]], dtype=np.float64), None, r_shoulder))

    colliders.append(
        _Collider(
            "capsule",
            np.array([ls[0], ls[1]], dtype=np.float64),
            np.array([le[0], le[1]], dtype=np.float64),
            r_arm,
        )
    )
    colliders.append(
        _Collider(
            "capsule",
            np.array([rs[0], rs[1]], dtype=np.float64),
            np.array([re[0], re[1]], dtype=np.float64),
            r_arm,
        )
    )
    return colliders


def _closest_on_segment(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    t = float(np.dot(p - a, ab) / (float(np.dot(ab, ab)) + 1e-12))
    t = max(0.0, min(1.0, t))
    return a + t * ab


def _project_out_circle(p: np.ndarray, c: np.ndarray, r: float, margin: float) -> None:
    d = p - c
    dist = float(np.linalg.norm(d))
    rr = r + margin
    if dist < rr and dist > 1e-8:
        p[:] = c + d * (rr / dist)
    elif dist <= 1e-8:
        p[:] = c + np.array([rr, 0.0], dtype=np.float64)


def _project_out_capsule(p: np.ndarray, a: np.ndarray, b: np.ndarray, r: float, margin: float) -> None:
    c = _closest_on_segment(p, a, b)
    _project_out_circle(p, c, r, margin)


def _collide_point(p: np.ndarray, colliders: List[_Collider], margin: float) -> None:
    for col in colliders:
        if col.kind == "circle":
            _project_out_circle(p, col.a, col.radius, margin)
        elif col.kind == "capsule" and col.b is not None:
            _project_out_capsule(p, col.a, col.b, col.radius, margin)


def _quad_point(quad: np.ndarray, u: float, v: float) -> np.ndarray:
    tl, tr, br, bl = quad[0], quad[1], quad[2], quad[3]
    top = (1.0 - u) * tl + u * tr
    bot = (1.0 - u) * bl + u * br
    return (1.0 - v) * top + v * bot


def _eval_bilinear(quad: np.ndarray, u: float, v: float) -> np.ndarray:
    return _quad_point(quad, u, v)


def _newton_inverse(target: np.ndarray, quad: np.ndarray, u0: float = 0.5, v0: float = 0.5) -> Tuple[float, float]:
    u, v = float(u0), float(v0)
    for _ in range(12):
        p = _eval_bilinear(quad, u, v)
        err = target - p
        if float(np.linalg.norm(err)) < 0.2:
            break
        eps = 1e-3
        pu = (_eval_bilinear(quad, u + eps, v) - _eval_bilinear(quad, u - eps, v)) / (2 * eps)
        pv = (_eval_bilinear(quad, u, v + eps) - _eval_bilinear(quad, u, v - eps)) / (2 * eps)
        J = np.stack([pu, pv], axis=1)
        try:
            delta = np.linalg.solve(J, err)
        except np.linalg.LinAlgError:
            break
        u = float(np.clip(u + delta[0], 0.0, 1.0))
        v = float(np.clip(v + delta[1], 0.0, 1.0))
    return u, v


def _point_in_quad(px: float, py: float, quad: np.ndarray) -> bool:
    cnt = quad.astype(np.float32).reshape(-1, 1, 2)
    return cv2.pointPolygonTest(cnt, (float(px), float(py)), False) >= 0


def _build_initial_positions(
    dst_quad: np.ndarray, nu: int, nv: int, gw: int, gh: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns:
        pos: (nv+1, nu+1, 2) output space
        uv_u, uv_v: garment pixel coords for each vertex
    """
    pos = np.zeros((nv + 1, nu + 1, 2), dtype=np.float64)
    uv_u = np.zeros((nv + 1, nu + 1), dtype=np.float64)
    uv_v = np.zeros((nv + 1, nu + 1), dtype=np.float64)
    for j in range(nv + 1):
        v = j / max(nv, 1)
        for i in range(nu + 1):
            u = i / max(nu, 1)
            uv_u[j, i] = u * (gw - 1)
            uv_v[j, i] = v * (gh - 1)
            pos[j, i] = _quad_point(dst_quad.astype(np.float64), u, v)
    return pos, uv_u, uv_v


def _rest_lengths(pos: np.ndarray) -> Dict[str, np.ndarray]:
    """Structural, shear, and bend rest lengths."""
    nu1, nv1 = pos.shape[1], pos.shape[0]
    # horizontal
    h = np.linalg.norm(pos[:, 1:, :] - pos[:, :-1, :], axis=2)
    # vertical
    ve = np.linalg.norm(pos[1:, :, :] - pos[:-1, :, :], axis=2)
    # shear diagonals
    d1 = np.linalg.norm(pos[1:, 1:, :] - pos[:-1, :-1, :], axis=2)
    d2 = np.linalg.norm(pos[:-1, 1:, :] - pos[1:, :-1, :], axis=2)
    # bend (skip-one)
    bh = np.linalg.norm(pos[:, 2:, :] - pos[:, :-2, :], axis=2) if nu1 > 2 else np.zeros((nv1, max(0, nu1 - 2)))
    bv = np.linalg.norm(pos[2:, :, :] - pos[:-2, :, :], axis=2) if nv1 > 2 else np.zeros((max(0, nv1 - 2), nu1))
    return {"h": h, "v": ve, "d1": d1, "d2": d2, "bh": bh, "bv": bv}


def _solve_distance(
    a: np.ndarray,
    b: np.ndarray,
    rest: float,
    stiff: float,
    pin_a: bool,
    pin_b: bool,
) -> None:
    if pin_a and pin_b:
        return
    delta = b - a
    dist = float(np.linalg.norm(delta)) + 1e-8
    err = (dist - rest) / dist
    corr = delta * err * stiff * 0.5
    wa = 0.0 if pin_a else 1.0
    wb = 0.0 if pin_b else 1.0
    wsum = wa + wb + 1e-8
    if not pin_a:
        a += corr * (wa / wsum)
    if not pin_b:
        b -= corr * (wb / wsum)


def _simulate_pbd_fixed(
    pos: np.ndarray,
    pos_pin: np.ndarray,
    rest: Dict[str, np.ndarray],
    colliders: List[_Collider],
    cfg: FabricConfig,
    pin_top_row: bool,
) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (final positions, per-vertex tension proxy)."""
    nu1, nv1 = pos.shape[1], pos.shape[0]
    pin = np.zeros((nv1, nu1), dtype=bool)
    if pin_top_row:
        pin[0, :] = True

    p = pos.copy()
    vel = np.zeros_like(p)
    tension_acc = np.zeros((nv1, nu1), dtype=np.float64)

    h_rest, v_rest = rest["h"], rest["v"]
    d1r, d2r = rest["d1"], rest["d2"]
    bhr, bvr = rest["bh"], rest["bv"]

    for it in range(cfg.iterations):
        g = cfg.gravity_px * (cfg.fabric_mass / max(1.0, nv1 / 22.0))
        vel[:, :, 1] += g * 0.55
        vel *= cfg.drag
        p += vel

        if pin_top_row:
            p[0, :, :] = pos_pin[0, :, :]
            vel[0, :, :] = 0.0

        # Stretch: horizontal
        for j in range(nv1):
            for i in range(nu1 - 1):
                _solve_distance(
                    p[j, i],
                    p[j, i + 1],
                    float(h_rest[j, i]),
                    cfg.stretch_stiffness,
                    bool(pin[j, i]),
                    bool(pin[j, i + 1]),
                )
        # Stretch: vertical
        for j in range(nv1 - 1):
            for i in range(nu1):
                _solve_distance(
                    p[j, i],
                    p[j + 1, i],
                    float(v_rest[j, i]),
                    cfg.stretch_stiffness,
                    bool(pin[j, i]),
                    bool(pin[j + 1, i]),
                )
        # Shear
        for j in range(nv1 - 1):
            for i in range(nu1 - 1):
                _solve_distance(
                    p[j, i],
                    p[j + 1, i + 1],
                    float(d1r[j, i]),
                    cfg.shear_stiffness,
                    bool(pin[j, i]),
                    bool(pin[j + 1, i + 1]),
                )
                _solve_distance(
                    p[j + 1, i],
                    p[j, i + 1],
                    float(d2r[j, i]),
                    cfg.shear_stiffness,
                    bool(pin[j + 1, i]),
                    bool(pin[j, i + 1]),
                )
        # Bending
        if nu1 > 2:
            for j in range(nv1):
                for i in range(nu1 - 2):
                    _solve_distance(
                        p[j, i],
                        p[j, i + 2],
                        float(bhr[j, i]),
                        cfg.bend_stiffness,
                        bool(pin[j, i]),
                        bool(pin[j, i + 2]),
                    )
        if nv1 > 2:
            for j in range(nv1 - 2):
                for i in range(nu1):
                    _solve_distance(
                        p[j, i],
                        p[j + 2, i],
                        float(bvr[j, i]),
                        cfg.bend_stiffness,
                        bool(pin[j, i]),
                        bool(pin[j + 2, i]),
                    )

        # Collisions (fabric must not intersect body primitives)
        for j in range(nv1):
            for i in range(nu1):
                if pin[j, i]:
                    continue
                for col in colliders:
                    if col.kind == "circle":
                        _project_out_circle(p[j, i], col.a, col.radius, cfg.collision_margin)
                    elif col.kind == "capsule" and col.b is not None:
                        _project_out_capsule(p[j, i], col.a, col.b, col.radius, cfg.collision_margin)

        if pin_top_row:
            p[0, :, :] = pos_pin[0, :, :]

    # Tension map from stretch ratio (horizontal + vertical)
    for j in range(nv1):
        for i in range(nu1 - 1):
            L = float(np.linalg.norm(p[j, i + 1] - p[j, i])) + 1e-8
            tension_acc[j, i] += max(0.0, L / (float(h_rest[j, i]) + 1e-8) - 1.0)
        for i in range(nu1):
            if j < nv1 - 1:
                L = float(np.linalg.norm(p[j + 1, i] - p[j, i])) + 1e-8
                tension_acc[j, i] += max(0.0, L / (float(v_rest[j, i]) + 1e-8) - 1.0)
    tension = np.clip(tension_acc * 0.5, 0.0, 2.5)
    return p, tension


def _rasterize_deformed_garment(
    rgba: np.ndarray,
    pos: np.ndarray,
    uv_u: np.ndarray,
    uv_v: np.ndarray,
    tension_v: np.ndarray,
    out_wh: Tuple[int, int],
    step: int = 6,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Inverse-map rasterization via coarse remap + tension at sample points.
    Returns (warped_rgba, tension_full_res).
    """
    ow, oh = out_wh
    nu1, nv1 = pos.shape[1], pos.shape[0]

    coarse_w = max(2, ow // step)
    coarse_h = max(2, oh // step)
    map_x = np.zeros((coarse_h, coarse_w), dtype=np.float32)
    map_y = np.zeros((coarse_h, coarse_w), dtype=np.float32)
    ten_s = np.zeros((coarse_h, coarse_w), dtype=np.float32)

    # Precompute per-vertex tension samples (reuse from caller) — here approximate 0 on coarse grid
    for cy in range(coarse_h):
        py = (cy + 0.5) / coarse_h * oh
        for cx in range(coarse_w):
            px = (cx + 0.5) / coarse_w * ow
            found = False
            for j in range(nv1 - 1):
                for i in range(nu1 - 1):
                    q_out = np.stack(
                        [
                            pos[j, i],
                            pos[j, i + 1],
                            pos[j + 1, i + 1],
                            pos[j + 1, i],
                        ],
                        axis=0,
                    ).astype(np.float64)
                    xmin, xmax = float(q_out[:, 0].min()), float(q_out[:, 0].max())
                    ymin, ymax = float(q_out[:, 1].min()), float(q_out[:, 1].max())
                    if px < xmin - 3 or px > xmax + 3 or py < ymin - 3 or py > ymax + 3:
                        continue
                    if not _point_in_quad(px, py, q_out):
                        continue
                    q_uv = np.stack(
                        [
                            [uv_u[j, i], uv_v[j, i]],
                            [uv_u[j, i + 1], uv_v[j, i + 1]],
                            [uv_u[j + 1, i + 1], uv_v[j + 1, i + 1]],
                            [uv_u[j + 1, i], uv_v[j + 1, i]],
                        ],
                        axis=0,
                    ).astype(np.float64)
                    uu, vv = _newton_inverse(np.array([px, py], dtype=np.float64), q_out, 0.5, 0.5)
                    gu = (1 - uu) * (1 - vv) * q_uv[0, 0] + uu * (1 - vv) * q_uv[1, 0] + uu * vv * q_uv[2, 0] + (1 - uu) * vv * q_uv[3, 0]
                    gv = (1 - uu) * (1 - vv) * q_uv[0, 1] + uu * (1 - vv) * q_uv[1, 1] + uu * vv * q_uv[2, 1] + (1 - uu) * vv * q_uv[3, 1]
                    map_x[cy, cx] = float(gu)
                    map_y[cy, cx] = float(gv)
                    ten_s[cy, cx] = float(
                        (1 - uu) * (1 - vv) * tension_v[j, i]
                        + uu * (1 - vv) * tension_v[j, i + 1]
                        + uu * vv * tension_v[j + 1, i + 1]
                        + (1 - uu) * vv * tension_v[j + 1, i]
                    )
                    found = True
                    break
                if found:
                    break
            if not found:
                map_x[cy, cx] = -1.0
                map_y[cy, cx] = -1.0

    map_x_full = cv2.resize(map_x, (ow, oh), interpolation=cv2.INTER_LINEAR)
    map_y_full = cv2.resize(map_y, (ow, oh), interpolation=cv2.INTER_LINEAR)
    ten_full = cv2.resize(ten_s, (ow, oh), interpolation=cv2.INTER_LINEAR)

    warped = cv2.remap(
        rgba,
        map_x_full,
        map_y_full,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return warped, ten_full


def _apply_tension_appearance(rgba: np.ndarray, tension: np.ndarray, cfg: FabricConfig) -> np.ndarray:
    """High tension → slight highlight; low tension → micro-contrast (wrinkles).
    
    CONFIT Fabric Intelligence Shading:
    - Adjust specular reflection based on fabric type
    - Apply micro-shadows in fold areas
    - Simulate fabric thickness via edge darkening
    """
    t = cv2.GaussianBlur(tension.astype(np.float32), (0, 0), sigmaX=2.5, sigmaY=2.5)
    p95 = float(np.percentile(t, 95)) if t.size else 1.0
    t = np.clip(t / (p95 + 1e-6), 0.0, 1.5)
    stretch = np.clip(t, 0.0, 1.0)
    wrinkle = np.clip(1.0 - t, 0.0, 1.0)
    rgb = rgba[:, :, :3].astype(np.float32)
    
    # Generate noise for wrinkle texture
    noise = cv2.GaussianBlur(
        (np.random.RandomState(42).rand(*rgb.shape[:2]).astype(np.float32) - 0.5) * 2.0,
        (3, 3),
        0,
    )
    
    # Stretch highlights (brighter on stretched areas)
    fac_stretch = 1.0 + cfg.stretch_highlight * stretch[..., None]
    
    # Wrinkle darkening (darker in wrinkle areas)
    wrinkle_intensity = cfg.wrinkle_strength * (0.35 + 0.2 * noise[..., None])
    # Apply fold frequency - more folds = more variation
    wrinkle_intensity *= (0.7 + cfg.fold_frequency * 0.6)
    fac_wrinkle = 1.0 - wrinkle[..., None] * wrinkle_intensity
    
    # Micro-shadows in fold areas (CONFIT enhancement)
    if cfg.micro_shadow_strength > 0.1:
        # Create shadow map from wrinkle pattern
        shadow_kernel = max(3, int(5 + cfg.fabric_thickness * 4))
        shadow_noise = cv2.GaussianBlur(noise, (shadow_kernel, shadow_kernel), 0)
        shadow_mask = wrinkle * (shadow_noise * 0.5 + 0.5) * cfg.micro_shadow_strength
        # Apply shadows - darker in fold valleys
        shadow_factor = 1.0 - shadow_mask[..., None] * 0.15
        rgb = rgb * shadow_factor
    
    # Apply stretch and wrinkle effects
    rgb = rgb * fac_stretch * fac_wrinkle
    
    # Fabric thickness simulation - subtle edge darkening for thick fabrics
    if cfg.fabric_thickness > 0.6:
        # Darken slightly for thick fabrics (wool, leather)
        thickness_darken = 1.0 - (cfg.fabric_thickness - 0.6) * 0.08
        rgb = rgb * thickness_darken
    elif cfg.fabric_thickness < 0.3:
        # Slightly brighter for thin fabrics (silk)
        thickness_brighten = 1.0 + (0.3 - cfg.fabric_thickness) * 0.05
        rgb = rgb * thickness_brighten
    
    rgb = np.clip(rgb, 0.0, 255.0)
    out = rgba.copy()
    out[:, :, :3] = rgb.astype(np.uint8)
    return out


def _struct_pack_f64(x: float) -> bytes:
    return struct.pack("<d", float(x))


def _cache_key(
    dst_quad: np.ndarray,
    rgba: np.ndarray,
    cfg: FabricConfig,
    pose: PoseResult,
    material_tag: str = "",
) -> str:
    h = hashlib.sha256()
    h.update(dst_quad.astype(np.float32).tobytes())
    h.update(rgba[:32, :32, :].tobytes())
    h.update(str(cfg.grid_u).encode())
    h.update(str(cfg.grid_v).encode())
    h.update(str(cfg.iterations).encode())
    h.update(material_tag.encode())
    sw = _shoulder_width_px(pose)
    h.update(_struct_pack_f64(sw))
    return h.hexdigest()[:32]


def _fabric_config_from_material(
    base: FabricConfig,
    material: Optional["MaterialProperties"],
) -> FabricConfig:
    """Adaptive warping (Step 3): soft fabrics → smoother curvature; rigid → limited bending.
    
    CONFIT Fabric Intelligence:
    - Cotton → soft folds, medium gravity
    - Denim → rigid deformation limits
    - Wool → volume preservation
    - Leather → minimal folding, strong highlights
    - Silk → high flow dynamics
    """
    if material is None:
        return base
    m = material
    # Higher stretch stiffness → less unrealistic elongation (denim, leather)
    stretch_guard = float(np.clip(1.08 / max(0.92, m.max_stretch_ratio), 0.85, 1.25))
    
    # Adjust grid resolution based on fabric thickness and fold frequency
    # Thicker fabrics with fewer folds need lower resolution
    thickness_factor = 1.0 - (m.fabric_thickness - 0.5) * 0.15
    fold_factor = 1.0 + (m.fold_frequency - 0.5) * 0.1
    grid_multiplier = thickness_factor * fold_factor
    
    # Adjust iterations based on wrinkle persistence
    # Higher persistence needs more iterations for stable wrinkles
    iter_adjust = int(round(base.iterations * (0.9 + m.wrinkle_persistence * 0.2)))
    
    return FabricConfig(
        grid_u=max(12, int(round(base.grid_u * grid_multiplier))),
        grid_v=max(16, int(round(base.grid_v * grid_multiplier))),
        iterations=max(12, min(48, iter_adjust)),
        stretch_stiffness=float(np.clip(base.stretch_stiffness * m.stretch_stiffness_scale * stretch_guard, 0.55, 0.98)),
        bend_stiffness=float(np.clip(base.bend_stiffness * m.bend_stiffness_scale, 0.12, 0.62)),
        shear_stiffness=float(np.clip(base.shear_stiffness * m.shear_scale, 0.2, 0.65)),
        gravity_px=float(np.clip(base.gravity_px * m.gravity_scale, 0.22, 0.62)),
        drag=base.drag,
        fabric_mass=base.fabric_mass,
        collision_margin=base.collision_margin,
        wrinkle_strength=float(np.clip(base.wrinkle_strength * m.wrinkle_strength_scale, 0.04, 0.22)),
        stretch_highlight=float(np.clip(base.stretch_highlight * m.stretch_highlight_scale, 0.02, 0.12)),
        # CONFIT extended properties
        fold_frequency=m.fold_frequency,
        wrinkle_persistence=m.wrinkle_persistence,
        fabric_thickness=m.fabric_thickness,
        micro_shadow_strength=m.micro_shadow_strength,
    )


def apply_fabric_physics_to_warp(
    g_rgba: np.ndarray,
    dst_quad: np.ndarray,
    pose: PoseResult,
    out_wh: Tuple[int, int],
    *,
    low_power: bool = False,
    material: Optional["MaterialProperties"] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Run fabric PBD on a garment grid and re-rasterize into output space.

    Args:
        g_rgba: Garment RGBA (uint8)
        dst_quad: 4x2 TL,TR,BR,BL in output pixels
        pose: PoseResult for colliders
        out_wh: (width, height) output canvas
        material: Optional fabric material profile (adaptive stiffness / wrinkle / highlights).

    Returns:
        (warped_rgba, debug_meta)
    """
    base_cfg = FabricConfig.lightweight() if low_power else FabricConfig.full()
    cfg = _fabric_config_from_material(base_cfg, material)
    gh, gw = g_rgba.shape[:2]
    nu, nv = cfg.grid_u, cfg.grid_v

    mat_tag = ""
    if material is not None:
        mat_tag = f"{material.fabric.value}:{material.bend_stiffness_scale:.3f}:{material.stretch_stiffness_scale:.3f}"
    key = _cache_key(dst_quad, g_rgba, cfg, pose, material_tag=mat_tag)
    if key in _MESH_CACHE:
        logger.debug("fabric mesh cache hit %s", key[:12])
        return _MESH_CACHE[key], {
            "fabricPhysics": "cached",
            "cacheKey": key,
            "fabricType": material.fabric.value if material is not None else None,
        }

    pos0, uv_u, uv_v = _build_initial_positions(dst_quad.astype(np.float64), nu, nv, gw, gh)
    pos_pin = pos0.copy()
    rest = _rest_lengths(pos0)
    colliders = build_body_colliders(pose, out_wh[0], out_wh[1])
    p_final, tension_v = _simulate_pbd_fixed(pos0, pos_pin, rest, colliders, cfg, pin_top_row=True)

    # Rasterize deformed mesh (inverse UV map + tension field)
    warped, ten_full = _rasterize_deformed_garment(
        g_rgba, p_final, uv_u, uv_v, tension_v, out_wh, step=18 if low_power else 14
    )
    warped = _apply_tension_appearance(warped, ten_full, cfg)

    # Cache
    if len(_MESH_CACHE) >= _MAX_MESH_CACHE:
        old = _MESH_CACHE_ORDER.pop(0)
        _MESH_CACHE.pop(old, None)
    _MESH_CACHE[key] = warped
    _MESH_CACHE_ORDER.append(key)

    meta: Dict[str, Any] = {
        "fabricPhysics": "pbd",
        "grid": [nu, nv],
        "iterations": cfg.iterations,
        "lowPower": bool(low_power),
        "colliders": len(colliders),
        "cacheKey": key,
        "fabricType": material.fabric.value if material is not None else None,
        "materialStiffness": getattr(material, "stiffness", None) if material is not None else None,
    }
    return warped, meta

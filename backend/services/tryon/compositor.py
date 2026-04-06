from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TorsoLightingStats:
    brightness: float
    contrast: float
    color_temperature: float


def extract_torso_lighting_stats(person_rgb: np.ndarray, torso_mask_u8: np.ndarray) -> TorsoLightingStats:
    m = torso_mask_u8 > 80
    if not np.any(m):
        gray = np.mean(person_rgb, axis=2)
        return TorsoLightingStats(
            brightness=float(np.mean(gray) / 255.0),
            contrast=float(np.std(gray) / 128.0),
            color_temperature=0.5,
        )
    torso_pixels = person_rgb[m]
    gray = np.mean(torso_pixels, axis=1)
    r = float(np.mean(torso_pixels[:, 0]))
    b = float(np.mean(torso_pixels[:, 2]))
    return TorsoLightingStats(
        brightness=float(np.mean(gray) / 255.0),
        contrast=float(np.std(gray) / 128.0),
        color_temperature=float((r - b) / (r + b + 1e-6) * 0.5 + 0.5),
    )


def match_garment_to_torso_lighting(garment_rgba: np.ndarray, stats: TorsoLightingStats) -> np.ndarray:
    out = garment_rgba.copy().astype(np.float32)
    alpha = out[:, :, 3] > 8
    if not np.any(alpha):
        return garment_rgba

    rgb = out[:, :, :3]
    current_brightness = float(np.mean(np.mean(rgb[alpha], axis=1)))
    target = stats.brightness * 255.0
    brightness_factor = float(np.clip(target / (current_brightness + 1e-6), 0.65, 1.45))
    rgb *= brightness_factor

    if stats.color_temperature > 0.55:
        rgb[:, :, 0] *= 1.03
        rgb[:, :, 1] *= 1.01
    elif stats.color_temperature < 0.45:
        rgb[:, :, 2] *= 1.03

    if stats.contrast > 0.6:
        mean = np.mean(rgb[alpha], axis=0)
        rgb = mean + (rgb - mean) * float(np.clip(1.0 + (stats.contrast - 0.5) * 0.2, 1.0, 1.2))

    out[:, :, :3] = np.clip(rgb, 0, 255)
    return out.astype(np.uint8)

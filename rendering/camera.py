"""
Camera state management and oversized board detection.
Coordinates dual-mode display (Panoramic Overview vs. Focused Tracking).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from core.models import Level


class CameraMode(str, Enum):
    PANORAMIC = "PANORAMIC"
    FOCUSED = "FOCUSED"


def is_level_oversized(
    level: Level,
    avail_w: int,
    avail_h: int,
    is_3d: bool = False,
) -> bool:
    """Returns True if the level requires tile downscaling to fit inside the given canvas."""
    all_cells = set(level.tiles.keys())
    for b_tiles in level.bridges.values():
        all_cells.update(b_tiles)
    if not all_cells:
        all_cells = {(r, c) for r in range(max(1, level.height)) for c in range(max(1, level.width))}

    if is_3d:
        min_u = min(c - r - 1 for r, c in all_cells)
        max_u = max(c - r + 1 for r, c in all_cells)
        min_v = min(c + r for r, c in all_cells)
        max_v = max(c + r + 2 for r, c in all_cells)
        delta_u = max(1, max_u - min_u)
        delta_v = max(1, max_v - min_v)

        fit_w = avail_w / (delta_u * 0.5)
        fit_h = avail_h / (delta_v * 0.25 + 1.35)
        return int(min(fit_w, fit_h)) < settings.TILE_SIZE
    else:
        min_r = min(r for r, c in all_cells)
        max_r = max(r for r, c in all_cells)
        min_c = min(c for r, c in all_cells)
        max_c = max(c for r, c in all_cells)
        span_r = max(1, max_r - min_r + 1)
        span_c = max(1, max_c - min_c + 1)

        fit_w = avail_w // span_c
        fit_h = avail_h // span_r
        return min(fit_w, fit_h) < settings.TILE_SIZE


class CameraState:
    """Manages viewport camera mode, coordinate offsets, and exponential smoothing."""

    def __init__(self, mode: CameraMode = CameraMode.PANORAMIC, speed: float = 12.0):
        self.mode = mode
        self.pos = [0.0, 0.0]
        self.target_pos = [0.0, 0.0]
        self.speed = speed

    def snap_to_target(self) -> None:
        """Immediately snaps position to target coordinates with zero delay."""
        self.pos[0] = float(self.target_pos[0])
        self.pos[1] = float(self.target_pos[1])

    def update(self, dt: float) -> None:
        """Smoothly moves pos toward target_pos using frame-rate independent exponential smoothing."""
        if dt <= 0:
            return
        factor = 1.0 - math.exp(-max(0.0, self.speed * dt))
        self.pos[0] += (self.target_pos[0] - self.pos[0]) * factor
        self.pos[1] += (self.target_pos[1] - self.pos[1]) * factor

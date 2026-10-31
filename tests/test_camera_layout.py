import pygame
import pytest
from config import settings
from levels.level_loader import load_level
from rendering.board_renderer import BoardRenderer
from rendering.camera import CameraMode, CameraState, is_level_oversized


def test_2d_active_cell_bounding_eliminates_negative_origin():
    level_11 = load_level("levels/level_11.json")
    renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
    origin_x, origin_y, tile_size = renderer.compute_layout(level_11)

    # Origin x must NOT be negative (previously -226 due to empty grid span)
    assert origin_x >= 0
    assert origin_y >= 0
    assert tile_size >= 12


def test_oversized_detection_contract():
    level_1 = load_level("levels/level_01.json")
    level_11 = load_level("levels/level_11.json")
    avail_w = settings.BOARD_AREA_WIDTH - 2 * settings.BOARD_MARGIN
    avail_h = settings.BOARD_AREA_HEIGHT - 2 * settings.BOARD_MARGIN

    # Standard level does NOT exceed standard scale
    assert is_level_oversized(level_1, avail_w, avail_h, is_3d=False) is False
    assert is_level_oversized(level_1, avail_w, avail_h, is_3d=True) is False

    # Stage 11 exceeds standard scale in both views
    assert is_level_oversized(level_11, avail_w, avail_h, is_3d=False) is True
    assert is_level_oversized(level_11, avail_w, avail_h, is_3d=True) is True


def test_camera_state_lerp():
    cam = CameraState(mode=CameraMode.FOCUSED, speed=10.0)
    cam.pos = [0.0, 0.0]
    cam.target_pos = [100.0, 200.0]
    cam.update(0.1)
    assert 0.0 < cam.pos[0] < 100.0
    assert 0.0 < cam.pos[1] < 200.0

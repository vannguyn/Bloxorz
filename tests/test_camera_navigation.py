import pygame
pygame.font.init()

from config import settings
from levels.level_loader import load_level
from rendering.camera import CameraMode
from ui.game_screen import GameScreen


def test_standard_level_disables_camera_toggle():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level("levels/level_01.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)

    assert screen.btn_camera_toggle.enabled is False
    assert screen.camera.mode == CameraMode.PANORAMIC

    # Pressing Z or clicking must be a no-op
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    assert screen.camera.mode == CameraMode.PANORAMIC


def test_oversized_level_enables_toggle_and_starts_panoramic():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)

    # Initial state is Panoramic
    assert screen.btn_camera_toggle.enabled is True
    assert screen.camera.mode == CameraMode.PANORAMIC

    # Toggle with Z key
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))
    assert screen.camera.mode == CameraMode.FOCUSED

    # Toggle back with click
    screen.btn_camera_toggle.callback()
    assert screen.camera.mode == CameraMode.PANORAMIC


def test_viewport_clipping_protects_sidebar():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)
    screen.camera.mode = CameraMode.FOCUSED
    screen.draw()

    # Verify sidebar background is preserved
    sidebar_sample = surface.get_at((settings.BOARD_AREA_WIDTH + 20, 20))[:3]
    assert sidebar_sample == settings.COLOR_PANEL_BG

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


def test_split_cube_camera_target_switch():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)
    screen.camera.mode = CameraMode.FOCUSED

    from core.interfaces import BlockState, GameState, Orientation
    # Set split state with distinct positions
    split_block = BlockState(
        r=5,
        c=5,
        orientation=Orientation.STANDING,
        is_split=True,
        cube_positions=((5, 5), (5, 25)),
        active_cube=0,
    )
    screen.current_state = GameState(block=split_block, bridge_mask=0)

    target_cube1 = screen._get_camera_target_for_block()

    # Switch active cube with SPACE
    event_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    screen.handle_event(event_space)
    target_cube2 = screen._get_camera_target_for_block()

    assert screen.current_state.block.active_cube == 1
    assert target_cube1 != target_cube2
    # Verify delta aligns with cube displacement: cube2 (5, 25) vs cube1 (5, 5)
    assert target_cube2[0] < target_cube1[0]  # c=25 is farther right, so camera shifts left (more negative)
    assert target_cube2[1] == target_cube1[1]  # r=5 is same row, so y target unchanged


def test_split_cube_camera_target_switch_3d():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)
    screen.view_mode = "3D"
    screen.camera.mode = CameraMode.FOCUSED

    from core.interfaces import BlockState, GameState, Orientation
    split_block = BlockState(
        r=5,
        c=5,
        orientation=Orientation.STANDING,
        is_split=True,
        cube_positions=((5, 5), (5, 25)),
        active_cube=0,
    )
    screen.current_state = GameState(block=split_block, bridge_mask=0)

    target_cube1 = screen._get_camera_target_for_block()
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    target_cube2 = screen._get_camera_target_for_block()

    assert screen.current_state.block.active_cube == 1
    assert target_cube1 != target_cube2


def test_replay_playback_updates_camera_target():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    levels = [load_level("levels/level_11.json")]
    screen = GameScreen(surface, levels=levels)
    screen.load_level(0)
    screen.camera.mode = CameraMode.FOCUSED
    screen._update_camera_target()
    initial_target = tuple(screen.camera.target_pos)

    # Move block right
    screen.handle_manual_move("R")
    screen.update(0.016)
    new_target = tuple(screen.camera.target_pos)

    assert new_target != initial_target
    assert new_target[0] < initial_target[0]  # block moved right, camera target shifted left

"""
Headless Smoke Tests for Bloxorz GUI, Rendering, and Solver Bridge.
Runs without a physical display using SDL_VIDEODRIVER=dummy.
"""
from __future__ import annotations

import os
import time
import pytest

# Enforce dummy video driver before pygame is initialized
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from config import settings
from core.interfaces import Orientation
from rendering.board_renderer import BoardRenderer
from rendering.block_renderer import BlockRenderer
from rendering.animation import SolutionReplayer
from ui.button import Button
from ui.game_screen import GameScreen
from ui.result_screen import ResultOverlay
from ui.solver_bridge import on_solve, AsyncSolverBridge, SolverBridgeState
from tests.mocks import (
    mock_level_simple,
    mock_level_with_fragile,
    mock_level_with_bridge,
    mock_level_split,
)


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    pygame.font.init()
    yield
    pygame.quit()


def test_headless_game_initialization():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    assert game_screen.surface.get_size() == (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
    assert len(game_screen.levels) >= 4
    assert game_screen.current_state.block.orientation == Orientation.STANDING


def test_render_all_mock_levels():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)

    # Render each mock level to ensure board & block renderers handle all tile types
    for idx in range(len(game_screen.levels)):
        game_screen.load_level(idx)
        game_screen.update(0.016)
        game_screen.draw()
        # Verify surface is not empty (contains rendered colors)
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_manual_input_movement():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    game_screen.load_level(0)  # Simple corridor

    start_pos = (game_screen.current_state.block.r, game_screen.current_state.block.c)
    assert game_screen.moves_count == 0

    # Simulate pressing Right arrow
    event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    game_screen.handle_event(event_right)
    game_screen.update(0.016)

    assert game_screen.moves_count == 1
    assert game_screen.current_state.block.orientation == Orientation.LYING_H
    assert game_screen.current_state.block.c == start_pos[1] + 1


def test_split_level_and_space_key():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    # Mock level 3 is split level
    game_screen.load_level(3)
    assert game_screen.current_state.block.is_split is True
    assert game_screen.current_state.block.active_cube == 0

    # Press SPACE to toggle active cube
    event_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    game_screen.handle_event(event_space)
    game_screen.update(0.016)

    assert game_screen.current_state.block.active_cube == 1


def test_sync_solver_bridge_contract():
    level = mock_level_simple()
    state = level.start
    result = on_solve("BFS", level, state)

    assert result.success is True
    assert result.path == ["R", "R", "R", "R"]
    assert result.expanded_nodes > 0
    assert result.search_time_ms >= 0
    assert result.peak_memory_kb >= 0


def test_async_solver_bridge_and_replayer():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    game_screen.load_level(0)

    # Trigger async BFS solve
    game_screen.trigger_solve("BFS")
    assert game_screen.solver_bridge.state == SolverBridgeState.RUNNING

    # Poll until worker completes (mock completes instantly, poll with timeout)
    t0 = time.time()
    while game_screen.solver_bridge.state == SolverBridgeState.RUNNING and (time.time() - t0) < 3.0:
        game_screen.update(0.05)
        time.sleep(0.02)

    assert game_screen.solver_bridge.state == SolverBridgeState.FINISHED
    assert game_screen.latest_result is not None
    assert game_screen.replayer is not None
    assert game_screen.replayer.total_steps == 4

    # Test stepping forward in replay
    init_idx = game_screen.replayer.current_index
    game_screen.replay_next_step()
    assert game_screen.replayer.current_index == init_idx + 1


def test_result_overlays_rendering():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    area = pygame.Rect(0, 0, 700, 680)

    for status in ("WIN", "LOST_FALL", "LOST_FRAGILE", "UNSOLVABLE"):
        ResultOverlay.draw(surface, area, status, moves_count=5)
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_button_hover_and_click():
    clicked = []
    btn = Button((10, 10, 100, 40), "Click Me", on_click=lambda: clicked.append(True))

    # Mouse motion over button
    ev_motion = pygame.event.Event(pygame.MOUSEMOTION, pos=(50, 20))
    btn.handle_event(ev_motion)
    assert btn.is_hovered is True

    # Mouse down
    ev_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 20))
    btn.handle_event(ev_down)
    assert btn.is_pressed is True

    # Mouse up
    ev_up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(50, 20))
    btn.handle_event(ev_up)
    assert btn.is_pressed is False
    assert clicked == [True]


def test_dependencies_adapter_contract(monkeypatch):
    from ui import dependencies
    assert isinstance(dependencies.IS_MOCK_CORE, bool)
    assert isinstance(dependencies.IS_MOCK_SOLVERS, bool)
    assert dependencies.IS_MOCK_MODE == (dependencies.IS_MOCK_CORE or dependencies.IS_MOCK_SOLVERS)
    assert callable(dependencies.apply_move)
    assert callable(dependencies.is_goal)
    assert callable(dependencies.get_solver)
    assert callable(dependencies.run_solver)
    assert callable(dependencies.get_levels)
    assert len(dependencies.get_levels()) >= 4
    solver = dependencies.get_solver("BFS")
    assert solver is not None
    assert dependencies.get_mode_badge_text() in (
        "[REAL]", "[MOCK CORE]", "[MOCK SOLVERS]", "[MOCK CORE+SOLVERS]"
    )

    # Validate all 4 mode badge variations
    monkeypatch.setattr(dependencies, "IS_MOCK_CORE", False)
    monkeypatch.setattr(dependencies, "IS_MOCK_SOLVERS", False)
    assert dependencies.get_mode_badge_text() == "[REAL]"

    monkeypatch.setattr(dependencies, "IS_MOCK_CORE", True)
    monkeypatch.setattr(dependencies, "IS_MOCK_SOLVERS", False)
    assert dependencies.get_mode_badge_text() == "[MOCK CORE]"

    monkeypatch.setattr(dependencies, "IS_MOCK_CORE", False)
    monkeypatch.setattr(dependencies, "IS_MOCK_SOLVERS", True)
    assert dependencies.get_mode_badge_text() == "[MOCK SOLVERS]"

    monkeypatch.setattr(dependencies, "IS_MOCK_CORE", True)
    monkeypatch.setattr(dependencies, "IS_MOCK_SOLVERS", True)
    assert dependencies.get_mode_badge_text() == "[MOCK CORE+SOLVERS]"



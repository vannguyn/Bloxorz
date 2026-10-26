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


def _mock_levels():
    return [
        mock_level_simple(),
        mock_level_with_fragile(),
        mock_level_with_bridge(),
        mock_level_split(),
    ]


def test_headless_game_initialization():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    assert game_screen.surface.get_size() == (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
    assert len(game_screen.levels) >= 4
    assert game_screen.current_state.block.orientation == Orientation.STANDING


def test_render_all_mock_levels():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface, levels=_mock_levels())

    # Render each mock level to ensure board & block renderers handle all tile types
    for idx in range(len(game_screen.levels)):
        game_screen.load_level(idx)
        game_screen.update(0.016)
        game_screen.draw()
        # Verify surface is not empty (contains rendered colors)
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_render_all_real_levels():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    assert len(game_screen.levels) == 10

    # Render each real level to ensure board & block renderers handle all 10 levels
    for idx in range(len(game_screen.levels)):
        game_screen.load_level(idx)
        game_screen.update(0.016)
        game_screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_manual_input_movement():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface, levels=_mock_levels())
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
    game_screen = GameScreen(surface, levels=_mock_levels())
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
    game_screen = GameScreen(surface, levels=_mock_levels())
    game_screen.load_level(0)

    # Trigger async BFS solve
    game_screen.trigger_solve("BFS")
    assert game_screen.solver_bridge.state == SolverBridgeState.RUNNING

    # Poll until worker completes with real-time timeout protection and sleep
    t0 = time.time()
    while game_screen.solver_bridge.state == SolverBridgeState.RUNNING:
        game_screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out after 3.0 seconds")

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


def test_replayer_speed_control():
    from tests.mocks import mock_level_simple
    from core.interfaces import GameState
    from rendering.animation import SolutionReplayer
    level = mock_level_simple()
    state = GameState(block=level.start, bridge_mask=0)
    replayer = SolutionReplayer(level, state, ["R", "R", "R", "R"], step_delay=0.4)

    assert replayer.speed_multiplier == 1.0
    assert replayer.effective_delay == pytest.approx(0.4)

    replayer.set_speed_multiplier(2.0)
    assert replayer.speed_multiplier == 2.0
    assert replayer.effective_delay == pytest.approx(0.2)

    # Test update with drift-free accumulator
    replayer.update(0.45)
    # At delay 0.2, 0.45s should advance 2 steps (timer keeps remaining 0.05s)
    assert replayer.current_index == 2
    assert replayer.timer == pytest.approx(0.05)


def test_game_screen_speed_button_cycle_and_persistence():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)

    assert game_screen.btn_speed.enabled is True
    assert game_screen.btn_speed.text == "Speed: 1.0x"
    assert game_screen.speed_preset_idx == 1

    # Cycle speed: 1.0x -> 2.0x -> 4.0x -> 0.5x -> 1.0x
    game_screen.cycle_speed()
    assert game_screen.btn_speed.text == "Speed: 2.0x"
    assert game_screen.speed_preset_idx == 2

    game_screen.cycle_speed()
    assert game_screen.btn_speed.text == "Speed: 4.0x"
    assert game_screen.speed_preset_idx == 3

    game_screen.cycle_speed()
    assert game_screen.btn_speed.text == "Speed: 0.5x"
    assert game_screen.speed_preset_idx == 0

    # Persistence across restart and load_level
    game_screen.restart_level()
    assert game_screen.speed_preset_idx == 0
    assert game_screen.btn_speed.text == "Speed: 0.5x"

    game_screen.load_level(1)
    assert game_screen.speed_preset_idx == 0
    assert game_screen.btn_speed.text == "Speed: 0.5x"


def test_game_screen_speed_button_click_and_persistence():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    assert "1.0x" in game_screen.btn_speed.text

    # Post real mouse click on btn_speed
    click_pos = game_screen.btn_speed.rect.center
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)
    up_ev = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=click_pos)
    game_screen.handle_event(down_ev)
    game_screen.handle_event(up_ev)

    assert "2.0x" in game_screen.btn_speed.text

    # Test persistence across restart and level switch
    game_screen.restart_level()
    assert "2.0x" in game_screen.btn_speed.text

    game_screen.next_level()
    assert "2.0x" in game_screen.btn_speed.text


def test_strict_import_hygiene():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    scanned_files = []
    for folder in ("ui", "rendering"):
        for py_path in (root / folder).rglob("*.py"):
            if py_path.name == "dependencies.py":
                continue
            scanned_files.append(py_path)
            content = py_path.read_text(encoding="utf-8")
            assert "from tests.mocks" not in content, f"Direct mock import found in {py_path}"
            assert "import tests.mocks" not in content, f"Direct mock import found in {py_path}"

    assert len(scanned_files) >= 6


def test_view_mode_toggle_and_persistence():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)

    # 1. Starts with "2D" mode as default
    assert game_screen.view_mode == "2D"
    assert hasattr(game_screen, "btn_view_mode")
    assert "2D" in game_screen.btn_view_mode.text

    # 2. cycle_view_mode() switches to "3D" and updates button text
    game_screen.cycle_view_mode()
    assert game_screen.view_mode == "3D"
    assert "3D" in game_screen.btn_view_mode.text

    # 3. Pressing 'V' key toggles view mode back to "2D" then "3D"
    ev_v = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v)
    game_screen.handle_event(ev_v)
    assert game_screen.view_mode == "2D"
    assert "2D" in game_screen.btn_view_mode.text

    game_screen.handle_event(ev_v)
    assert game_screen.view_mode == "3D"
    assert "3D" in game_screen.btn_view_mode.text

    # 4. Clicking btn_view_mode via mouse event toggles back to "2D" then "3D"
    click_pos = game_screen.btn_view_mode.rect.center
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=click_pos)
    up_ev = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=click_pos)
    game_screen.handle_event(down_ev)
    game_screen.handle_event(up_ev)
    assert game_screen.view_mode == "2D"
    assert "2D" in game_screen.btn_view_mode.text

    game_screen.handle_event(down_ev)
    game_screen.handle_event(up_ev)
    assert game_screen.view_mode == "3D"
    assert "3D" in game_screen.btn_view_mode.text

    # 5. Calling restart_level() and load_level(1) preserves view_mode == "3D"
    game_screen.restart_level()
    assert game_screen.view_mode == "3D"
    assert "3D" in game_screen.btn_view_mode.text

    game_screen.load_level(1)
    assert game_screen.view_mode == "3D"
    assert "3D" in game_screen.btn_view_mode.text

    # 6. Rendering with game_screen.draw() in both "2D" and "3D" runs cleanly and produces non-empty surface pixels
    game_screen.draw()
    raw_3d = pygame.image.tobytes(surface, "RGB")
    assert any(b > 0 for b in raw_3d)

    game_screen.cycle_view_mode()
    assert game_screen.view_mode == "2D"
    game_screen.draw()
    raw_2d = pygame.image.tobytes(surface, "RGB")
    assert any(b > 0 for b in raw_2d)


def test_render_all_mock_levels_in_3d_mode():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface, levels=_mock_levels())
    game_screen.view_mode = "3D"

    # Render each mock level in 3D isometric mode
    for idx in range(len(game_screen.levels)):
        game_screen.load_level(idx)
        assert game_screen.view_mode == "3D"
        game_screen.update(0.016)
        game_screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_render_all_real_levels_in_3d_mode():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    assert len(game_screen.levels) == 10
    game_screen.view_mode = "3D"

    # Render each real level in 3D isometric mode
    for idx in range(len(game_screen.levels)):
        game_screen.load_level(idx)
        assert game_screen.view_mode == "3D"
        game_screen.update(0.016)
        game_screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_manual_input_in_3d_mode():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface, levels=_mock_levels())
    game_screen.view_mode = "3D"
    game_screen.load_level(0)

    start_pos = (game_screen.current_state.block.r, game_screen.current_state.block.c)
    assert game_screen.moves_count == 0

    # Dispatch arrow key event (pygame.K_RIGHT)
    event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    game_screen.handle_event(event_right)
    game_screen.update(0.016)
    game_screen.draw()

    assert game_screen.moves_count == 1
    assert game_screen.current_state.block.orientation == Orientation.LYING_H
    assert game_screen.current_state.block.c == start_pos[1] + 1
    raw_bytes = pygame.image.tobytes(surface, "RGB")
    assert any(b > 0 for b in raw_bytes)

    # Dispatch WASD key event (pygame.K_d)
    event_d = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
    game_screen.handle_event(event_d)
    game_screen.update(0.016)
    game_screen.draw()

    assert game_screen.moves_count == 2
    raw_bytes2 = pygame.image.tobytes(surface, "RGB")
    assert any(b > 0 for b in raw_bytes2)


def test_replayer_playback_in_3d_mode():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface, levels=_mock_levels())
    game_screen.view_mode = "3D"
    game_screen.load_level(0)

    # Trigger replayer on a solution path
    game_screen.replayer = SolutionReplayer(
        game_screen.level,
        game_screen.current_state,
        ["R", "R", "R", "R"],
        step_delay=0.4,
    )
    assert game_screen.replayer is not None
    assert game_screen.replayer.total_steps == 4

    # Step forward
    init_idx = game_screen.replayer.current_index
    game_screen.replay_next_step()
    assert game_screen.replayer.current_index == init_idx + 1

    # Update with dt
    game_screen.update(0.05)

    # Verify draw succeeds with replayer active
    game_screen.draw()
    raw_bytes = pygame.image.tobytes(surface, "RGB")
    assert any(b > 0 for b in raw_bytes)

    # Advance time through replayer and draw
    game_screen.update(0.5)
    game_screen.draw()
    raw_bytes2 = pygame.image.tobytes(surface, "RGB")
    assert any(b > 0 for b in raw_bytes2)







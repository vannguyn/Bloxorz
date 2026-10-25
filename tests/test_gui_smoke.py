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
from core.block import Cube, Orientation
from core.game_state import GameState
from core.board import Board
from rendering.board_renderer import BoardRenderer
from rendering.block_renderer import BlockRenderer
from rendering.animation import SolutionReplayer
from ui.button import Button
from ui.game_screen import GameScreen
from ui.menu_screen import MenuScreen
from ui.pause_screen import PauseScreen
from ui.result_screen import ResultOverlay
from ui.solver_bridge import on_solve, AsyncSolverBridge, SolverBridgeState
from ui.dependencies import get_levels


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
    assert len(game_screen.levels) == 10
    assert game_screen.level.id == "level_01"
    assert game_screen.current_state.block.orientation == Orientation.STANDING


def test_render_all_loaded_levels():
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

    start_pos = game_screen.current_state.block.position
    assert game_screen.moves_count == 0

    # Simulate pressing Right arrow
    event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    game_screen.handle_event(event_right)
    game_screen.update(0.016)

    assert game_screen.moves_count == 1
    assert game_screen.current_state.block.orientation == Orientation.HORIZONTAL
    assert game_screen.current_state.block.position == (start_pos[0] + 1, start_pos[1])

    assert game_screen.manual_transition is not None
    game_screen.update(game_screen.MANUAL_ANIMATION_SECONDS / 2)
    assert game_screen.manual_transition_elapsed == pytest.approx(0.016 + game_screen.MANUAL_ANIMATION_SECONDS / 2)
    game_screen.draw()
    game_screen.update(game_screen.MANUAL_ANIMATION_SECONDS / 2)
    assert game_screen.manual_transition is None


def test_split_level_and_space_key():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    # Exercise the real split-state transition directly.
    board = Board(width=4, height=1, tiles=frozenset((x, 0) for x in range(4)), goal=(3, 0))
    game_screen.current_state = GameState(board, Cube((0, 0)), Cube((3, 0)))
    assert game_screen.current_state.is_split is True
    assert game_screen.current_state.controlled_index == 0

    # Press SPACE to toggle active cube
    event_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    game_screen.handle_event(event_space)
    game_screen.update(0.016)

    assert game_screen.current_state.controlled_index == 1


def test_sync_solver_bridge_contract():
    level = get_levels()[0]
    state = level.start_state
    result = on_solve("BFS", level, state)

    assert result.success is True
    assert result.path is not None
    assert result.solution_length == len(result.path)
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
    assert game_screen.replayer.total_steps == game_screen.latest_result.solution_length

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


def test_menu_and_pause_screens_render_and_dispatch_actions():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    actions = []
    menu = MenuScreen(surface, lambda: actions.append("start"), lambda: actions.append("quit"))
    pause = PauseScreen(surface, lambda: actions.append("resume"), lambda: actions.append("menu"))

    menu.draw()
    pause.draw()
    assert len(menu.buttons) == 2
    assert len(pause.buttons) == 2

    button = menu.buttons[0]
    button.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center))
    button.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=button.rect.center))
    assert actions == ["start"]


def test_dependencies_adapter_contract():
    from ui import dependencies
    assert isinstance(dependencies.IS_MOCK_CORE, bool)
    assert isinstance(dependencies.IS_MOCK_SOLVERS, bool)
    assert dependencies.IS_MOCK_MODE == (dependencies.IS_MOCK_CORE or dependencies.IS_MOCK_SOLVERS)
    assert callable(dependencies.apply_move)
    assert callable(dependencies.is_goal)
    assert callable(dependencies.get_solver)
    assert callable(dependencies.run_solver)
    assert callable(dependencies.get_levels)
    assert len(dependencies.get_levels()) == 10
    solver = dependencies.get_solver("BFS")
    assert solver is not None
    assert dependencies.get_mode_badge_text() == "[REAL]"


def test_replayer_speed_control():
    from levels.level_loader import load_levels
    from rendering.animation import SolutionReplayer
    level = load_levels()[0]
    state = level.start_state
    replayer = SolutionReplayer(level, state, ["R", "D", "R", "U"], step_delay=0.4)

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
    assert replayer.transition_progress == pytest.approx(0.25)


def test_replayer_draws_intermediate_block_position():
    from levels.level_loader import load_levels
    from rendering.animation import SolutionReplayer

    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    level = load_levels()[0]
    replayer = SolutionReplayer(level, level.start_state, ["R"], step_delay=0.4)
    board_renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
    board_renderer.compute_layout(level, pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT))
    block_renderer = BlockRenderer(board_renderer)

    replayer.update(0.2)
    assert replayer.transition_progress == pytest.approx(0.5)
    block_renderer.draw(
        surface,
        replayer.current_state,
        transition_to=replayer.next_state,
        progress=replayer.transition_progress,
    )


def test_board_uses_isometric_diamond_projection():
    level = get_levels()[0]
    renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
    renderer.compute_layout(level, pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT))

    origin = renderer.project(0, 0)
    right = renderer.project(1, 0)
    down = renderer.project(0, 1)
    assert right[0] - origin[0] == pytest.approx(renderer.tile_size / 2, abs=1)
    assert right[1] - origin[1] == pytest.approx(-renderer.tile_height / 2, abs=1)
    assert down[0] - origin[0] == pytest.approx(renderer.tile_size / 2, abs=1)
    assert down[1] - origin[1] == pytest.approx(renderer.tile_height / 2, abs=1)
    assert renderer.tile_size > settings.TILE_SIZE * 1.65


def test_void_tile_renders_as_a_black_hole():
    surface = pygame.Surface((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
    level = get_levels()[0]
    renderer.compute_layout(
        level,
        pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT),
    )
    renderer._draw_void(surface, 0, 0)
    center = renderer._average(renderer.tile_corners(0, 0))

    assert surface.get_at(center)[:3] == (2, 4, 8)


def test_horizontal_roll_has_distinct_intermediate_animation_frames():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    level = get_levels()[0]
    start = level.start_state
    end = start.move("right")
    assert end is not None
    renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)
    renderer.compute_layout(
        level,
        pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT),
    )
    block_renderer = BlockRenderer(renderer)

    block_renderer.draw(surface, start)
    standing = pygame.image.tobytes(surface, "RGB")
    block_renderer.draw(surface, start, transition_to=end, progress=0.5)
    rolling = pygame.image.tobytes(surface, "RGB")
    block_renderer.draw(surface, end)
    horizontal = pygame.image.tobytes(surface, "RGB")

    assert standing != rolling
    assert rolling != horizontal


def test_bridge_folds_between_closed_and_open_states():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    level = next(item for item in get_levels() if item.board.bridges)
    bridge_id, bridge = next(iter(level.board.bridges.items()))
    start = level.start_state
    closed_states = start.bridge_map
    open_states = dict(closed_states)
    closed_states[bridge_id] = "closed"
    open_states[bridge_id] = "open"
    closed = GameState(level.board, start.block, bridge_states=closed_states)
    opened = GameState(level.board, start.block, bridge_states=open_states)
    renderer = BoardRenderer(settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT)

    renderer.draw(
        surface,
        level,
        opened,
        pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT),
        bridge_transition=(closed, opened, 0.5),
    )
    halfway = pygame.image.tobytes(surface, "RGB")
    renderer.draw(
        surface,
        level,
        opened,
        pygame.Rect(0, 0, settings.BOARD_AREA_WIDTH, settings.BOARD_AREA_HEIGHT),
        bridge_transition=(closed, opened, 1.0),
    )
    fully_open = pygame.image.tobytes(surface, "RGB")

    assert bridge.tiles
    assert halfway != fully_open


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

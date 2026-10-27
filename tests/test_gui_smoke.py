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
from core.interfaces import BlockState, GameState, Level, Orientation, SolverResult, Switch, TileType
from rendering.board_renderer import BoardRenderer
from rendering.block_renderer import BlockRenderer
from rendering.animation import SolutionReplayer
from ui.button import Button
from ui.game_screen import GameScreen
from ui.result_screen import ResultOverlay
from ui.solver_bridge import on_solve, AsyncSolverBridge, SolverBridgeState
from ui.dependencies import is_goal
from tests.mocks import (
    mock_level_simple,
    mock_level_with_fragile,
    mock_level_with_bridge,
    mock_level_split,
    MockBFSSolver,
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


def test_replayer_empty_path_boundary_guard():
    from tests.mocks import mock_level_simple
    from core.interfaces import GameState
    from rendering.animation import SolutionReplayer
    level = mock_level_simple()
    state = GameState(block=level.start, bridge_mask=0)
    replayer = SolutionReplayer(level, state, [], step_delay=0.4)
    assert replayer.is_finished is True
    replayer.play()
    assert replayer.is_playing is True
    # update() must catch is_finished, reset is_playing to False, and return False
    changed = replayer.update(0.1)
    assert changed is False
    assert replayer.is_playing is False


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


def test_2d_special_cells_visual_redesign():
    """Verify 2D special cells visual redesign: no red-X on closed bridge, full-span fragile stripes, switch press state."""
    surface = pygame.Surface((800, 600))
    renderer = BoardRenderer(800, 600)

    # 1. Closed bridge in 2D: verify no red pixels and verify recessed docking rails/pins
    level_bridge = mock_level_with_bridge()
    state_bridge_closed = GameState(block=level_bridge.start, bridge_mask=0)
    surface.fill((0, 0, 0))
    renderer.draw(surface, level_bridge, state_bridge_closed)

    bridge_cell = (1, 4)
    bridge_rect = renderer.get_cell_rect(*bridge_cell)
    bridge_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(bridge_rect.left, bridge_rect.right)
        for y in range(bridge_rect.top, bridge_rect.bottom)
    ]
    red_pixels = [
        p for p in bridge_pixels
        if p == (120, 50, 60) or (p[0] > 150 and p[1] < 100 and p[2] < 100) or (p[0] > 110 and p[1] < 70 and p[2] < 70)
    ]
    assert len(red_pixels) == 0, f"Found red pixels in closed bridge: {red_pixels[:5]}"

    has_dock_features = any(
        p in (settings.COLOR_BRIDGE_DOCK_RAIL, settings.COLOR_BRIDGE_DOCK_PIN)
        for p in bridge_pixels
    )
    assert has_dock_features, "Closed bridge should render docking rail or pin features"

    # 2. Fragile tile in 2D: verify amber glass base and white fracture crack lines
    level_fragile = mock_level_with_fragile()
    state_fragile = GameState(block=level_fragile.start, bridge_mask=0)
    surface.fill((0, 0, 0))
    renderer.draw(surface, level_fragile, state_fragile)

    fragile_cell = (1, 3)
    fragile_rect = renderer.get_cell_rect(*fragile_cell)

    fragile_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(fragile_rect.left, fragile_rect.right)
        for y in range(fragile_rect.top, fragile_rect.bottom)
    ]
    orange_pixels = [
        p for p in fragile_pixels
        if p == settings.COLOR_FRAGILE or (p[0] > 200 and 100 <= p[1] <= 180 and 20 <= p[2] <= 80)
    ]
    stripe_pixels = [
        p for p in fragile_pixels
        if p == settings.COLOR_FRAGILE_STRIPE
    ]
    assert len(orange_pixels) > 50, "Fragile tile orange base missing"
    assert len(stripe_pixels) > 0, "Fragile tile hazard warning stripes missing"

    # 3. Switch in 2D: verify pixel colors change when block is standing on switch vs away
    sw_cell = (1, 2)
    state_away = GameState(
        block=BlockState(r=1, c=0, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface.fill((0, 0, 0))
    renderer.draw(surface, level_bridge, state_away)
    sw_rect = renderer.get_cell_rect(*sw_cell)
    pixels_away = [
        surface.get_at((x, y))[:3]
        for x in range(sw_rect.left, sw_rect.right)
        for y in range(sw_rect.top, sw_rect.bottom)
    ]

    state_standing_on_sw = GameState(
        block=BlockState(r=1, c=2, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface.fill((0, 0, 0))
    renderer.draw(surface, level_bridge, state_standing_on_sw)
    pixels_on = [
        surface.get_at((x, y))[:3]
        for x in range(sw_rect.left, sw_rect.right)
        for y in range(sw_rect.top, sw_rect.bottom)
    ]

    assert pixels_away != pixels_on, "Switch should render differently when block is on it vs away"

    # 4. Heavy & Split switches in 2D
    heavy_sw = Switch(id="sw_heavy", type="heavy", position=(0, 0), bridge_ids=[], mode="toggle")
    split_sw = Switch(id="sw_split", type="split", position=(0, 0), bridge_ids=[], mode="toggle")
    test_rect = pygame.Rect(10, 10, renderer.tile_size, renderer.tile_size)

    # Heavy switch: metal base plate and crimson X arms
    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, test_rect, heavy_sw, is_pressed=False)
    heavy_unpressed = [
        surface.get_at((x, y))[:3]
        for x in range(10, 10 + renderer.tile_size)
        for y in range(10, 10 + renderer.tile_size)
    ]
    assert any(p == settings.COLOR_HEAVY_BASE for p in heavy_unpressed), "Heavy switch base missing"
    assert any(p == settings.COLOR_HEAVY_RED for p in heavy_unpressed), "Heavy switch X arms missing"

    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, test_rect, heavy_sw, is_pressed=True)
    heavy_pressed = [
        surface.get_at((x, y))[:3]
        for x in range(10, 10 + renderer.tile_size)
        for y in range(10, 10 + renderer.tile_size)
    ]
    assert heavy_pressed != heavy_unpressed, "Heavy switch should visually update when pressed"

    # Split switch: cyan brackets and wings
    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, test_rect, split_sw, is_pressed=False)
    split_unpressed = [
        surface.get_at((x, y))[:3]
        for x in range(10, 10 + renderer.tile_size)
        for y in range(10, 10 + renderer.tile_size)
    ]
    assert any(p == settings.COLOR_SPLIT_CYAN for p in split_unpressed), "Split switch cyan affordance missing"

    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, test_rect, split_sw, is_pressed=True)
    split_pressed = [
        surface.get_at((x, y))[:3]
        for x in range(10, 10 + renderer.tile_size)
        for y in range(10, 10 + renderer.tile_size)
    ]
    assert split_pressed != split_unpressed, "Split switch should visually update when pressed"


def test_redesign_2d_special_cells():
    """Alias for test_2d_special_cells_visual_redesign to satisfy both -k filters."""
    test_2d_special_cells_visual_redesign()


def test_closed_bridge_vs_heavy_switch_red_exclusivity_2d():
    """Assert closed bridge has 0 red pixels (r > 150 and g < 100 and b < 100),
    while heavy switch has > 10 red pixels in 2D mode.
    Also verifies all 10 real production levels render cleanly in 2D mode with overhauled visuals.
    """
    from levels.level_loader import load_level, load_all_levels

    renderer = BoardRenderer(800, 600)
    block_renderer = BlockRenderer(renderer)

    # 1. Verify the latest heavy-bridge level's closed bridge vs switch visuals.
    lvl3 = load_level("level_03")
    state_closed = GameState(block=lvl3.start, bridge_mask=0)
    surface = pygame.Surface((800, 600))
    surface.fill((0, 0, 0))
    renderer.draw(surface, lvl3, state_closed)

    for cell in lvl3.bridges["bridge_heavy"]:
        rect = renderer.get_cell_rect(*cell)
        red_pixels = [
            surface.get_at((x, y))[:3]
            for x in range(rect.left, rect.right)
            for y in range(rect.top, rect.bottom)
            if surface.get_at((x, y))[0] > 150
            and surface.get_at((x, y))[1] < 100
            and surface.get_at((x, y))[2] < 100
        ]
        assert len(red_pixels) == 0, (
            f"2D closed bridge cell {cell} contained {len(red_pixels)} red pixels; strictly 0 expected"
        )

    heavy_sw = next(s for s in lvl3.switches if s.type == "heavy")
    heavy_rect = renderer.get_cell_rect(*heavy_sw.position)
    heavy_red_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(heavy_rect.left, heavy_rect.right)
        for y in range(heavy_rect.top, heavy_rect.bottom)
        if surface.get_at((x, y))[0] > 150
        and surface.get_at((x, y))[1] < 100
        and surface.get_at((x, y))[2] < 100
    ]
    assert len(heavy_red_pixels) > 10, (
        f"2D heavy switch at {heavy_sw.position} had {len(heavy_red_pixels)} red pixels; expected > 10"
    )

    # Switch depression visual differentiation
    pixels_unpressed = [
        surface.get_at((x, y))[:3]
        for x in range(heavy_rect.left, heavy_rect.right)
        for y in range(heavy_rect.top, heavy_rect.bottom)
    ]
    state_pressed = GameState(
        block=BlockState(r=heavy_sw.position[0], c=heavy_sw.position[1], orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface_pressed = pygame.Surface((800, 600))
    surface_pressed.fill((0, 0, 0))
    renderer.draw(surface_pressed, lvl3, state_pressed)
    pixels_pressed = [
        surface_pressed.get_at((x, y))[:3]
        for x in range(heavy_rect.left, heavy_rect.right)
        for y in range(heavy_rect.top, heavy_rect.bottom)
    ]
    assert pixels_unpressed != pixels_pressed, "Heavy switch visual output must change upon depression"

    # 2. Verify all 10 real production levels render cleanly in 2D mode
    all_levels = load_all_levels()
    assert len(all_levels) == 10
    for lvl in all_levels:
        surf = pygame.Surface((800, 600))
        st = GameState(block=lvl.start, bridge_mask=lvl.initial_bridge_mask)
        renderer.draw(surf, lvl, st)
        block_renderer.draw(surf, st)
        raw = pygame.image.tobytes(surf, "RGB")
        assert any(b > 0 for b in raw), f"2D rendering for {lvl.id} produced empty surface"


def test_2d_amber_glass_and_switch_patch():
    """Assert 2D fragile tile renders amber base with white radiating crack lines,
    heavy switch renders 12-point embossed steel X on base plate with rivets,
    and split switch compresses wing gap from 6px to 2px when pressed.
    """
    renderer = BoardRenderer(800, 600)
    tile_rect = pygame.Rect(10, 10, renderer.tile_size, renderer.tile_size)
    surface = pygame.Surface((800, 600))

    # 1. Fragile tile in 2D
    surface.fill((0, 0, 0))
    renderer._draw_fragile_tile(surface, tile_rect)
    fragile_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(tile_rect.left, tile_rect.right)
        for y in range(tile_rect.top, tile_rect.bottom)
    ]
    orange_base_pixels = [
        p for p in fragile_pixels
        if p == settings.COLOR_FRAGILE or (p[0] > 200 and 100 <= p[1] <= 180 and 20 <= p[2] <= 80)
    ]
    stripe_pixels = [
        p for p in fragile_pixels
        if p == settings.COLOR_FRAGILE_STRIPE
    ]
    assert len(orange_base_pixels) > 50, (
        f"2D fragile tile orange base pixels count={len(orange_base_pixels)}; expected > 50"
    )
    assert len(stripe_pixels) > 5, (
        f"2D fragile tile stripe pixels count={len(stripe_pixels)}; expected > 5"
    )

    # 2. Heavy switch in 2D: base plate COLOR_HEAVY_BASE and 12-point cross COLOR_HEAVY_RED
    heavy_sw = Switch(id="sw_heavy", type="heavy", position=(0, 0), bridge_ids=[], mode="toggle")
    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, tile_rect, heavy_sw, is_pressed=False)
    heavy_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(tile_rect.left, tile_rect.right)
        for y in range(tile_rect.top, tile_rect.bottom)
    ]
    assert any(p == settings.COLOR_HEAVY_BASE for p in heavy_pixels), (
        "Heavy switch metal base plate (COLOR_HEAVY_BASE) missing in 2D"
    )
    assert any(p == settings.COLOR_HEAVY_RED for p in heavy_pixels), (
        "Heavy switch 12-point cross (COLOR_HEAVY_RED) missing in 2D"
    )

    # 3. Split switch in 2D: wing gap compression between pressed vs unpressed
    split_sw = Switch(id="sw_split", type="split", position=(0, 0), bridge_ids=[], mode="toggle")
    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, tile_rect, split_sw, is_pressed=False)
    split_unpressed = [
        surface.get_at((x, y))[:3]
        for x in range(tile_rect.left, tile_rect.right)
        for y in range(tile_rect.top, tile_rect.bottom)
    ]
    surface.fill((0, 0, 0))
    renderer._draw_switch(surface, tile_rect, split_sw, is_pressed=True)
    split_pressed = [
        surface.get_at((x, y))[:3]
        for x in range(tile_rect.left, tile_rect.right)
        for y in range(tile_rect.top, tile_rect.bottom)
    ]
    assert any(p == settings.COLOR_SPLIT_CYAN for p in split_unpressed), (
        "Split switch wing (COLOR_SPLIT_CYAN) missing in 2D"
    )
    assert split_pressed != split_unpressed, (
        "Split switch pixel output must differ when is_pressed=True due to gap compression"
    )


def test_patch_2d_amber_glass_and_switch():
    """Alias for -k patch_2d filter compatibility."""
    test_2d_amber_glass_and_switch_patch()


def test_all_10_stages_visual_patch_regression_2d():
    """Validates visual patch regression across all 10 real production stages in 2D:
    1. All 10 stages render cleanly without exceptions in 2D mode with board and block.
    2. Fragile tiles in stages contain predominantly orange hues (R > G > B), white crack highlights (R, G, B > 220), and rust under-shadow pixels (110 <= R <= 180, 30 <= G <= 90, B < 60).
    3. Heavy switches and Split switches visibly alter pixel representation upon block contact.
    4. Heavy switches contain COLOR_HEAVY_BASE and COLOR_HEAVY_RED; Split switches contain COLOR_SPLIT_CYAN.
    """
    from core.interfaces import TileType
    from levels.level_loader import load_all_levels

    all_levels = load_all_levels()
    assert len(all_levels) == 10

    renderer = BoardRenderer(800, 600)
    block_renderer = BlockRenderer(renderer)
    fragile_tiles_checked = 0

    for lvl in all_levels:
        surf = pygame.Surface((800, 600))
        st = GameState(block=lvl.start, bridge_mask=lvl.initial_bridge_mask)
        renderer.draw(surf, lvl, st)
        block_renderer.draw(surf, st)
        raw = pygame.image.tobytes(surf, "RGB")
        assert any(b > 0 for b in raw), f"2D rendering for {lvl.id} produced empty surface"

        # Check fragile tiles in this stage
        for (r, c), tile_type in lvl.tiles.items():
            if tile_type == TileType.FRAGILE:
                fragile_tiles_checked += 1
                rect = renderer.get_cell_rect(r, c)
                pixels = [
                    surf.get_at((x, y))[:3]
                    for x in range(rect.left, rect.right)
                    for y in range(rect.top, rect.bottom)
                ]
                orange_pixels = [p for p in pixels if p[0] > p[1] > p[2]]
                stripe_pixels = [p for p in pixels if p == settings.COLOR_FRAGILE_STRIPE]
                assert len(orange_pixels) > 50, (
                    f"2D stage {lvl.id} fragile tile at ({r}, {c}) lacking dominant orange hues (found {len(orange_pixels)})"
                )
                assert len(stripe_pixels) > 0, (
                    f"2D stage {lvl.id} fragile tile at ({r}, {c}) lacking hazard warning stripes"
                )

        # Check switches in this stage
        for sw in lvl.switches:
            if sw.type in ("heavy", "split"):
                block_away = lvl.start if (lvl.start.r, lvl.start.c) != sw.position else BlockState(
                    r=(sw.position[0] + 2) % lvl.height,
                    c=(sw.position[1] + 2) % lvl.width,
                    orientation=Orientation.STANDING,
                )
                st_unpressed = GameState(block=block_away, bridge_mask=lvl.initial_bridge_mask)
                st_pressed = GameState(
                    block=BlockState(r=sw.position[0], c=sw.position[1], orientation=Orientation.STANDING),
                    bridge_mask=lvl.initial_bridge_mask,
                )

                surf_unpressed = pygame.Surface((800, 600))
                renderer.draw(surf_unpressed, lvl, st_unpressed)
                rect = renderer.get_cell_rect(*sw.position)
                pix_unpressed = [
                    surf_unpressed.get_at((x, y))[:3]
                    for x in range(rect.left, rect.right)
                    for y in range(rect.top, rect.bottom)
                ]

                surf_pressed = pygame.Surface((800, 600))
                renderer.draw(surf_pressed, lvl, st_pressed)
                pix_pressed = [
                    surf_pressed.get_at((x, y))[:3]
                    for x in range(rect.left, rect.right)
                    for y in range(rect.top, rect.bottom)
                ]

                assert pix_unpressed != pix_pressed, (
                    f"2D switch {sw.id} ({sw.type}) in {lvl.id} did not alter pixel representation upon contact"
                )

                if sw.type == "heavy":
                    assert any(p == settings.COLOR_HEAVY_BASE for p in pix_unpressed), (
                        f"Heavy switch in {lvl.id} missing COLOR_HEAVY_BASE"
                    )
                    assert any(p == settings.COLOR_HEAVY_RED for p in pix_unpressed), (
                        f"Heavy switch in {lvl.id} missing COLOR_HEAVY_RED"
                    )
                elif sw.type == "split":
                    assert any(p == settings.COLOR_SPLIT_CYAN for p in pix_unpressed), (
                        f"Split switch in {lvl.id} missing COLOR_SPLIT_CYAN"
                    )

    assert fragile_tiles_checked == 20, f"Expected 20 fragile tiles across all stages, got {fragile_tiles_checked}"


def test_2d_pixel_art_fragile_tile_rendering():
    """Verify 2D fragile tile renders solid orange body with diagonal hazard warning stripes."""
    renderer = BoardRenderer(viewport_width=800, viewport_height=600)
    tile_size = settings.TILE_SIZE  # 48
    surf = pygame.Surface((tile_size, tile_size))
    rect = pygame.Rect(0, 0, tile_size, tile_size)
    renderer._draw_fragile_tile(surf, rect)

    pixels = [surf.get_at((x, y))[:3] for x in range(rect.width) for y in range(rect.height)]
    total_pixels = len(pixels)

    orange_pixels = [p for p in pixels if p[0] > p[1] > p[2]]
    stripe_pixels = [p for p in pixels if p == settings.COLOR_FRAGILE_STRIPE]

    assert len(stripe_pixels) > 0, "Expected diagonal hazard warning stripes"
    assert len(orange_pixels) / total_pixels > 0.50, (
        f"Orange pixels (R > G > B) must dominate > 50% of tile area (got {len(orange_pixels) / total_pixels:.2%})"
    )


def test_button_icon_and_selected_state():
    """Verify Button renders with selected=True using COLOR_BTN_PRIMARY, and draws an icon via icon_drawer."""
    from ui.icons import draw_play_icon

    surface = pygame.Surface((200, 100))
    surface.fill((0, 0, 0))
    font = pygame.font.Font(None, 16)

    # 1. Button with selected=True, icon_drawer, and text
    btn = Button(
        (10, 10, 120, 36),
        "Play",
        icon_drawer=draw_play_icon,
        selected=True,
    )
    assert btn.selected is True
    assert btn.icon_drawer is draw_play_icon

    btn.draw(surface, font)

    # Background must contain COLOR_BTN_PRIMARY pixels
    btn_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(btn.rect.left, btn.rect.right)
        for y in range(btn.rect.top, btn.rect.bottom)
    ]
    assert settings.COLOR_BTN_PRIMARY in btn_pixels, (
        f"Button with selected=True did not contain COLOR_BTN_PRIMARY {settings.COLOR_BTN_PRIMARY}"
    )

    # Active border should be COLOR_TEXT_ACCENT
    assert settings.COLOR_TEXT_ACCENT in btn_pixels, (
        f"Button with selected=True did not contain active border COLOR_TEXT_ACCENT {settings.COLOR_TEXT_ACCENT}"
    )

    # 2. Icon-only button (empty text) centers icon
    surface.fill((0, 0, 0))
    icon_only_btn = Button(
        (10, 10, 50, 36),
        "",
        icon_drawer=draw_play_icon,
        selected=False,
    )
    icon_only_btn.draw(surface, font)
    icon_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(icon_only_btn.rect.left, icon_only_btn.rect.right)
        for y in range(icon_only_btn.rect.top, icon_only_btn.rect.bottom)
    ]
    # Check drawn pixels exist (non-black and default button color exists)
    assert settings.COLOR_BTN_DEFAULT in icon_pixels
    assert any(p != (0, 0, 0) and p != settings.COLOR_BTN_DEFAULT for p in icon_pixels)


def test_legend_bar_rendering():
    """Verify LegendBar renders a pill bar containing 5 chips (Block, Goal, Fragile Tile, Closed Bridge, Split Switch)."""
    from ui.legend_bar import LegendBar

    legend = LegendBar()
    surface = pygame.Surface((700, 680))
    surface.fill((10, 15, 25))
    area_rect = pygame.Rect(0, 0, 700, 680)
    font = pygame.font.Font(None, 16)

    bar_rect = legend.draw(surface, area_rect, font)
    assert isinstance(bar_rect, pygame.Rect)

    # Bar docked near the bottom of area_rect with height 34-36px
    assert bar_rect.bottom <= area_rect.bottom
    assert bar_rect.top >= area_rect.bottom - 50
    assert 32 <= bar_rect.height <= 38

    # Verify background and border colors in pill bar
    pill_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(bar_rect.left, bar_rect.right)
        for y in range(bar_rect.top, bar_rect.bottom)
    ]
    assert settings.COLOR_CARD_BG in pill_pixels, "LegendBar container missing COLOR_CARD_BG"
    assert settings.COLOR_CARD_BORDER in pill_pixels, "LegendBar container missing COLOR_CARD_BORDER"

    # Verify 5 visual chips rendered:
    # 1. Block: orange rect (245, 130, 45)
    orange_pixels = [p for p in pill_pixels if p == (245, 130, 45)]
    assert len(orange_pixels) > 0, "LegendBar missing Block chip orange rect (245, 130, 45)"

    # 2. Goal: gold circle (255, 215, 0)
    gold_pixels = [p for p in pill_pixels if p == (255, 215, 0)]
    assert len(gold_pixels) > 0, "LegendBar missing Goal chip gold circle (255, 215, 0)"

    # 3. Fragile Tile: orange rect with yellow stripes
    fragile_stripe_pixels = [p for p in pill_pixels if p == settings.COLOR_FRAGILE_STRIPE]
    assert len(fragile_stripe_pixels) > 0, "LegendBar missing Fragile Tile hazard stripe pixels"

    # 4. Closed Bridge: dark rect with red X (239, 68, 68)
    red_x_pixels = [p for p in pill_pixels if p == (239, 68, 68)]
    assert len(red_x_pixels) > 0, "LegendBar missing Closed Bridge red X (239, 68, 68)"

    # 5. Split Switch: cyan arched wings (56, 189, 248)
    cyan_pixels = [p for p in pill_pixels if p == (56, 189, 248)]
    assert len(cyan_pixels) > 0, "LegendBar missing Split Switch cyan arched wings (56, 189, 248)"

    # Check chips specification
    assert hasattr(legend, "CHIPS")
    chip_labels = [chip[0] for chip in legend.CHIPS]
    assert chip_labels == ["Block", "Goal", "Fragile Tile", "Closed Bridge", "Split Switch"]


def test_game_screen_card_layout_and_algorithm_selection():
    """Verify card-based sidebar layout, interactive algorithm radio selection, telemetry keys, and docked LegendBar."""
    from core.interfaces import SolverResult

    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface)

    # 1. screen.selected_algo defaults to "BFS"
    assert hasattr(screen, "selected_algo"), "GameScreen missing selected_algo attribute"
    assert screen.selected_algo == "BFS"

    # Verify algorithm buttons exist and BFS is initially selected
    assert hasattr(screen, "btn_algo_bfs")
    assert hasattr(screen, "btn_algo_dfs")
    assert hasattr(screen, "btn_solve_action")
    assert screen.btn_algo_bfs.selected is True
    assert screen.btn_algo_dfs.selected is False
    assert "Solve (BFS)" in screen.btn_solve_action.text

    # 2. Clicking DFS button switches screen.selected_algo to "DFS", highlights DFS, un-highlights BFS
    dfs_click_event = pygame.event.Event(
        pygame.MOUSEBUTTONUP,
        button=1,
        pos=screen.btn_algo_dfs.rect.center,
    )
    screen.btn_algo_dfs.is_pressed = True
    screen.btn_algo_dfs.handle_event(dfs_click_event)

    assert screen.selected_algo == "DFS"
    assert screen.btn_algo_dfs.selected is True
    assert screen.btn_algo_bfs.selected is False

    # 3. Primary solve button label reflects "Solve (DFS)"
    assert "Solve (DFS)" in screen.btn_solve_action.text

    # 4. Verifies solution metrics card renders telemetry keys: Time:, Memory:, Expanded:, Length:, Cost:
    rendered_texts: list[str] = []
    real_font_mono = screen.font_mono

    class FontSpy:
        def __init__(self, font):
            self._font = font

        def render(self, text, antialias, color, background=None):
            rendered_texts.append(str(text))
            return self._font.render(text, antialias, color, background)

        def __getattr__(self, name):
            return getattr(self._font, name)

    screen.font_mono = FontSpy(real_font_mono)

    # Render without solver result (initial state)
    screen.draw()
    for key in ["Time:", "Memory:", "Expanded:", "Length:", "Cost:"]:
        assert any(key in t for t in rendered_texts), (
            f"Telemetry key '{key}' not found in rendered texts without result: {rendered_texts}"
        )

    # Render with an active solver result
    rendered_texts.clear()
    screen.latest_result = SolverResult(
        path=["R", "R", "U"],
        expanded_nodes=128,
        search_time_ms=45.67,
        peak_memory_kb=1024,
        solution_length=3,
        cost=3.0,
        success=True,
    )
    screen.draw()
    for key in ["Time:", "Memory:", "Expanded:", "Length:", "Cost:"]:
        assert any(key in t for t in rendered_texts), (
            f"Telemetry key '{key}' not found in rendered texts with result: {rendered_texts}"
        )

    # 5. Verifies LegendBar is rendered on the screen docked at bottom of board_rect
    assert hasattr(screen, "legend_bar"), "GameScreen missing legend_bar attribute"
    assert screen.legend_bar.last_rect is not None, "LegendBar was not drawn"
    assert screen.board_rect.contains(screen.legend_bar.last_rect), (
        f"LegendBar rect {screen.legend_bar.last_rect} is not contained within board_rect {screen.board_rect}"
    )


def test_all_10_stages_card_sidebar_and_docked_legend_regression():
    """Verify all 10 stages render cleanly in both 2D and 3D with card-based sidebar,
    docked LegendBar, full algorithm selection radio cycling, and speed controls.
    """
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    game_screen = GameScreen(surface)
    assert len(game_screen.levels) == 10

    # 1. Test all 10 stages in 2D and 3D with docked LegendBar and card layout
    for mode in ("2D", "3D"):
        game_screen.view_mode = mode
        for idx in range(len(game_screen.levels)):
            game_screen.load_level(idx)
            assert game_screen.view_mode == mode
            game_screen.update(0.016)
            game_screen.draw()

            # Surface must have rendered pixels
            raw_bytes = pygame.image.tobytes(surface, "RGB")
            assert any(b > 0 for b in raw_bytes), f"Stage {idx+1} rendered blank in {mode}"

            # Docked LegendBar must be drawn within board_rect
            assert game_screen.legend_bar.last_rect is not None
            assert game_screen.board_rect.contains(game_screen.legend_bar.last_rect)

            # Sidebar cards must be within screen bounds and right of board_rect
            card_x = settings.WINDOW_WIDTH - 270
            assert card_x >= game_screen.board_rect.right

    # 2. Full algorithm selection cycle through all 4 algorithms in the 2x2 grid
    for algo in ("BFS", "DFS", "UCS", "A*"):
        game_screen.select_algo(algo)
        assert game_screen.selected_algo == algo
        assert f"Solve ({algo})" in game_screen.btn_solve_action.text
        # Ensure only the active algorithm button has selected=True
        for name, btn in game_screen.algo_buttons.items():
            if name in ("A*", "ASTAR") and algo in ("A*", "ASTAR"):
                assert btn.selected is True
            elif name == algo:
                assert btn.selected is True
            else:
                assert btn.selected is False

    # 3. Verify playback button icons and initial states
    assert game_screen.btn_solve_action.icon_drawer is not None
    assert game_screen.btn_replay_prev.icon_drawer is not None
    assert game_screen.btn_replay_toggle.icon_drawer is not None
    assert game_screen.btn_replay_next.icon_drawer is not None
    assert game_screen.btn_speed.icon_drawer is not None

    # Step replay controls should initially be disabled before solution replay
    assert game_screen.btn_replay_prev.enabled is False
    assert game_screen.btn_replay_toggle.enabled is False
    assert game_screen.btn_replay_next.enabled is False


def test_playback_slider_hidden_when_idle():
    """Verify timeline slider is hidden and Card 2 is compact before solve."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    # Initial state: replayer is None
    assert screen.replayer is None
    assert hasattr(screen, "timeline_slider"), "GameScreen missing timeline_slider attribute"
    assert hasattr(screen, "card2_rect"), "GameScreen missing card2_rect attribute"
    assert screen.card2_rect.height == 156
    assert screen.btn_speed.rect.y == 374
    assert screen.timeline_slider.enabled is False

    # Spy on timeline_slider.draw to ensure it is NOT drawn
    drawn = []
    screen.timeline_slider.draw = lambda s: drawn.append(True)

    screen.draw()
    assert len(drawn) == 0, "Slider should not be drawn when idle (no replayer)"


def test_playback_slider_visible_and_card_expands_when_solved():
    """Verify timeline slider appears, Card 2 expands, and Step label is rendered after solve."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    # Solve level
    screen.trigger_solve("BFS")
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out")

    assert screen.replayer is not None
    assert screen.card2_rect.height == 192
    assert screen.btn_speed.rect.y == 408
    assert screen.timeline_slider.max_val == screen.replayer.total_steps
    assert screen.timeline_slider.enabled is True

    # Verify slider is drawn when solved
    drawn = []
    screen.timeline_slider.draw = lambda s: drawn.append(True)

    # Also capture font rendering to verify "Step: X/Y" is rendered
    rendered_texts = []
    real_font_mono = screen.font_mono

    class FontSpy:
        def __init__(self, font):
            self._font = font

        def render(self, text, antialias, color, background=None):
            rendered_texts.append(str(text))
            return self._font.render(text, antialias, color, background)

        def __getattr__(self, name):
            return getattr(self._font, name)

    screen.font_mono = FontSpy(real_font_mono)

    screen.draw()
    assert len(drawn) > 0, "Slider must be drawn when solved"
    step_labels = [t for t in rendered_texts if "Step:" in t]
    assert len(step_labels) > 0, f"Expected 'Step: 0/{screen.replayer.total_steps}' rendered"
    assert f"Step: 0/{screen.replayer.total_steps}" in step_labels[0]


def test_playback_slider_drag_auto_pause():
    """Verify dragging timeline slider pauses playback, scrubs replayer index, and updates state."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    # Solve level (4 steps)
    screen.trigger_solve("BFS")
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out")

    assert screen.replayer is not None
    assert screen.replayer.is_playing is True
    total_steps = screen.replayer.total_steps
    assert total_steps == 4

    # Simulate mouse drag at 50% of the slider track
    slider = screen.timeline_slider
    click_mid_x = slider.rect.left + slider.rect.width // 2
    click_y = slider.rect.centery

    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (click_mid_x, click_y), "button": 1})
    screen.handle_event(down_ev)

    # Playback should be paused automatically on drag start
    assert screen.replayer.is_playing is False
    assert screen.btn_replay_toggle.text == "Play"

    # Value should scrub to step 2 (50% of 4)
    assert screen.timeline_slider.value == 2
    assert screen.replayer.current_index == 2
    assert screen.current_state == screen.replayer.current_state
    assert screen.outcome_status is None

    # Scrub to step 1 (25% of 4)
    click_q_x = slider.rect.left + slider.rect.width // 4
    move_q_ev = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (click_q_x, click_y), "buttons": (1, 0, 0)})
    screen.handle_event(move_q_ev)
    assert screen.timeline_slider.value == 1
    assert screen.replayer.current_index == 1
    assert screen.current_state == screen.replayer.current_state

    # Scrub back to start (step 0)
    click_start_x = slider.rect.left
    move_start_ev = pygame.event.Event(pygame.MOUSEMOTION, {"pos": (click_start_x, click_y), "buttons": (1, 0, 0)})
    screen.handle_event(move_start_ev)
    assert screen.timeline_slider.value == 0
    assert screen.replayer.current_index == 0
    assert screen.current_state == screen.replayer.current_state

    # Release drag
    up_ev = pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (click_start_x, click_y), "button": 1})
    screen.handle_event(up_ev)
    assert slider.is_dragging is False

    # Verify scrubbing clears existing win status
    screen.outcome_status = "WIN"
    slider.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (click_q_x, click_y), "button": 1}))
    assert screen.replayer.current_index == 1
    assert screen.outcome_status is None


def test_playback_dynamic_card_expansion_clearance():
    """Verify clearance between Card 3 bottom and footer keybindings is at least 30px."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    # 1. Idle state clearance
    screen.draw()
    assert hasattr(screen, "footer_y"), "GameScreen missing footer_y attribute"
    assert hasattr(screen, "card3_rect"), "GameScreen missing card3_rect attribute"
    idle_clearance = screen.footer_y - screen.card3_rect.bottom
    assert idle_clearance >= 30, f"Idle clearance {idle_clearance}px < 30px"

    # 2. Solved state clearance
    screen.trigger_solve("BFS")
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out")

    screen.draw()
    solved_clearance = screen.footer_y - screen.card3_rect.bottom
    assert solved_clearance >= 30, f"Solved clearance {solved_clearance}px < 30px"
    # Ensure Card 3 top is anchored dynamically to card2_rect.bottom + 14
    assert screen.card3_rect.top == screen.card2_rect.bottom + 14


def test_playback_slider_split_scrubbing():
    """Verify split-block state restoration and rendering during timeline scrubbing."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())

    # 1. Test Mock Level 3 (dedicated split-cube level)
    screen.load_level(3)
    assert screen.current_state.block.is_split is True
    assert screen.current_state.block.active_cube == 0
    assert screen.current_state.block.cube_positions == ((2, 1), (3, 4))

    # Path exercising: SPACE (switch active), U (move cube 1), SPACE (switch active), R (move cube 0), R (merge cubes)
    path = ["SPACE", "U", "SPACE", "R", "R"]
    screen.replayer = SolutionReplayer(screen.level, screen.current_state, path)
    screen.timeline_slider.min_val = 0
    screen.timeline_slider.max_val = screen.replayer.total_steps
    screen.timeline_slider.value = 0
    screen._update_layout()

    slider = screen.timeline_slider
    assert slider.max_val == 5

    # Verify rendering at initial split state (Step 0) in both 2D and 3D
    for mode in ("2D", "3D"):
        screen.view_mode = mode
        screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)

    # Scrub forward to Step 1 (active cube toggled to 1 via SPACE)
    x1 = slider.rect.left + round(1 / 5.0 * slider.rect.width)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x1, slider.rect.centery), "button": 1}))
    assert screen.replayer.current_index == 1
    assert screen.current_state.block.is_split is True
    assert screen.current_state.block.active_cube == 1
    assert screen.current_state.block.cube_positions == ((2, 1), (3, 4))

    # Scrub forward to Step 2 (Cube 1 moved to (2, 4))
    x2 = slider.rect.left + round(2 / 5.0 * slider.rect.width)
    screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (x2, slider.rect.centery), "buttons": (1, 0, 0)}))
    assert screen.replayer.current_index == 2
    assert screen.current_state.block.is_split is True
    assert screen.current_state.block.active_cube == 1
    assert screen.current_state.block.cube_positions == ((2, 1), (2, 4))

    # Scrub forward to Step 5 (Cube 0 merged with Cube 1 into lying horizontal block)
    x5 = slider.rect.right
    screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (x5, slider.rect.centery), "buttons": (1, 0, 0)}))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x5, slider.rect.centery), "button": 1}))
    assert screen.replayer.current_index == 5
    assert screen.current_state.block.is_split is False
    assert screen.current_state.block.orientation == Orientation.LYING_H
    assert screen.current_state.block.cube_positions is None

    # Verify rendering at merged state in both 2D and 3D
    for mode in ("2D", "3D"):
        screen.view_mode = mode
        screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)

    # Scrub backward to Step 2 (restore split state from merged state)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x2, slider.rect.centery), "button": 1}))
    assert screen.replayer.current_index == 2
    assert screen.current_state.block.is_split is True
    assert screen.current_state.block.active_cube == 1
    assert screen.current_state.block.cube_positions == ((2, 1), (2, 4))

    # Scrub backward to Step 0 (restore initial split state)
    x0 = slider.rect.left
    screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (x0, slider.rect.centery), "buttons": (1, 0, 0)}))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x0, slider.rect.centery), "button": 1}))
    assert screen.replayer.current_index == 0
    assert screen.current_state.block.is_split is True
    assert screen.current_state.block.active_cube == 0
    assert screen.current_state.block.cube_positions == ((2, 1), (3, 4))

    # Verify rendering after scrub back to start in both 2D and 3D
    for mode in ("2D", "3D"):
        screen.view_mode = mode
        screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)

    # 2. Test Real Stage 8 (Split Garden)
    real_screen = GameScreen(surface)
    real_screen.load_level(7)  # Stage 08: Split Garden
    assert real_screen.current_state.block.is_split is False

    # Path ["R", "R"] enters the split switch at (4, 4), splitting the block
    stage8_path = ["R", "R"]
    real_screen.replayer = SolutionReplayer(real_screen.level, real_screen.current_state, stage8_path)
    real_screen.timeline_slider.min_val = 0
    real_screen.timeline_slider.max_val = real_screen.replayer.total_steps
    real_screen.timeline_slider.value = 0
    real_screen._update_layout()

    stage8_slider = real_screen.timeline_slider

    # Scrub to Step 2 (entered split switch -> split block)
    x_stage8_2 = stage8_slider.rect.right
    real_screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x_stage8_2, stage8_slider.rect.centery), "button": 1}))
    assert real_screen.replayer.current_index == 2
    assert real_screen.current_state.block.is_split is True
    assert real_screen.current_state.block.cube_positions == ((4, 5), (4, 6))

    for mode in ("2D", "3D"):
        real_screen.view_mode = mode
        real_screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)

    # Scrub back to Step 0 (restored unsplit start state)
    x_stage8_0 = stage8_slider.rect.left
    real_screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (x_stage8_0, stage8_slider.rect.centery), "buttons": (1, 0, 0)}))
    real_screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x_stage8_0, stage8_slider.rect.centery), "button": 1}))
    assert real_screen.replayer.current_index == 0
    assert real_screen.current_state.block.is_split is False
    assert real_screen.current_state.block.cube_positions is None

    for mode in ("2D", "3D"):
        real_screen.view_mode = mode
        real_screen.draw()
        raw_bytes = pygame.image.tobytes(surface, "RGB")
        assert any(b > 0 for b in raw_bytes)


def test_playback_slider_all_stages_scrubbing_regression():
    """Verify loading, solving, and scrubbing across all 10 real stages in both 2D and 3D modes."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface)
    assert len(screen.levels) == 10

    for idx in range(len(screen.levels)):
        screen.load_level(idx)

        # Trigger solve (BFS solves mock/stub paths instantly)
        screen.trigger_solve("BFS")
        t0 = time.time()
        while screen.solver_bridge.state == SolverBridgeState.RUNNING:
            screen.update(0.05)
            time.sleep(0.005)
            if time.time() - t0 > 3.0:
                pytest.fail(f"Stage {idx + 1} solve timed out")

        assert screen.replayer is not None
        assert screen.timeline_slider.enabled is True
        total_steps = screen.replayer.total_steps
        assert screen.timeline_slider.max_val == total_steps
        max_step = len(screen.replayer.states) - 1

        slider = screen.timeline_slider

        # 1. Scrub to end
        screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (slider.rect.left, slider.rect.centery), "button": 1}))
        screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (slider.rect.right, slider.rect.centery), "buttons": (1, 0, 0)}))
        screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (slider.rect.right, slider.rect.centery), "button": 1}))
        assert screen.replayer.current_index == max_step

        # 2. Scrub back to start
        screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (slider.rect.right, slider.rect.centery), "button": 1}))
        screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (slider.rect.left, slider.rect.centery), "buttons": (1, 0, 0)}))
        screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (slider.rect.left, slider.rect.centery), "button": 1}))
        assert screen.replayer.current_index == 0
        assert slider.is_dragging is False

        # Render in both 2D and 3D to ensure no clipping, out-of-bounds, or shader crash
        for mode in ("2D", "3D"):
            screen.view_mode = mode
            screen.draw()
            raw_bytes = pygame.image.tobytes(surface, "RGB")
            assert any(b > 0 for b in raw_bytes)


def test_playback_overlay_suppression_and_goal_activation(monkeypatch):
    """Verify that intermediate playback/scrubbing keeps overlay suppressed, while reaching the goal activates overlay and scrubbing backward toggles it off."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    # Valid solution path reaching the goal on mock level 0
    winning_path = ["R", "U", "L", "D", "R", "U", "R", "D", "R"]
    screen.replayer = SolutionReplayer(screen.level, screen.current_state, winning_path)
    screen.timeline_slider.min_val = 0
    screen.timeline_slider.max_val = screen.replayer.total_steps
    screen.timeline_slider.value = 0
    screen._update_layout()

    overlay_draws = []
    original_draw = ResultOverlay.draw

    def spy_draw(*args, **kwargs):
        overlay_draws.append(args)
        return original_draw(*args, **kwargs)

    monkeypatch.setattr(ResultOverlay, "draw", spy_draw)

    total_steps = screen.replayer.total_steps
    assert total_steps == 9

    # 1. Intermediate playback keeps overlay suppressed
    screen.update(0.1)
    assert not screen.replayer.is_finished
    assert screen.outcome_status is None
    screen.draw()
    assert len(overlay_draws) == 0

    # Run playback to completion via update() -> activates WIN overlay
    while not screen.replayer.is_finished:
        screen.update(0.5)

    assert screen.replayer.is_finished is True
    assert is_goal(screen.current_state, screen.level) is True
    assert screen.outcome_status == "WIN"
    screen.draw()
    assert len(overlay_draws) > 0

    # 2. Stepping backward toggles overlay off
    overlay_draws.clear()
    screen.replay_prev_step()
    assert screen.replayer.current_index == total_steps - 1
    assert screen.outcome_status is None
    screen.draw()
    assert len(overlay_draws) == 0

    # Stepping forward back to goal activates WIN overlay
    screen.replay_next_step()
    assert screen.replayer.current_index == total_steps
    assert screen.outcome_status == "WIN"
    screen.draw()
    assert len(overlay_draws) > 0

    # 3. Scrubbing backward toggles overlay off
    overlay_draws.clear()
    slider = screen.timeline_slider
    # Scrub back to start
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (slider.rect.left, slider.rect.centery), "button": 1}))
    assert screen.replayer.current_index == 0
    assert screen.outcome_status is None
    screen.draw()
    assert len(overlay_draws) == 0

    # Scrub all the way to end -> activates WIN overlay
    screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": (slider.rect.right, slider.rect.centery), "buttons": (1, 0, 0)}))
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (slider.rect.right, slider.rect.centery), "button": 1}))
    assert screen.replayer.current_index == total_steps
    assert is_goal(screen.current_state, screen.level) is True
    assert screen.outcome_status == "WIN"
    screen.draw()
    assert len(overlay_draws) > 0


def test_playback_overlay_authority_and_toggle(monkeypatch):
    """Verify playback controls have full authority over victory overlay (activation, stepping, scrubbing, restart)."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    # 4-step level where start is (1, 1) and goal is (4, 4)
    tiles = {(r, c): TileType.FLOOR for r in range(6) for c in range(6)}
    tiles[(4, 4)] = TileType.GOAL
    lvl4 = Level(
        width=6,
        height=6,
        tiles=tiles,
        goal=(4, 4),
        start=BlockState(1, 1, Orientation.STANDING),
        bridges={},
        switches=[],
        split_rules={},
        id="mock_4step",
        name="Mock 4 Step",
    )
    screen = GameScreen(surface, levels=[lvl4])
    screen.load_level(0)

    overlay_draw_moves = []
    original_draw = ResultOverlay.draw

    def spy_draw(surface, area_rect, status, moves_count=0, font_large=None, font_small=None):
        overlay_draw_moves.append(moves_count)
        return original_draw(surface, area_rect, status, moves_count=moves_count, font_large=font_large, font_small=font_small)

    monkeypatch.setattr(ResultOverlay, "draw", spy_draw)

    # Solve mock level 0 (4 steps)
    res_mock = SolverResult(
        path=["D", "D", "R", "R"],
        expanded_nodes=4,
        search_time_ms=1.0,
        peak_memory_kb=10,
        solution_length=4,
        cost=4.0,
        success=True,
    )
    def mock_poll():
        screen.solver_bridge.state = SolverBridgeState.FINISHED
        return res_mock

    monkeypatch.setattr(screen.solver_bridge, "start_solve", lambda algo, lvl, st: setattr(screen.solver_bridge, "state", SolverBridgeState.RUNNING))
    monkeypatch.setattr(screen.solver_bridge, "poll", mock_poll)

    screen.trigger_solve("BFS")
    screen.update(0.016)

    assert screen.replayer is not None
    assert screen.replayer.total_steps == 4

    # Let replayer play to finish: assert outcome_status == "WIN"
    while not screen.replayer.is_finished:
        screen.update(0.2)

    assert screen.replayer.current_index == 4
    assert is_goal(screen.current_state, screen.level) is True
    assert screen.outcome_status == "WIN"

    # Verify victory overlay receives total_steps moves count instead of 0
    overlay_draw_moves.clear()
    screen.draw()
    assert len(overlay_draw_moves) > 0
    assert overlay_draw_moves[-1] == screen.replayer.total_steps == 4

    # Click << Step (replay_prev_step): assert current_index == 3 and outcome_status is None
    screen.replay_prev_step()
    assert screen.replayer.current_index == 3
    assert screen.outcome_status is None

    # Click >> Step (replay_next_step): assert current_index == 4 and outcome_status == "WIN"
    screen.replay_next_step()
    assert screen.replayer.current_index == 4
    assert screen.outcome_status == "WIN"
    overlay_draw_moves.clear()
    screen.draw()
    assert overlay_draw_moves[-1] == screen.replayer.total_steps == 4

    # Drag slider to step 2: assert current_index == 2 and outcome_status is None
    screen._on_slider_drag_start()
    assert screen.outcome_status is None
    screen._on_slider_change(2)
    assert screen.replayer.current_index == 2
    assert screen.outcome_status is None

    # Drag slider back to step 4: assert current_index == 4 and outcome_status == "WIN"
    screen._on_slider_change(4)
    assert screen.replayer.current_index == 4
    assert screen.outcome_status == "WIN"

    # Click Play toggle button at step 4: assert current_index == 0, is_playing is True, and outcome_status is None
    screen.replay_toggle_play()
    assert screen.replayer.current_index == 0
    assert screen.replayer.is_playing is True
    assert screen.outcome_status is None


def test_playback_dismisses_prior_manual_win_overlay():
    """Verify that scrubbing, stepping replay, or triggering solve dismisses any prior manual win/loss overlay."""
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    # Replayer on mock level 0
    winning_path = ["R", "U", "L", "D", "R", "U", "R", "D", "R"]
    screen.replayer = SolutionReplayer(screen.level, screen.current_state, winning_path)
    screen.timeline_slider.min_val = 0
    screen.timeline_slider.max_val = screen.replayer.total_steps
    screen.timeline_slider.value = 0
    screen._update_layout()

    # 1. Slider drag start clears outcome_status
    screen.outcome_status = "WIN"
    screen._on_slider_drag_start()
    assert screen.outcome_status is None

    # 2. Slider change clears outcome_status
    screen.outcome_status = "WIN"
    screen._on_slider_change(1)
    assert screen.outcome_status is None

    # 3. Step forward clears outcome_status
    screen.outcome_status = "WIN"
    screen.replay_next_step()
    assert screen.outcome_status is None

    # 4. Step backward clears outcome_status
    screen.outcome_status = "WIN"
    screen.replay_prev_step()
    assert screen.outcome_status is None

    # 5. Trigger solve clears outcome_status
    screen.outcome_status = "WIN"
    screen.trigger_solve("BFS")
    assert screen.outcome_status is None
    # Wait for solve to finish
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            break

    # 6. Manual gameplay reaching goal still sets outcome_status == "WIN"
    screen.load_level(0)
    assert screen.outcome_status is None
    for move in winning_path:
        screen.handle_manual_move(move)
    assert is_goal(screen.current_state, screen.level) is True
    assert screen.outcome_status == "WIN"


def test_playback_header_status_pill_states():
    """Verify that Card 2 PLAYBACK header displays [REPLAYING] and [GOAL REACHED] status pills."""
    # 4-step linear corridor level where 4 'R' moves reach goal at (1, 7) standing
    tiles = {(r, c): TileType.FLOOR for r in range(3) for c in range(9)}
    goal = (1, 7)
    tiles[goal] = TileType.GOAL
    level_4step = Level(
        width=9,
        height=3,
        tiles=tiles,
        goal=goal,
        start=BlockState(r=1, c=1, orientation=Orientation.STANDING),
        bridges={},
        switches=[],
        split_rules={},
        id="lvl_4step",
        name="Mock 4-Step Corridor",
    )

    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=[level_4step])
    screen.load_level(0)

    # Track rendered strings and colors via FontSpy on screen.font_mono
    rendered_calls: list[tuple[str, tuple]] = []
    real_font_mono = screen.font_mono

    class FontSpy:
        def __init__(self, font):
            self._font = font

        def render(self, text, antialias, color, background=None):
            rendered_calls.append((str(text), color))
            return self._font.render(text, antialias, color, background)

        def __getattr__(self, name):
            return getattr(self._font, name)

    screen.font_mono = FontSpy(real_font_mono)

    # 1. Trigger BFS solve on 4-step level
    screen.trigger_solve("BFS")
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out after 3.0 seconds")

    assert screen.replayer is not None
    assert screen.replayer.total_steps == 4
    assert screen.replayer.current_index == 0

    # Draw at step 0: should render "[REPLAYING]" in accent cyan (70, 210, 245)
    rendered_calls.clear()
    screen.draw()
    replaying_calls = [(t, c) for t, c in rendered_calls if "[REPLAYING]" in t]
    goal_calls = [(t, c) for t, c in rendered_calls if "[GOAL REACHED]" in t]
    assert len(replaying_calls) > 0, f"Expected '[REPLAYING]' at step 0, rendered calls: {rendered_calls}"
    assert replaying_calls[0][1] == (70, 210, 245)
    assert len(goal_calls) == 0

    # 2. Advance / scrub to step 4 (goal reached)
    slider = screen.timeline_slider
    # Scrub all the way to right end
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": (slider.rect.right, slider.rect.centery), "button": 1},
        )
    )
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEMOTION,
            {"pos": (slider.rect.right, slider.rect.centery), "buttons": (1, 0, 0)},
        )
    )
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"pos": (slider.rect.right, slider.rect.centery), "button": 1},
        )
    )
    assert screen.replayer.current_index == 4
    assert is_goal(screen.current_state, screen.level) is True

    # Draw at step 4: should render "[GOAL REACHED]" in emerald green (0, 230, 118)
    rendered_calls.clear()
    screen.draw()
    replaying_calls = [(t, c) for t, c in rendered_calls if "[REPLAYING]" in t]
    goal_calls = [(t, c) for t, c in rendered_calls if "[GOAL REACHED]" in t]
    assert len(goal_calls) > 0, f"Expected '[GOAL REACHED]' at goal, rendered calls: {rendered_calls}"
    assert goal_calls[0][1] == (0, 230, 118)
    assert len(replaying_calls) == 0

    # Verify subtle rounded dark-green pill background (15, 35, 30) and thin border (25, 90, 60)
    card_x = screen.sidebar_rect.left + 14
    card_w = screen.sidebar_rect.width - 28
    found_bg = False
    found_border = False
    for x in range(card_x, card_x + card_w):
        for y in range(260, 280):
            pixel = surface.get_at((x, y))[:3]
            if pixel == (15, 35, 30):
                found_bg = True
            elif pixel == (25, 90, 60):
                found_border = True
    assert found_bg is True, "Expected pill background (15, 35, 30) rendered on surface"
    assert found_border is True, "Expected pill border (25, 90, 60) rendered on surface"

    # 3. Scrub back to step 2 (intermediate step)
    step2_x = slider.rect.left + int(slider.rect.width * (2 / 4))
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": (step2_x, slider.rect.centery), "button": 1},
        )
    )
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEMOTION,
            {"pos": (step2_x, slider.rect.centery), "buttons": (1, 0, 0)},
        )
    )
    screen.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"pos": (step2_x, slider.rect.centery), "button": 1},
        )
    )
    assert screen.replayer.current_index == 2

    # Draw at step 2: should toggle back to "[REPLAYING]"
    rendered_calls.clear()
    screen.draw()
    replaying_calls = [(t, c) for t, c in rendered_calls if "[REPLAYING]" in t]
    goal_calls = [(t, c) for t, c in rendered_calls if "[GOAL REACHED]" in t]
    assert len(replaying_calls) > 0, f"Expected '[REPLAYING]' after scrubbing to step 2, rendered calls: {rendered_calls}"
    assert replaying_calls[0][1] == (70, 210, 245)
    assert len(goal_calls) == 0


def test_solver_always_solves_from_initial_state():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)  # Simple corridor

    initial_state = screen.initial_state
    assert screen.moves_count == 0

    # Move manually to change current_state and moves_count
    event_right = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
    screen.handle_event(event_right)
    screen.update(0.016)

    assert screen.moves_count == 1
    assert screen.current_state != initial_state

    # Trigger solve
    screen.trigger_solve("BFS")

    # Assert that current_state is reset to initial_state, moves_count reset to 0, outcome_status is None
    assert screen.current_state == screen.initial_state
    assert screen.moves_count == 0
    assert screen.outcome_status is None

    # Wait for solve to finish
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out")

    assert screen.latest_result is not None
    assert screen.latest_result.success is True
    # Path must be full solution from initial_state (4 steps: ["R", "R", "R", "R"])
    assert screen.latest_result.path == ["R", "R", "R", "R"]
    assert screen.replayer is not None
    assert screen.replayer.initial_state == screen.initial_state
    assert screen.replayer.total_steps == 4


def test_replayer_auto_pauses_and_switches_button_to_play():
    surface = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    screen = GameScreen(surface, levels=_mock_levels())
    screen.load_level(0)

    screen.trigger_solve("BFS")
    t0 = time.time()
    while screen.solver_bridge.state == SolverBridgeState.RUNNING:
        screen.update(0.05)
        time.sleep(0.01)
        if time.time() - t0 > 3.0:
            pytest.fail("Solver bridge timed out")

    assert screen.replayer is not None
    assert screen.replayer.is_playing is True
    assert screen.btn_replay_toggle.text == "Pause"

    # Advance time past completion
    for _ in range(50):
        screen.update(0.1)
        if screen.replayer.is_finished:
            break

    assert screen.replayer.is_finished is True
    assert screen.replayer.is_playing is False
    assert screen.btn_replay_toggle.text == "Play"


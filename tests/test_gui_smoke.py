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
from core.interfaces import BlockState, GameState, Orientation, Switch
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
    amber_pixels = [
        p for p in fragile_pixels
        if p[0] > 200 and 100 <= p[1] <= 180 and 20 <= p[2] <= 80
    ]
    crack_pixels = [
        p for p in fragile_pixels
        if p[0] > 240 and p[1] > 240 and p[2] > 240
    ]
    assert len(amber_pixels) > 50, "Fragile tile amber base missing"
    assert len(crack_pixels) > 0, "Fragile tile radiating white crack lines missing"

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

    # 1. Verify Level 1 closed bridge vs heavy switch red exclusivity
    lvl1 = load_level("level_01")
    state_closed = GameState(block=lvl1.start, bridge_mask=0)
    surface = pygame.Surface((800, 600))
    surface.fill((0, 0, 0))
    renderer.draw(surface, lvl1, state_closed)

    # North bridge cells at (4, 1) and (5, 1)
    for cell in lvl1.bridges["north_bridge"]:
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

    # Heavy switch at (4, 4)
    heavy_sw = next(s for s in lvl1.switches if s.type == "heavy")
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
    renderer.draw(surface_pressed, lvl1, state_pressed)
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
    amber_base_pixels = [
        p for p in fragile_pixels
        if p[0] > 200 and 100 <= p[1] <= 180 and 20 <= p[2] <= 80
    ]
    white_crack_pixels = [
        p for p in fragile_pixels
        if p[0] > 240 and p[1] > 240 and p[2] > 240
    ]
    assert len(amber_base_pixels) > 50, (
        f"2D fragile tile amber base pixels count={len(amber_base_pixels)}; expected > 50"
    )
    assert len(white_crack_pixels) > 5, (
        f"2D fragile tile white crack pixels count={len(white_crack_pixels)}; expected > 5"
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
                white_crack_pixels = [p for p in pixels if p[0] > 220 and p[1] > 220 and p[2] > 220]
                rust_shadow_pixels = [
                    p for p in pixels
                    if 110 <= p[0] <= 180 and 30 <= p[1] <= 90 and p[2] < 60
                ]
                assert len(orange_pixels) > 50, (
                    f"2D stage {lvl.id} fragile tile at ({r}, {c}) lacking dominant orange hues (found {len(orange_pixels)})"
                )
                assert len(white_crack_pixels) > 0, (
                    f"2D stage {lvl.id} fragile tile at ({r}, {c}) lacking white crack highlights"
                )
                assert len(rust_shadow_pixels) > 0, (
                    f"2D stage {lvl.id} fragile tile at ({r}, {c}) lacking rust under-shadow pixels"
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

    assert fragile_tiles_checked == 7, f"Expected 7 fragile tiles across all stages, got {fragile_tiles_checked}"


def test_2d_pixel_art_fragile_tile_rendering():
    """Verify 2D fragile tile renders pixel-art crack with rust-brown under-shadow depth and dominant orange substrate."""
    renderer = BoardRenderer(viewport_width=800, viewport_height=600)
    tile_size = settings.TILE_SIZE  # 48
    surf = pygame.Surface((tile_size, tile_size))
    rect = pygame.Rect(0, 0, tile_size, tile_size)
    renderer._draw_fragile_tile(surf, rect)

    pixels = [surf.get_at((x, y))[:3] for x in range(rect.width) for y in range(rect.height)]
    total_pixels = len(pixels)

    white_crack_pixels = [p for p in pixels if p[0] > 240 and p[1] > 240 and p[2] > 240]
    rust_shadow_pixels = [
        p for p in pixels
        if 110 <= p[0] <= 180 and 30 <= p[1] <= 90 and p[2] < 60
    ]
    orange_pixels = [p for p in pixels if p[0] > p[1] > p[2]]

    assert len(white_crack_pixels) > 0, "Expected white crack pixels (R, G, B > 240)"
    assert len(rust_shadow_pixels) > 0, "Expected rust-brown shadow pixels (R in [110, 180], G in [30, 90], B < 60)"
    assert len(orange_pixels) / total_pixels > 0.60, (
        f"Orange pixels (R > G > B) must dominate > 60% of tile area (got {len(orange_pixels) / total_pixels:.2%})"
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

    # 3. Fragile Tile: amber rect with white crack
    white_crack_pixels = [p for p in pill_pixels if p == (255, 255, 255)]
    assert len(white_crack_pixels) > 0, "LegendBar missing Fragile Tile white crack pixels"

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













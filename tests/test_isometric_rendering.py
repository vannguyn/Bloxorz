"""Unit tests for IsometricBoardRenderer and 3D isometric rendering pipeline."""
import pygame
import pytest

from core.interfaces import BlockState, GameState, Level, Orientation, Switch, TileType
from rendering.isometric_board_renderer import IsometricBoardRenderer
from rendering.isometric_block_renderer import IsometricBlockRenderer
from config import settings


@pytest.fixture(scope="session", autouse=True)
def init_pygame():
    """Initializes pygame headless for testing."""
    pygame.init()
    yield
    pygame.quit()


def create_test_level() -> Level:
    """Creates a small mock level containing all tile and switch types."""
    # 4x4 grid with floor, fragile, bridge, goal, and switches
    tiles: dict[tuple[int, int], TileType] = {
        (0, 0): TileType.FLOOR,
        (0, 1): TileType.FLOOR,
        (0, 2): TileType.FRAGILE,
        (1, 0): TileType.FLOOR,
        (1, 1): TileType.FLOOR,
        (1, 2): TileType.BRIDGE,
        (2, 0): TileType.FLOOR,
        (2, 1): TileType.FLOOR,
        (2, 2): TileType.GOAL,
    }
    bridges = {
        "b1": [(1, 2)],
    }
    switches = [
        Switch(id="sw_soft", type="soft", position=(0, 0), bridge_ids=["b1"], mode="toggle"),
        Switch(id="sw_heavy", type="heavy", position=(1, 0), bridge_ids=["b1"], mode="toggle"),
        Switch(id="sw_split", type="split", position=(2, 0), bridge_ids=[], mode="toggle"),
    ]
    start = BlockState(r=0, c=0, orientation=Orientation.STANDING)
    return Level(
        width=3,
        height=3,
        tiles=tiles,
        goal=(2, 2),
        start=start,
        bridges=bridges,
        switches=switches,
        split_rules={},
    )


class TestIsometricBoardRenderer:
    def test_projection_formula_2_to_1(self):
        """Validates 2:1 dimetric projection coordinates against analytical math."""
        renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        renderer.origin_x = 400
        renderer.origin_y = 200
        renderer.tile_size = 60

        # tile_w = 60, tile_h = 30, tile_elev = 30
        # px = 400 + (c - r) * 30
        # py = 200 + (c + r) * 15 - z * 30

        # Origin point (0, 0, 0)
        assert renderer.project(0, 0, 0.0) == (400, 200)

        # Step along columns: (0, 1, 0) -> px = 400 + 30 = 430, py = 200 + 15 = 215
        assert renderer.project(0, 1, 0.0) == (430, 215)

        # Step along rows: (1, 0, 0) -> px = 400 - 30 = 370, py = 200 + 15 = 215
        assert renderer.project(1, 0, 0.0) == (370, 215)

        # Elevation step: z = 1.0 -> px = 400, py = 200 - 30 = 170
        assert renderer.project(0, 0, 1.0) == (400, 170)

        # Fractional coordinates: center of (0, 0) is (0.5, 0.5, 0.0)
        # px = 400 + (0.5 - 0.5) * 30 = 400
        # py = 200 + (0.5 + 0.5) * 15 = 215
        assert renderer.cell_center(0, 0, 0.0) == (400, 215)
        assert renderer.cell_center(0, 0, 0.0) == renderer.project(0.5, 0.5, 0.0)

    def test_tile_corners_order(self):
        """Corners must return 4 points forming a diamond in clockwise order."""
        renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        renderer.origin_x = 400
        renderer.origin_y = 200
        renderer.tile_size = 40

        corners = renderer.tile_corners(1, 2, 0.0)
        assert len(corners) == 4
        assert corners[0] == renderer.project(1, 2, 0.0)      # Top
        assert corners[1] == renderer.project(1, 3, 0.0)      # Right
        assert corners[2] == renderer.project(2, 3, 0.0)      # Bottom
        assert corners[3] == renderer.project(2, 2, 0.0)      # Left

    def test_compute_layout_centers_board(self):
        """Board layout must be centered inside the given area_rect with valid tile_size."""
        renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        area_rect = pygame.Rect(50, 50, 700, 500)

        origin_x, origin_y, tile_size = renderer.compute_layout(level, area_rect)

        assert tile_size >= 16
        assert renderer.origin_x == origin_x
        assert renderer.origin_y == origin_y

        # Collect all tile diamond corner projections at z=0
        all_x = []
        all_y = []
        for r, c in level.tiles.keys():
            for px, py in renderer.tile_corners(r, c, 0.0):
                all_x.append(px)
                all_y.append(py)

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        # Must fit completely within area_rect
        assert min_x >= area_rect.left
        assert max_x <= area_rect.right
        assert min_y >= area_rect.top
        assert max_y <= area_rect.bottom

        # Centering check: center of bounding box should be within 4px of area_rect center
        center_x = (min_x + max_x) / 2
        assert abs(center_x - area_rect.centerx) <= 4

    def test_draw_renders_without_crash_and_produces_pixels(self):
        """Surface must contain non-background pixels after drawing."""
        renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        state = GameState(
            block=BlockState(r=0, c=0, orientation=Orientation.STANDING),
            bridge_mask=0,
        )

        surf = pygame.Surface((800, 600))
        bg_color = (0, 0, 0)
        surf.fill(bg_color)

        area_rect = pygame.Rect(0, 0, 800, 600)
        renderer.draw(surf, level, state, area_rect)

        # Count non-black pixels
        non_bg_pixels = 0
        for x in range(0, 800, 10):
            for y in range(0, 600, 10):
                if surf.get_at((x, y))[:3] != bg_color:
                    non_bg_pixels += 1

        assert non_bg_pixels > 50

    def test_draw_bridge_open_vs_closed_differentiation(self):
        """Open bridges and closed bridges must render distinct pixel outputs."""
        renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()

        # Closed bridge
        state_closed = GameState(
            block=BlockState(r=0, c=0, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        surf_closed = pygame.Surface((800, 600))
        surf_closed.fill((0, 0, 0))
        renderer.draw(surf_closed, level, state_closed)

        # Open bridge
        state_open = GameState(
            block=BlockState(r=0, c=0, orientation=Orientation.STANDING),
            bridge_mask=1,
        )
        surf_open = pygame.Surface((800, 600))
        surf_open.fill((0, 0, 0))
        renderer.draw(surf_open, level, state_open)

        # Verify pixels at bridge position (1, 2) differ
        bx, by = renderer.cell_center(1, 2, 0.0)
        color_closed = surf_closed.get_at((bx, by))
        color_open = surf_open.get_at((bx, by))
        assert color_closed != color_open

    def test_all_10_real_levels_render_successfully(self):
        """All 10 real json levels must compute layout and render without exceptions."""
        from levels.level_loader import load_level, compute_initial_bridge_mask

        renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        for i in range(1, 11):
            lvl = load_level(f"level_{i:02d}")
            init_mask = lvl.initial_bridge_mask
            st = GameState(block=lvl.start, bridge_mask=init_mask)
            surf = pygame.Surface((800, 600))
            renderer.draw(surf, lvl, st)
            assert renderer.tile_size >= 16


class TestIsometricBlockRenderer:
    def test_standing_block_renders_and_has_vertical_height(self):
        """A standing block should render with height=2.0 above its base tile."""
        board_renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        board_renderer.compute_layout(level)

        block_renderer = IsometricBlockRenderer(board_renderer)
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )

        surf = pygame.Surface((800, 600))
        surf.fill((0, 0, 0))
        block_renderer.draw(surf, state)

        # Check that top center of standing block (z ~ 1.5 - 2.0) contains non-black pixels
        top_center_x, top_center_y = board_renderer.project(1.5, 1.5, 1.8)
        assert surf.get_at((top_center_x, top_center_y))[:3] != (0, 0, 0)

        # Count drawn pixels across block region
        drawn = sum(
            1 for x in range(top_center_x - 30, top_center_x + 30, 2)
            for y in range(top_center_y - 30, top_center_y + 60, 2)
            if surf.get_at((x, y))[:3] != (0, 0, 0)
        )
        assert drawn > 50

    def test_lying_blocks_geometry(self):
        """LYING_H (2 cols) and LYING_V (2 rows) must render across their occupied cells."""
        board_renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        board_renderer.compute_layout(level)
        block_renderer = IsometricBlockRenderer(board_renderer)

        # LYING_H at (0, 0): spans (0, 0) and (0, 1)
        state_h = GameState(
            block=BlockState(r=0, c=0, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        surf_h = pygame.Surface((800, 600))
        surf_h.fill((0, 0, 0))
        block_renderer.draw(surf_h, state_h)

        # Both cell centers at z=0.8 should have block pixels
        p1 = board_renderer.project(0.5, 0.5, 0.8)
        p2 = board_renderer.project(0.5, 1.5, 0.8)
        assert surf_h.get_at(p1)[:3] != (0, 0, 0)
        assert surf_h.get_at(p2)[:3] != (0, 0, 0)

        # LYING_V at (0, 0): spans (0, 0) and (1, 0)
        state_v = GameState(
            block=BlockState(r=0, c=0, orientation=Orientation.LYING_V),
            bridge_mask=0,
        )
        surf_v = pygame.Surface((800, 600))
        surf_v.fill((0, 0, 0))
        block_renderer.draw(surf_v, state_v)

        pv1 = board_renderer.project(0.5, 0.5, 0.8)
        pv2 = board_renderer.project(1.5, 0.5, 0.8)
        assert surf_v.get_at(pv1)[:3] != (0, 0, 0)
        assert surf_v.get_at(pv2)[:3] != (0, 0, 0)

    def test_split_cubes_and_active_cube_highlight(self):
        """Split cubes must both render, and the active cube must have golden highlight."""
        board_renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        board_renderer.compute_layout(level)
        block_renderer = IsometricBlockRenderer(board_renderer)

        # Split: cube 0 at (0, 0) [active], cube 1 at (2, 1) [inactive]
        state_0_active = GameState(
            block=BlockState(
                r=0, c=0, orientation=Orientation.STANDING,
                is_split=True, cube_positions=((0, 0), (2, 1)), active_cube=0
            ),
            bridge_mask=0,
        )
        surf_0 = pygame.Surface((800, 600))
        surf_0.fill((0, 0, 0))
        block_renderer.draw(surf_0, state_0_active)

        # Split: cube 0 inactive, cube 1 active
        state_1_active = GameState(
            block=BlockState(
                r=0, c=0, orientation=Orientation.STANDING,
                is_split=True, cube_positions=((0, 0), (2, 1)), active_cube=1
            ),
            bridge_mask=0,
        )
        surf_1 = pygame.Surface((800, 600))
        surf_1.fill((0, 0, 0))
        block_renderer.draw(surf_1, state_1_active)

        # Both positions must be drawn
        p_c0 = board_renderer.project(0.5, 0.5, 0.5)
        p_c1 = board_renderer.project(2.5, 1.5, 0.5)
        assert surf_0.get_at(p_c0)[:3] != (0, 0, 0)
        assert surf_0.get_at(p_c1)[:3] != (0, 0, 0)

        # Cube 0 top face center when active vs inactive should be visibly different (e.g. golden badge)
        p_badge_0 = board_renderer.project(0.5, 0.5, 1.0)
        color_active = surf_0.get_at(p_badge_0)[:3]
        color_inactive = surf_1.get_at(p_badge_0)[:3]
        assert color_active != color_inactive

    def test_transition_interpolation_lift_and_lerp(self):
        """Transition interpolation must smoothly move block and apply parabolic lift."""
        board_renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        board_renderer.compute_layout(level)
        block_renderer = IsometricBlockRenderer(board_renderer)

        start_state = GameState(
            block=BlockState(r=0, c=0, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        end_state = GameState(
            block=BlockState(r=0, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )

        # Render at intermediate progress steps without exception
        surfaces = []
        for prog in [0.0, 0.25, 0.5, 0.75, 1.0]:
            surf = pygame.Surface((800, 600))
            surf.fill((0, 0, 0))
            block_renderer.draw(surf, start_state, transition_to=end_state, progress=prog)
            surfaces.append(surf)

        # Check midpoint (prog=0.5) has lift:
        # At t=0.5, r=0, c=0.5, orientation snaps to LYING_H (h=1), lift ~ 0.25 - 0.35.
        # Top of the block should be higher than a resting LYING_H block at z=0.
        surf_mid = surfaces[2]
        # Midpoint top face center: r=0.5, c=1.5, z=1.0 + lift ~ 1.35
        p_elevated = board_renderer.project(0.5, 1.5, 1.3)
        assert surf_mid.get_at(p_elevated)[:3] != (0, 0, 0)

    def test_transition_progress_clamping(self):
        """Progress values outside [0.0, 1.0] must be clamped without error."""
        board_renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
        level = create_test_level()
        board_renderer.compute_layout(level)
        block_renderer = IsometricBlockRenderer(board_renderer)

        s1 = GameState(block=BlockState(r=1, c=1, orientation=Orientation.STANDING), bridge_mask=0)
        s2 = GameState(block=BlockState(r=1, c=2, orientation=Orientation.STANDING), bridge_mask=0)

        surf = pygame.Surface((800, 600))
        block_renderer.draw(surf, s1, transition_to=s2, progress=-0.5)
        block_renderer.draw(surf, s1, transition_to=s2, progress=1.5)


def test_visual_redesign_tokens_defined_and_valid():
    """Verify newly introduced visual affordance redesign design tokens are defined and valid RGB."""
    expected_tokens = {
        "COLOR_GOAL_WALL_LEFT": (18, 22, 32),
        "COLOR_GOAL_WALL_RIGHT": (28, 34, 48),
        "COLOR_GOAL_ABYSS": (6, 8, 12),
        "COLOR_BRIDGE_DOCK_RAIL": (35, 60, 80),
        "COLOR_BRIDGE_DOCK_PIN": (45, 85, 110),
        "COLOR_FRAGILE_STRIPE": (255, 185, 45),
        "COLOR_SWITCH_PEDESTAL": (70, 50, 10),
        "COLOR_SWITCH_HEAVY_BASE": (45, 50, 60),
    }
    for name, expected_val in expected_tokens.items():
        assert hasattr(settings, name), f"Missing design token {name} in config.settings"
        val = getattr(settings, name)
        assert isinstance(val, tuple), f"{name} must be a tuple"
        assert len(val) == 3, f"{name} must have 3 elements (RGB)"
        assert all(isinstance(c, int) and 0 <= c <= 255 for c in val), f"{name} components must be ints in [0, 255]"
        assert val == expected_val, f"{name} has unexpected value {val}, expected {expected_val}"


def test_visual_patch_tokens_defined_and_valid():
    """Verify patch visual tokens are defined, have correct tuple length (3 or 4),
    elements are ints in [0, 255], and match expected color values.
    """
    expected_tokens = {
        "COLOR_GLASS_FILL": (245, 130, 45, 185),
        "COLOR_GLASS_CRACK": (255, 255, 255, 230),
        "COLOR_GLASS_BORDER": (255, 160, 60),
        "COLOR_SPLIT_CYAN": (56, 189, 248),
        "COLOR_SPLIT_DARK": (2, 132, 199),
        "COLOR_HEAVY_RED": (239, 68, 68),
        "COLOR_HEAVY_DARKRED": (153, 27, 27),
        "COLOR_HEAVY_BASE": (71, 85, 105),
    }
    for name, expected_val in expected_tokens.items():
        assert hasattr(settings, name), f"Missing patch token {name} in config.settings"
        val = getattr(settings, name)
        assert isinstance(val, tuple), f"{name} must be a tuple"
        assert len(val) in (3, 4), f"{name} must have 3 (RGB) or 4 (RGBA) elements"
        assert len(val) == len(expected_val), f"{name} length mismatch: got {len(val)}, expected {len(expected_val)}"
        assert all(isinstance(c, int) and 0 <= c <= 255 for c in val), f"{name} components must be ints in [0, 255]"
        assert val == expected_val, f"{name} has unexpected value {val}, expected {expected_val}"


def test_3d_special_cells_visual_redesign():
    """Verify 3D isometric special cells redesign:
    1. Closed bridge: 0 red pixels, sunken docking rails and guide pins rendered.
    2. Fragile tile: 3D side wall depth halved compared to floor slab; full-span hazard stripes rendered.
    3. Goal tile: optical shaft interior wall colors (left/right walls, abyss floor) rendered.
    4. Switches: tactile depression and visual response when block is standing on switch vs away.
    """
    surface = pygame.Surface((800, 600))
    renderer = IsometricBoardRenderer(800, 600)
    level = create_test_level()

    # 1. Closed Bridge: 0 red pixels and docking features present
    state_closed = GameState(
        block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface.fill((0, 0, 0))
    renderer.draw(surface, level, state_closed)

    bridge_rect = renderer.get_cell_rect(1, 2)
    bridge_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(bridge_rect.left, bridge_rect.right)
        for y in range(bridge_rect.top, bridge_rect.bottom)
    ]
    red_pixels = [
        p for p in bridge_pixels
        if p == (130, 50, 60) or p == (120, 50, 60) or (p[0] > 110 and p[1] < 70 and p[2] < 70)
    ]
    assert len(red_pixels) == 0, f"Found red pixels in closed bridge: {red_pixels[:5]}"

    has_dock_features = any(
        p in (settings.COLOR_BRIDGE_DOCK_RAIL, settings.COLOR_BRIDGE_DOCK_PIN)
        for p in bridge_pixels
    )
    assert has_dock_features, "Closed bridge should render docking rail or pin features"

    # 2. Fragile Tile: side wall depth strictly 35% of floor slab; amber glass and white fracture cracks present
    standard_depth = renderer.get_slab_depth(TileType.FLOOR)
    fragile_depth = renderer.get_slab_depth(TileType.FRAGILE)
    assert fragile_depth == max(2, round(standard_depth * 0.35)), (
        f"Fragile slab depth {fragile_depth} should be strictly 35% relative to standard {standard_depth}"
    )

    fragile_rect = renderer.get_cell_rect(0, 2)
    fragile_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(fragile_rect.left, fragile_rect.right)
        for y in range(fragile_rect.top, fragile_rect.bottom)
    ]
    has_cracks = any(p[0] > 240 and p[1] > 240 and p[2] > 240 for p in fragile_pixels)
    assert has_cracks, "Fragile tile diamond should render white fracture crack lines"
    has_amber = any(p[0] > 200 and 100 <= p[1] <= 180 and p[2] < 80 for p in fragile_pixels)
    assert has_amber, "Fragile tile diamond should render amber glass fill"

    # 3. Goal Tile: shaft interior wall colors present
    goal_rect = renderer.get_cell_rect(2, 2)
    goal_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(goal_rect.left, goal_rect.right)
        for y in range(goal_rect.top, goal_rect.bottom)
    ]
    assert any(p == settings.COLOR_GOAL_WALL_LEFT for p in goal_pixels), "Goal left interior wall color missing"
    assert any(p == settings.COLOR_GOAL_WALL_RIGHT for p in goal_pixels), "Goal right interior wall color missing"
    assert any(p == settings.COLOR_GOAL_ABYSS for p in goal_pixels), "Goal bottom abyss floor color missing"

    # 4. Switches: tactile depression and visual change when standing on switch vs away
    # Test soft switch at (0, 0)
    sw_soft_rect = renderer.get_cell_rect(0, 0)
    state_sw_away = GameState(
        block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface.fill((0, 0, 0))
    renderer.draw(surface, level, state_sw_away)
    pixels_soft_away = [
        surface.get_at((x, y))[:3]
        for x in range(sw_soft_rect.left, sw_soft_rect.right)
        for y in range(sw_soft_rect.top, sw_soft_rect.bottom)
    ]

    state_sw_soft_on = GameState(
        block=BlockState(r=0, c=0, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface.fill((0, 0, 0))
    renderer.draw(surface, level, state_sw_soft_on)
    pixels_soft_on = [
        surface.get_at((x, y))[:3]
        for x in range(sw_soft_rect.left, sw_soft_rect.right)
        for y in range(sw_soft_rect.top, sw_soft_rect.bottom)
    ]
    assert pixels_soft_away != pixels_soft_on, "Soft switch should render differently when pressed"

    # Test heavy switch at (1, 0)
    sw_heavy_rect = renderer.get_cell_rect(1, 0)
    pixels_heavy_away = [
        surface.get_at((x, y))[:3]
        for x in range(sw_heavy_rect.left, sw_heavy_rect.right)
        for y in range(sw_heavy_rect.top, sw_heavy_rect.bottom)
    ]
    state_sw_heavy_on = GameState(
        block=BlockState(r=1, c=0, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface.fill((0, 0, 0))
    renderer.draw(surface, level, state_sw_heavy_on)
    pixels_heavy_on = [
        surface.get_at((x, y))[:3]
        for x in range(sw_heavy_rect.left, sw_heavy_rect.right)
        for y in range(sw_heavy_rect.top, sw_heavy_rect.bottom)
    ]
    assert pixels_heavy_away != pixels_heavy_on, "Heavy switch should render differently when pressed"


def test_redesign_3d_special_cells():
    """Alias for test_3d_special_cells_visual_redesign to satisfy -k 'redesign_3d' filter."""
    test_3d_special_cells_visual_redesign()


def test_closed_bridge_vs_heavy_switch_red_exclusivity_3d():
    """Assert closed bridge has 0 red pixels (r > 150 and g < 100 and b < 100),
    while heavy switch has > 10 red pixels in 3D mode.
    Also verifies all 10 real production levels render cleanly in 3D mode with overhauled visuals.
    """
    from levels.level_loader import load_level, load_all_levels

    renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
    block_renderer = IsometricBlockRenderer(renderer)

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
            f"3D closed bridge cell {cell} contained {len(red_pixels)} red pixels; strictly 0 expected"
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
        f"3D heavy switch at {heavy_sw.position} had {len(heavy_red_pixels)} red pixels; expected > 10"
    )

    # Switch tactile depression visual differentiation
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
    assert pixels_unpressed != pixels_pressed, "Heavy switch visual output must change upon tactile depression"

    # 2. Verify all 10 real production levels render cleanly in 3D mode
    all_levels = load_all_levels()
    assert len(all_levels) == 10
    for lvl in all_levels:
        surf = pygame.Surface((800, 600))
        st = GameState(block=lvl.start, bridge_mask=lvl.initial_bridge_mask)
        renderer.draw(surf, lvl, st)
        block_renderer.draw(surf, st)
        raw = pygame.image.tobytes(surf, "RGB")
        assert any(b > 0 for b in raw), f"3D rendering for {lvl.id} produced empty surface"


def test_3d_amber_glass_and_switch_patch():
    """Validates Task 3 3D Isometric visual patch:
    1. get_slab_depth(TileType.FRAGILE) == max(2, round(d * 0.35)).
    2. Fragile tile renders amber glass and white fracture crack lines.
    3. Heavy switch in 3D uses COLOR_HEAVY_BASE and COLOR_HEAVY_RED.
    4. Split switch in 3D renders arched wings with COLOR_SPLIT_CYAN and center void groove,
       and visually depresses/compresses when pressed.
    """
    renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
    d = renderer.get_slab_depth(TileType.FLOOR)
    expected_fragile_d = max(2, round(d * 0.35))
    assert renderer.get_slab_depth(TileType.FRAGILE) == expected_fragile_d

    surface = pygame.Surface((800, 600))
    surface.fill((0, 0, 0))
    level = create_test_level()
    state = GameState(
        block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    renderer.draw(surface, level, state)

    # 1. Fragile tile: white cracks and amber tones
    fragile_rect = renderer.get_cell_rect(0, 2)
    fragile_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(fragile_rect.left, fragile_rect.right)
        for y in range(fragile_rect.top, fragile_rect.bottom)
    ]
    white_cracks = [
        p for p in fragile_pixels
        if p[0] > 240 and p[1] > 240 and p[2] > 240
    ]
    assert len(white_cracks) > 0, "Fragile top diamond should contain white fracture crack pixels"

    amber_pixels = [
        p for p in fragile_pixels
        if p[0] > 200 and 100 <= p[1] <= 180 and p[2] < 80
    ]
    assert len(amber_pixels) > 0, "Fragile top diamond should contain amber glass pixels"

    # 2. Heavy switch in 3D: COLOR_HEAVY_BASE and COLOR_HEAVY_RED
    heavy_rect = renderer.get_cell_rect(1, 0)
    heavy_pixels = [
        surface.get_at((x, y))[:3]
        for x in range(heavy_rect.left, heavy_rect.right)
        for y in range(heavy_rect.top, heavy_rect.bottom)
    ]
    assert settings.COLOR_HEAVY_BASE in heavy_pixels, "Heavy switch base should contain COLOR_HEAVY_BASE"
    assert settings.COLOR_HEAVY_RED in heavy_pixels, "Heavy switch arms should contain COLOR_HEAVY_RED"

    # 3. Split switch in 3D: COLOR_SPLIT_CYAN, void groove, and tactile/compression response
    split_rect = renderer.get_cell_rect(2, 0)
    pixels_split_unpressed = [
        surface.get_at((x, y))[:3]
        for x in range(split_rect.left, split_rect.right)
        for y in range(split_rect.top, split_rect.bottom)
    ]
    assert settings.COLOR_SPLIT_CYAN in pixels_split_unpressed, "Split switch should contain COLOR_SPLIT_CYAN"
    assert (15, 23, 42) in pixels_split_unpressed, "Split switch should contain center void groove (15, 23, 42)"

    state_split_pressed = GameState(
        block=BlockState(r=2, c=0, orientation=Orientation.STANDING),
        bridge_mask=0,
    )
    surface_split_pressed = pygame.Surface((800, 600))
    surface_split_pressed.fill((0, 0, 0))
    renderer.draw(surface_split_pressed, level, state_split_pressed)
    pixels_split_pressed = [
        surface_split_pressed.get_at((x, y))[:3]
        for x in range(split_rect.left, split_rect.right)
        for y in range(split_rect.top, split_rect.bottom)
    ]
    assert pixels_split_unpressed != pixels_split_pressed, "Split switch should render differently when pressed"


def test_patch_3d_amber_glass_and_switch():
    """Alias for -k patch_3d filter compatibility."""
    test_3d_amber_glass_and_switch_patch()


def test_all_10_stages_visual_patch_regression_3d():
    """Validates visual patch regression across all 10 real production stages in 3D:
    1. All 10 stages render cleanly without exceptions in 3D mode with board and block.
    2. Fragile tiles in stages contain predominantly orange hues (R > G > B) and white crack highlights (R, G, B > 220).
    3. Heavy switches and Split switches visibly alter pixel representation upon block contact.
    4. Heavy switches contain COLOR_HEAVY_BASE and COLOR_HEAVY_RED; Split switches contain COLOR_SPLIT_CYAN.
    """
    from levels.level_loader import load_all_levels

    all_levels = load_all_levels()
    assert len(all_levels) == 10

    renderer = IsometricBoardRenderer(viewport_width=800, viewport_height=600)
    block_renderer = IsometricBlockRenderer(renderer)

    for lvl in all_levels:
        surf = pygame.Surface((800, 600))
        st = GameState(block=lvl.start, bridge_mask=lvl.initial_bridge_mask)
        renderer.draw(surf, lvl, st)
        block_renderer.draw(surf, st)
        raw = pygame.image.tobytes(surf, "RGB")
        assert any(b > 0 for b in raw), f"3D rendering for {lvl.id} produced empty surface"

        # Check fragile tiles in this stage
        for (r, c), tile_type in lvl.tiles.items():
            if tile_type == TileType.FRAGILE:
                rect = renderer.get_cell_rect(r, c)
                pixels = [
                    surf.get_at((x, y))[:3]
                    for x in range(rect.left, rect.right)
                    for y in range(rect.top, rect.bottom)
                ]
                orange_pixels = [p for p in pixels if p[0] > p[1] > p[2]]
                white_crack_pixels = [p for p in pixels if p[0] > 220 and p[1] > 220 and p[2] > 220]
                assert len(orange_pixels) > 20, (
                    f"3D stage {lvl.id} fragile tile at ({r}, {c}) lacking dominant orange hues (found {len(orange_pixels)})"
                )
                assert len(white_crack_pixels) > 0, (
                    f"3D stage {lvl.id} fragile tile at ({r}, {c}) lacking white crack highlights"
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
                    f"3D switch {sw.id} ({sw.type}) in {lvl.id} did not alter pixel representation upon contact"
                )

                if sw.type == "heavy":
                    assert any(p == settings.COLOR_HEAVY_BASE for p in pix_unpressed), (
                        f"3D Heavy switch in {lvl.id} missing COLOR_HEAVY_BASE"
                    )
                    assert any(p == settings.COLOR_HEAVY_RED for p in pix_unpressed), (
                        f"3D Heavy switch in {lvl.id} missing COLOR_HEAVY_RED"
                    )
                elif sw.type == "split":
                    assert any(p == settings.COLOR_SPLIT_CYAN for p in pix_unpressed), (
                        f"3D Split switch in {lvl.id} missing COLOR_SPLIT_CYAN"
                    )







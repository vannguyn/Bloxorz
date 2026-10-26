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


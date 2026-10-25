"""Unit tests for IsometricBoardRenderer and 3D isometric rendering pipeline."""
import pygame
import pytest

from core.interfaces import BlockState, GameState, Level, Orientation, Switch, TileType
from rendering.isometric_board_renderer import IsometricBoardRenderer


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

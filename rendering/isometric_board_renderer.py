"""
3D Isometric Board Renderer for Bloxorz.
Draws floor, goal, fragile tiles, bridges (open/closed), and switches (soft, heavy, split)
using a 2:1 dimetric isometric projection and painter's algorithm depth sorting.
"""
from __future__ import annotations

import pygame
from core.interfaces import GameState, Level, Switch, TileType
from config import settings


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Applies a lighting shade factor (0.0 to 1.0) to an RGB tuple."""
    return (
        max(0, min(255, round(color[0] * factor))),
        max(0, min(255, round(color[1] * factor))),
        max(0, min(255, round(color[2] * factor))),
    )


class IsometricBoardRenderer:
    """Renders the grid board and mechanism tiles in 2:1 isometric projection."""

    def __init__(self, viewport_width: int, viewport_height: int):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.tile_size = settings.TILE_SIZE
        self.origin_x = 0
        self.origin_y = 0

    def compute_layout(self, level: Level, area_rect: pygame.Rect | None = None) -> tuple[int, int, int]:
        """Calculates origin_x, origin_y, and tile_size to center the isometric board in area_rect."""
        rect = area_rect or pygame.Rect(0, 0, self.viewport_width, self.viewport_height)
        avail_w = rect.width - 2 * settings.BOARD_MARGIN
        avail_h = rect.height - 2 * settings.BOARD_MARGIN

        # Collect all active grid cells
        all_cells = set(level.tiles.keys())
        for b_tiles in level.bridges.values():
            all_cells.update(b_tiles)
        if not all_cells:
            all_cells = {(r, c) for r in range(max(1, level.height)) for c in range(max(1, level.width))}

        # Dimetric projection coordinate bounds
        # For each cell (r, c), u in [c - r - 1, c - r + 1], v in [c + r, c + r + 2]
        min_u = min(c - r - 1 for r, c in all_cells)
        max_u = max(c - r + 1 for r, c in all_cells)
        min_v = min(c + r for r, c in all_cells)
        max_v = max(c + r + 2 for r, c in all_cells)

        delta_u = max(1, max_u - min_u)
        delta_v = max(1, max_v - min_v)

        # Scale tile_size to fit viewport width and height
        # Width span = delta_u * (tile_size * 0.5)
        # Height span = delta_v * (tile_size * 0.25) + extrusion (0.15) + standing block & hop (1.2)
        max_size_w = avail_w / (delta_u * 0.5)
        max_size_h = avail_h / (delta_v * 0.25 + 1.35)
        tile_size = max(16, min(settings.TILE_SIZE, int(min(max_size_w, max_size_h))))

        tile_w = tile_size
        tile_h = tile_size * 0.5
        d = max(4, round(tile_size * 0.15))

        # Center horizontally: (min_u + max_u)/2 * (tile_w * 0.5) is the relative horizontal midpoint
        mid_x_rel = ((min_u + max_u) / 2.0) * (tile_w * 0.5)
        origin_x = round(rect.centerx - mid_x_rel)

        # Center vertically: account for tile vertical span plus extrusion and block headroom
        y_min_rel = min_v * (tile_h * 0.5) - tile_size
        y_max_rel = max_v * (tile_h * 0.5) + d
        mid_y_rel = (y_min_rel + y_max_rel) / 2.0
        origin_y = round(rect.centery - mid_y_rel)

        self.tile_size = tile_size
        self.origin_x = origin_x
        self.origin_y = origin_y
        return origin_x, origin_y, tile_size

    def project(self, r: float, c: float, z: float = 0.0) -> tuple[int, int]:
        """Dimetric 2:1 projection from grid (r, c, z) to screen coordinates (px, py)."""
        tile_w = self.tile_size
        tile_h = self.tile_size * 0.5
        tile_elev = self.tile_size * 0.5

        px = self.origin_x + (c - r) * (tile_w * 0.5)
        py = self.origin_y + (c + r) * (tile_h * 0.5) - z * tile_elev
        return round(px), round(py)

    def tile_corners(self, r: float, c: float, z: float = 0.0) -> list[tuple[int, int]]:
        """Returns the 4 screen points forming the top diamond of cell (r, c) at elevation z.

        Order: [Top (r, c), Right (r, c+1), Bottom (r+1, c+1), Left (r+1, c)].
        """
        return [
            self.project(r, c, z),
            self.project(r, c + 1, z),
            self.project(r + 1, c + 1, z),
            self.project(r + 1, c, z),
        ]

    def cell_center(self, r: float, c: float, z: float = 0.0) -> tuple[int, int]:
        """Returns the screen center coordinates of cell (r, c) at elevation z."""
        return self.project(r + 0.5, c + 0.5, z)

    def get_cell_rect(self, row: int, col: int) -> pygame.Rect:
        """Returns the screen bounding Rect for a cell diamond at z=0."""
        corners = self.tile_corners(row, col, 0.0)
        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]
        d = max(4, round(self.tile_size * 0.15))
        return pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys) + d)

    def draw(
        self,
        surface: pygame.Surface,
        level: Level,
        state: GameState,
        area_rect: pygame.Rect | None = None,
    ) -> None:
        """Draws all board tiles, bridges, and switches in depth-sorted isometric view."""
        self.compute_layout(level, area_rect)

        # Bridge status map
        bridge_index_map = {b_id: i for i, b_id in enumerate(level.bridges.keys())}
        bridge_cell_status: dict[tuple[int, int], bool] = {}
        for b_id, b_tiles in level.bridges.items():
            b_idx = bridge_index_map.get(b_id, 0)
            is_open = bool(state.bridge_mask & (1 << b_idx))
            for cell in b_tiles:
                bridge_cell_status[cell] = is_open

        # Switches map
        switches_by_pos = {sw.position: sw for sw in level.switches}

        # Combine all tiles
        all_cells: dict[tuple[int, int], TileType] = dict(level.tiles)
        for b_id, b_tiles in level.bridges.items():
            for cell in b_tiles:
                if cell not in all_cells:
                    all_cells[cell] = TileType.BRIDGE

        # Painter's Algorithm Depth Sort: sort by key (r + c, r) ascending
        sorted_cells = sorted(all_cells.keys(), key=lambda pos: (pos[0] + pos[1], pos[0]))

        d = max(4, round(self.tile_size * 0.15))

        for r, c in sorted_cells:
            tile_type = all_cells[(r, c)]
            if tile_type == TileType.VOID:
                continue

            corners = self.tile_corners(r, c, 0.0)
            p_top, p_right, p_bottom, p_left = corners

            if tile_type == TileType.BRIDGE:
                is_open = bridge_cell_status.get((r, c), False)
                self._draw_bridge_tile(surface, corners, d, is_open)
            elif tile_type == TileType.FLOOR:
                self._draw_floor_tile(surface, corners, d)
            elif tile_type == TileType.FRAGILE:
                self._draw_fragile_tile(surface, corners, d)
            elif tile_type == TileType.GOAL:
                self._draw_goal_tile(surface, corners, d)

            # Switches drawn on top of tile diamond
            if (r, c) in switches_by_pos:
                self._draw_switch(surface, (r, c), switches_by_pos[(r, c)])

    def _draw_side_walls(
        self,
        surface: pygame.Surface,
        corners: list[tuple[int, int]],
        d: int,
        base_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
    ) -> None:
        """Draws shaded left and right vertical extrusion walls."""
        _p_top, p_right, p_bottom, p_left = corners

        # Left face: [p_left, p_bottom, p_bottom + d, p_left + d]
        left_poly = [
            p_left,
            p_bottom,
            (p_bottom[0], p_bottom[1] + d),
            (p_left[0], p_left[1] + d),
        ]
        color_left = _shade(base_color, 0.75)
        pygame.draw.polygon(surface, color_left, left_poly)
        pygame.draw.polygon(surface, border_color, left_poly, 1)

        # Right face: [p_bottom, p_right, p_right + d, p_bottom + d]
        right_poly = [
            p_bottom,
            p_right,
            (p_right[0], p_right[1] + d),
            (p_bottom[0], p_bottom[1] + d),
        ]
        color_right = _shade(base_color, 0.55)
        pygame.draw.polygon(surface, color_right, right_poly)
        pygame.draw.polygon(surface, border_color, right_poly, 1)

    def _draw_floor_tile(self, surface: pygame.Surface, corners: list[tuple[int, int]], d: int) -> None:
        p_top, p_right, _p_bottom, p_left = corners
        border_color = settings.COLOR_FLOOR_BORDER

        # Side walls
        self._draw_side_walls(surface, corners, d, settings.COLOR_FLOOR, border_color)

        # Top diamond face
        pygame.draw.polygon(surface, settings.COLOR_FLOOR, corners)
        pygame.draw.polygon(surface, border_color, corners, 1)

        # Subtle bevel highlight on back edges
        highlight_color = (230, 238, 248)
        pygame.draw.line(surface, highlight_color, p_left, p_top, 1)
        pygame.draw.line(surface, highlight_color, p_top, p_right, 1)

    def _draw_fragile_tile(self, surface: pygame.Surface, corners: list[tuple[int, int]], d: int) -> None:
        p_top, p_right, p_bottom, p_left = corners
        border_color = settings.COLOR_FRAGILE_BORDER

        # Side walls
        self._draw_side_walls(surface, corners, d, settings.COLOR_FRAGILE, border_color)

        # Top diamond face
        pygame.draw.polygon(surface, settings.COLOR_FRAGILE, corners)
        pygame.draw.polygon(surface, border_color, corners, 2)

        # Diagonal hazard hatch lines across diamond
        for t in (0.25, 0.5, 0.75):
            p_a = (
                round((1 - t) * p_top[0] + t * p_right[0]),
                round((1 - t) * p_top[1] + t * p_right[1]),
            )
            p_b = (
                round((1 - t) * p_left[0] + t * p_bottom[0]),
                round((1 - t) * p_left[1] + t * p_bottom[1]),
            )
            pygame.draw.line(surface, border_color, p_a, p_b, 2)

    def _draw_goal_tile(self, surface: pygame.Surface, corners: list[tuple[int, int]], d: int) -> None:
        _p_top, _p_right, _p_bottom, _p_left = corners
        border_color = (25, 28, 38)

        # Side walls
        self._draw_side_walls(surface, corners, d, settings.COLOR_GOAL, border_color)

        # Top diamond face
        pygame.draw.polygon(surface, settings.COLOR_GOAL, corners)
        pygame.draw.polygon(surface, settings.COLOR_GOAL_RING, corners, 1)

        # Recessed dark hole in center
        cx = sum(p[0] for p in corners) / 4.0
        cy = sum(p[1] for p in corners) / 4.0
        inner_corners = [
            (round(cx + (px - cx) * 0.55), round(cy + (py - cy) * 0.55))
            for px, py in corners
        ]
        # Hole abyss
        pygame.draw.polygon(surface, (12, 14, 20), inner_corners)
        pygame.draw.polygon(surface, settings.COLOR_GOAL_RING, inner_corners, 2)

    def _draw_bridge_tile(
        self,
        surface: pygame.Surface,
        corners: list[tuple[int, int]],
        d: int,
        is_open: bool,
    ) -> None:
        p_top, p_right, p_bottom, p_left = corners

        if is_open:
            # Elevated illuminated bridge tile
            border_color = settings.COLOR_BRIDGE_OPEN_BORDER
            self._draw_side_walls(surface, corners, d, settings.COLOR_BRIDGE_OPEN, border_color)
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_OPEN, corners)
            pygame.draw.polygon(surface, border_color, corners, 1)

            # Planks line across center
            mid_l = (round((p_left[0] + p_top[0]) / 2), round((p_left[1] + p_top[1]) / 2))
            mid_r = (round((p_right[0] + p_bottom[0]) / 2), round((p_right[1] + p_bottom[1]) / 2))
            pygame.draw.line(surface, border_color, mid_l, mid_r, 1)
        else:
            # Closed bridge: sunken dark void lattice without tall extrusion
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_CLOSED, corners)
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_CLOSED_BORDER, corners, 1)
            # Dotted/dim red cross to signify inactive bridge span
            pygame.draw.line(surface, (130, 50, 60), p_left, p_right, 1)
            pygame.draw.line(surface, (130, 50, 60), p_top, p_bottom, 1)

    def _draw_switch(self, surface: pygame.Surface, pos: tuple[int, int], switch: Switch) -> None:
        r, c = pos
        cx, cy = self.cell_center(r, c, 0.0)
        sw_size = max(5, round(self.tile_size * 0.22))

        if switch.type == "soft":
            # Yellow isometric disc/ellipse
            w = max(6, sw_size * 2)
            h = max(4, sw_size)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.ellipse(surface, settings.COLOR_SWITCH_SOFT, rect)
            pygame.draw.ellipse(surface, (160, 130, 10), rect, 2)

        elif switch.type == "heavy":
            # Bold red cross
            arm_w = sw_size
            arm_h = round(sw_size * 0.5)
            p1 = (cx - arm_w, cy - arm_h)
            p2 = (cx + arm_w, cy + arm_h)
            p3 = (cx - arm_w, cy + arm_h)
            p4 = (cx + arm_w, cy - arm_h)
            width = max(3, self.tile_size // 14)
            pygame.draw.line(surface, settings.COLOR_SWITCH_HEAVY, p1, p2, width)
            pygame.draw.line(surface, settings.COLOR_SWITCH_HEAVY, p3, p4, width)

        elif switch.type == "split":
            # Split brackets / split diamond icon
            arm_w = sw_size
            arm_h = round(sw_size * 0.5)
            lw = max(2, self.tile_size // 16)
            # Left bracket
            p_tl = (cx - 2, cy - arm_h)
            p_ml = (cx - arm_w, cy)
            p_bl = (cx - 2, cy + arm_h)
            pygame.draw.lines(surface, settings.COLOR_SWITCH_SPLIT, False, [p_tl, p_ml, p_bl], lw)
            # Right bracket
            p_tr = (cx + 2, cy - arm_h)
            p_mr = (cx + arm_w, cy)
            p_br = (cx + 2, cy + arm_h)
            pygame.draw.lines(surface, settings.COLOR_SWITCH_SPLIT, False, [p_tr, p_mr, p_br], lw)

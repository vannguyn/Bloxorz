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

    def get_slab_depth(self, tile_type: TileType = TileType.FLOOR) -> int:
        """Returns the vertical slab extrusion depth for the given tile type."""
        d = max(4, round(self.tile_size * 0.15))
        if tile_type == TileType.FRAGILE:
            return max(2, d // 2)
        return d

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

        # Switches map and occupied cells for switch state feedback
        switches_by_pos = {sw.position: sw for sw in level.switches}
        occupied_cells = set(state.occupied_cells())

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
                is_pressed = (r, c) in occupied_cells
                self._draw_switch(surface, (r, c), switches_by_pos[(r, c)], is_pressed)

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
        fragile_d = max(2, d // 2)

        # 50% vertical thickness side walls
        self._draw_side_walls(surface, corners, fragile_d, settings.COLOR_FRAGILE, border_color)

        # Top diamond face
        pygame.draw.polygon(surface, settings.COLOR_FRAGILE, corners)
        pygame.draw.polygon(surface, border_color, corners, 1)

        # Full-span diagonal hazard warning stripes across diamond face
        for t in (0.2, 0.4, 0.6, 0.8):
            p_a = (
                round((1 - t) * p_top[0] + t * p_right[0]),
                round((1 - t) * p_top[1] + t * p_right[1]),
            )
            p_b = (
                round((1 - t) * p_left[0] + t * p_bottom[0]),
                round((1 - t) * p_left[1] + t * p_bottom[1]),
            )
            pygame.draw.line(surface, settings.COLOR_FRAGILE_STRIPE, p_a, p_b, 2)

    def _draw_goal_tile(self, surface: pygame.Surface, corners: list[tuple[int, int]], d: int) -> None:
        p_top, p_right, p_bottom, p_left = corners
        border_color = (25, 28, 38)

        # External slab side walls
        self._draw_side_walls(surface, corners, d, settings.COLOR_GOAL, border_color)

        # Sunken optical shaft aperture converging downward to dark abyss
        cx = sum(p[0] for p in corners) / 4.0
        cy = sum(p[1] for p in corners) / 4.0
        shaft_depth = round(d * 1.8)

        inner_corners = [
            (round(cx + (px - cx) * 0.55), round(cy + (py - cy) * 0.55 + shaft_depth))
            for px, py in corners
        ]
        _i_top, i_right, i_bottom, i_left = inner_corners

        # Top diamond base
        pygame.draw.polygon(surface, settings.COLOR_GOAL, corners)

        # Bottom abyss floor
        pygame.draw.polygon(surface, settings.COLOR_GOAL_ABYSS, inner_corners)

        # Left internal shaft wall: polygon [p_left, p_bottom, i_bottom, i_left]
        pygame.draw.polygon(surface, settings.COLOR_GOAL_WALL_LEFT, [p_left, p_bottom, i_bottom, i_left])

        # Right internal shaft wall: polygon [p_bottom, p_right, i_right, i_bottom]
        pygame.draw.polygon(surface, settings.COLOR_GOAL_WALL_RIGHT, [p_bottom, p_right, i_right, i_bottom])

        # Top perimeter highlight: subtle gold rim
        pygame.draw.polygon(surface, (190, 155, 50), corners, 1)

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
            # Closed bridge: sunken pit well without red-X
            bottom_corners = [(x, y + d) for (x, y) in corners]

            # Sunken abyss base floor
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_CLOSED, bottom_corners)

            # Sunken docking rail wireframe at pit depth
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_DOCK_RAIL, bottom_corners, 1)
            # Internal docking rail struts across sunken floor
            pygame.draw.line(surface, settings.COLOR_BRIDGE_DOCK_RAIL, bottom_corners[0], bottom_corners[2], 1)
            pygame.draw.line(surface, settings.COLOR_BRIDGE_DOCK_RAIL, bottom_corners[1], bottom_corners[3], 1)

            # Vertical corner guide pins linking surface corners to sunken pit
            for pt_top, pt_bot in zip(corners, bottom_corners):
                pygame.draw.line(surface, settings.COLOR_BRIDGE_DOCK_RAIL, pt_top, pt_bot, 1)

            # 4 corner docking guide circles at surface height
            pin_rad = max(2, round(self.tile_size * 0.05))
            for pt in corners:
                pygame.draw.circle(surface, settings.COLOR_BRIDGE_DOCK_PIN, pt, pin_rad)

    def _draw_switch(
        self,
        surface: pygame.Surface,
        pos: tuple[int, int],
        switch: Switch,
        is_pressed: bool = False,
    ) -> None:
        r, c = pos
        cx, cy = self.cell_center(r, c, 0.0)
        sw_size = max(5, round(self.tile_size * 0.22))

        if switch.type == "soft":
            # Cylindrical base pedestal
            w = max(10, round(self.tile_size * 0.44))
            h = max(5, round(w * 0.5))
            pedestal_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.ellipse(surface, settings.COLOR_SWITCH_PEDESTAL, pedestal_rect)
            pygame.draw.ellipse(surface, (40, 30, 10), pedestal_rect, 1)

            # Cap elevation: -4px relaxed, -1px pressed
            elev_y = -1 if is_pressed else -4
            cap_cy = cy + elev_y
            cap_w = max(8, w - 2)
            cap_h = max(4, h - 1)

            # Cylindrical skirt connecting pedestal to elevated cap
            if elev_y < 0:
                skirt_poly = [
                    (cx - cap_w // 2, cap_cy),
                    (cx + cap_w // 2, cap_cy),
                    (cx + w // 2, cy),
                    (cx - w // 2, cy),
                ]
                pygame.draw.polygon(surface, settings.COLOR_SWITCH_PEDESTAL, skirt_poly)

            # Tactile circular button cap
            cap_rect = pygame.Rect(cx - cap_w // 2, cap_cy - cap_h // 2, cap_w, cap_h)
            cap_color = (255, 245, 130) if is_pressed else settings.COLOR_SWITCH_SOFT
            pygame.draw.ellipse(surface, cap_color, cap_rect)
            rim_color = (200, 175, 30) if is_pressed else (160, 130, 10)
            pygame.draw.ellipse(surface, rim_color, cap_rect, 1 if is_pressed else 2)

        elif switch.type == "heavy":
            # Cast-metal base polygon
            bw = max(9, round(self.tile_size * 0.32))
            bh = max(5, round(bw * 0.5))
            base_poly = [
                (cx, cy - bh),
                (cx + bw, cy),
                (cx, cy + bh),
                (cx - bw, cy),
            ]
            pygame.draw.polygon(surface, settings.COLOR_SWITCH_HEAVY_BASE, base_poly)
            pygame.draw.polygon(surface, (25, 28, 35), base_poly, 1)

            # 3D extruded X arms and shadow
            arm_w = sw_size
            arm_h = round(sw_size * 0.5)

            # Drop shadow beneath arms
            sh_p1 = (cx - arm_w, cy - arm_h + 1)
            sh_p2 = (cx + arm_w, cy + arm_h + 1)
            sh_p3 = (cx - arm_w, cy + arm_h + 1)
            sh_p4 = (cx + arm_w, cy - arm_h + 1)
            lw = max(3, self.tile_size // 12)
            pygame.draw.line(surface, (20, 22, 28), sh_p1, sh_p2, lw)
            pygame.draw.line(surface, (20, 22, 28), sh_p3, sh_p4, lw)

            # Elevated 3D X arms
            elev_y = -1 if is_pressed else -3
            ac_y = cy + elev_y
            p1 = (cx - arm_w, ac_y - arm_h)
            p2 = (cx + arm_w, ac_y + arm_h)
            p3 = (cx - arm_w, ac_y + arm_h)
            p4 = (cx + arm_w, ac_y - arm_h)
            x_color = (255, 110, 110) if is_pressed else settings.COLOR_SWITCH_HEAVY
            pygame.draw.line(surface, x_color, p1, p2, lw)
            pygame.draw.line(surface, x_color, p3, p4, lw)

        elif switch.type == "split":
            # Split: twin curved bracket arcs and dual cyan gem pips with elevation
            elev_y = -1 if is_pressed else -3
            scy = cy + elev_y

            split_color = (130, 225, 255) if is_pressed else settings.COLOR_SWITCH_SPLIT
            rad = sw_size
            bracket_h = max(4, round(rad * 0.7))
            bracket_w = max(3, rad // 2)
            l_cx = cx - bracket_w - 2
            r_cx = cx + bracket_w + 2
            arc_lw = max(2, self.tile_size // 18)

            # Twin curved bracket arcs
            pygame.draw.arc(surface, split_color, (l_cx - 4, scy - bracket_h, 8, bracket_h * 2), 1.57, 4.71, arc_lw)
            pygame.draw.arc(surface, split_color, (r_cx - 4, scy - bracket_h, 8, bracket_h * 2), -1.57, 1.57, arc_lw)

            # Dual cyan gem pips with elevation
            pip_w = max(3, round(self.tile_size * 0.08))
            pip_h = max(2, round(pip_w * 0.5))
            pip_offset = max(3, rad // 3)

            # Left isometric gem pip
            gem_l = [
                (cx - pip_offset, scy - pip_h),
                (cx - pip_offset + pip_w, scy),
                (cx - pip_offset, scy + pip_h),
                (cx - pip_offset - pip_w, scy),
            ]
            pygame.draw.polygon(surface, split_color, gem_l)

            # Right isometric gem pip
            gem_r = [
                (cx + pip_offset, scy - pip_h),
                (cx + pip_offset + pip_w, scy),
                (cx + pip_offset, scy + pip_h),
                (cx + pip_offset - pip_w, scy),
            ]
            pygame.draw.polygon(surface, split_color, gem_r)

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
            return max(2, round(d * 0.35))
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
        glass_depth = max(2, round(d * 0.35))

        # Side walls with shaded amber tones and glass border
        self._draw_side_walls(surface, corners, glass_depth, settings.COLOR_FRAGILE, settings.COLOR_GLASS_BORDER)

        # Base fill
        pygame.draw.polygon(surface, settings.COLOR_FRAGILE, corners)

        # Bounding box of top diamond
        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        tw = max(1, max_x - min_x)
        th = max(1, max_y - min_y)

        # Alpha surface for translucent amber glass and pixel-art crack projection
        iso_crack = pygame.Surface((tw, th), pygame.SRCALPHA)
        local_corners = [(x - min_x, y - min_y) for (x, y) in corners]
        pygame.draw.polygon(iso_crack, settings.COLOR_GLASS_FILL, local_corners)

        pw = max(2, round(tw / 32.0))
        ph = max(1, round(th / 32.0))

        # Under-shadow layer (depth)
        for gx, gy in settings.FRAGILE_CRACK_SHADOW:
            u = gx / 32.0
            v = gy / 32.0
            px = int(round(tw * 0.5 + (u - v) * (tw * 0.5)))
            py = int(round((u + v) * (th * 0.5)))
            pygame.draw.rect(iso_crack, settings.COLOR_GLASS_SHADOW, (px, py, pw, ph))

        # White starburst crack highlight layer
        crack_color = settings.COLOR_GLASS_CRACK[:3]
        for gx, gy in settings.FRAGILE_CRACK_WHITE:
            u = gx / 32.0
            v = gy / 32.0
            px = int(round(tw * 0.5 + (u - v) * (tw * 0.5)))
            py = int(round((u + v) * (th * 0.5)))
            pygame.draw.rect(iso_crack, crack_color, (px, py, pw, ph))

        surface.blit(iso_crack, (min_x, min_y))
        pygame.draw.polygon(surface, settings.COLOR_GLASS_BORDER, corners, 1)

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
            # Base metal octagon plate
            bw = max(10, round(self.tile_size * 0.35))
            bh = max(5, round(bw * 0.5))
            c1 = max(2, round(bw * 0.3))
            c2 = max(1, round(bh * 0.3))
            octagon_base = [
                (cx - c1, cy - bh + c2), (cx + c1, cy - bh + c2),
                (cx + bw - c1, cy - c2), (cx + bw - c1, cy + c2),
                (cx + c1, cy + bh - c2), (cx - c1, cy + bh - c2),
                (cx - bw + c1, cy + c2), (cx - bw + c1, cy - c2),
            ]
            pygame.draw.polygon(surface, settings.COLOR_HEAVY_BASE, octagon_base)
            pygame.draw.polygon(surface, (148, 163, 184), octagon_base, 1)

            # 4 corner rivets
            rivets = [
                (cx, cy - bh + c2 + 1),
                (cx + bw - c1 - 1, cy),
                (cx, cy + bh - c2 - 1),
                (cx - bw + c1 + 1, cy),
            ]
            for rx, ry in rivets:
                pygame.draw.circle(surface, (148, 163, 184), (rx, ry), 1)

            # 3D Extruded cross arms
            elev_y = -1 if is_pressed else -4
            arm_w = max(6, round(self.tile_size * 0.22))
            arm_h = max(3, round(arm_w * 0.5))
            lw = max(3, round(self.tile_size / 10))

            if not is_pressed:
                # Lower shadow base and vertical extrusion when not pressed
                sh_p1 = (cx - arm_w, cy - arm_h)
                sh_p2 = (cx + arm_w, cy + arm_h)
                sh_p3 = (cx - arm_w, cy + arm_h)
                sh_p4 = (cx + arm_w, cy - arm_h)
                pygame.draw.line(surface, settings.COLOR_HEAVY_DARKRED, sh_p1, sh_p2, lw)
                pygame.draw.line(surface, settings.COLOR_HEAVY_DARKRED, sh_p3, sh_p4, lw)
                for dy in range(elev_y, 0):
                    pygame.draw.line(surface, settings.COLOR_HEAVY_DARKRED, (cx - arm_w, cy + dy - arm_h), (cx + arm_w, cy + dy + arm_h), lw)
                    pygame.draw.line(surface, settings.COLOR_HEAVY_DARKRED, (cx - arm_w, cy + dy + arm_h), (cx + arm_w, cy + dy - arm_h), lw)

            # Upper cross arms
            ac_y = cy + elev_y
            p1 = (cx - arm_w, ac_y - arm_h)
            p2 = (cx + arm_w, ac_y + arm_h)
            p3 = (cx - arm_w, ac_y + arm_h)
            p4 = (cx + arm_w, ac_y - arm_h)
            x_color = (255, 120, 120) if is_pressed else settings.COLOR_HEAVY_RED
            pygame.draw.line(surface, x_color, p1, p2, lw)
            pygame.draw.line(surface, x_color, p3, p4, lw)

        elif switch.type == "split":
            # 3D Split switch: symmetrical arched bracket wings with dynamic gap compression
            lift = -1 if is_pressed else -4
            gap = 2 if is_pressed else 5
            scy = cy + lift

            sw_w = max(6, round(self.tile_size * 0.16))
            sw_h = max(7, round(self.tile_size * 0.22))

            # Arched left and right bracket wings
            lw_top = [
                (cx - gap - sw_w, scy - sw_h),
                (cx - gap - max(2, sw_w // 3), scy - sw_h),
                (cx - gap - max(2, sw_w // 3), scy - max(2, sw_h // 3)),
                (cx - gap, scy),
                (cx - gap - max(2, sw_w // 3), scy + max(2, sw_h // 3)),
                (cx - gap - max(2, sw_w // 3), scy + sw_h),
                (cx - gap - sw_w, scy + sw_h),
                (cx - gap - max(3, sw_w * 2 // 3), scy),
            ]
            rw_top = [
                (cx + gap + sw_w, scy - sw_h),
                (cx + gap + max(2, sw_w // 3), scy - sw_h),
                (cx + gap + max(2, sw_w // 3), scy - max(2, sw_h // 3)),
                (cx + gap, scy),
                (cx + gap + max(2, sw_w // 3), scy + max(2, sw_h // 3)),
                (cx + gap + max(2, sw_w // 3), scy + sw_h),
                (cx + gap + sw_w, scy + sw_h),
                (cx + gap + max(3, sw_w * 2 // 3), scy),
            ]

            # Lower shadow skirts (10, 60, 100)
            drop = -lift
            lw_shadow = [(x, y + drop) for (x, y) in lw_top]
            rw_shadow = [(x, y + drop) for (x, y) in rw_top]
            pygame.draw.polygon(surface, (10, 60, 100), lw_shadow)
            pygame.draw.polygon(surface, (10, 60, 100), rw_shadow)

            # Extrusion skirt between top and shadow
            for i in range(len(lw_top)):
                ni = (i + 1) % len(lw_top)
                if lw_top[i][1] >= scy or lw_top[ni][1] >= scy:
                    pygame.draw.polygon(surface, (10, 60, 100), [lw_top[i], lw_top[ni], lw_shadow[ni], lw_shadow[i]])
                if rw_top[i][1] >= scy or rw_top[ni][1] >= scy:
                    pygame.draw.polygon(surface, (10, 60, 100), [rw_top[i], rw_top[ni], rw_shadow[ni], rw_shadow[i]])

            # Top polygons
            color = (200, 240, 255) if is_pressed else settings.COLOR_SPLIT_CYAN
            pygame.draw.polygon(surface, color, lw_top)
            pygame.draw.polygon(surface, settings.COLOR_SPLIT_DARK, lw_top, 1)
            pygame.draw.polygon(surface, color, rw_top)
            pygame.draw.polygon(surface, settings.COLOR_SPLIT_DARK, rw_top, 1)

            # Center void groove (15, 23, 42)
            pygame.draw.line(surface, (15, 23, 42), (cx, cy - sw_h - 2), (cx, cy + sw_h + 2), 2)

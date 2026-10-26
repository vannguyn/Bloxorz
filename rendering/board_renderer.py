"""
2D Top-down Board Renderer for Bloxorz.
Draws floor, goal, fragile tiles, bridges (open/closed), and switches (soft, heavy, split).
Decoupled from input and game logic per IDD plan.
"""
from __future__ import annotations

import pygame
from core.interfaces import GameState, Level, Switch, TileType
from config import settings


class BoardRenderer:
    """Renders the grid board and static mechanism tiles."""

    def __init__(self, viewport_width: int, viewport_height: int):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.tile_size = settings.TILE_SIZE
        self.origin_x = 0
        self.origin_y = 0

    def compute_layout(self, level: Level, area_rect: pygame.Rect | None = None) -> tuple[int, int, int]:
        """Calculates origin and dynamic tile size to center the board inside the viewport area."""
        rect = area_rect or pygame.Rect(0, 0, self.viewport_width, self.viewport_height)
        avail_w = rect.width - 2 * settings.BOARD_MARGIN
        avail_h = rect.height - 2 * settings.BOARD_MARGIN

        max_cols = max(level.width, 1)
        max_rows = max(level.height, 1)

        size_w = avail_w // max_cols
        size_h = avail_h // max_rows
        tile_size = max(24, min(settings.TILE_SIZE, size_w, size_h))

        board_w = max_cols * tile_size
        board_h = max_rows * tile_size

        origin_x = rect.x + (rect.width - board_w) // 2
        origin_y = rect.y + (rect.height - board_h) // 2

        self.tile_size = tile_size
        self.origin_x = origin_x
        self.origin_y = origin_y
        return origin_x, origin_y, tile_size

    def get_cell_rect(self, row: int, col: int) -> pygame.Rect:
        """Returns the screen Rect for a given grid cell (row, col)."""
        x = self.origin_x + col * self.tile_size
        y = self.origin_y + row * self.tile_size
        return pygame.Rect(x, y, self.tile_size, self.tile_size)

    def draw(
        self,
        surface: pygame.Surface,
        level: Level,
        state: GameState,
        area_rect: pygame.Rect | None = None,
    ) -> None:
        """Draws all board tiles, bridges, and switches."""
        self.compute_layout(level, area_rect)

        # Build bridge open/closed status map from state.bridge_mask
        bridge_index_map = {b_id: i for i, b_id in enumerate(level.bridges.keys())}
        bridge_cell_status: dict[tuple[int, int], bool] = {}
        for b_id, b_tiles in level.bridges.items():
            b_idx = bridge_index_map.get(b_id, 0)
            is_open = bool(state.bridge_mask & (1 << b_idx))
            for cell in b_tiles:
                bridge_cell_status[cell] = is_open

        # 1. Draw tiles
        for (r, c), tile_type in level.tiles.items():
            cell_rect = self.get_cell_rect(r, c)

            if tile_type == TileType.FLOOR:
                self._draw_floor_tile(surface, cell_rect)
            elif tile_type == TileType.GOAL:
                self._draw_goal_tile(surface, cell_rect)
            elif tile_type == TileType.FRAGILE:
                self._draw_fragile_tile(surface, cell_rect)
            elif tile_type == TileType.BRIDGE:
                is_open = bridge_cell_status.get((r, c), False)
                self._draw_bridge_tile(surface, cell_rect, is_open)

        # 2. Draw switches
        occupied_cells = set(state.occupied_cells())
        for sw in level.switches:
            cell_rect = self.get_cell_rect(sw.position[0], sw.position[1])
            is_pressed = sw.position in occupied_cells
            self._draw_switch(surface, cell_rect, sw, is_pressed=is_pressed)

    def _draw_floor_tile(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, settings.COLOR_FLOOR, rect)
        pygame.draw.rect(surface, settings.COLOR_FLOOR_BORDER, rect, 1)
        # Highlight top-left bevel
        pygame.draw.line(surface, (230, 238, 248), rect.topleft, rect.topright, 1)
        pygame.draw.line(surface, (230, 238, 248), rect.topleft, rect.bottomleft, 1)

    def _draw_goal_tile(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, settings.COLOR_GOAL, rect)
        pygame.draw.rect(surface, settings.COLOR_GOAL_RING, rect, 2)
        center = rect.center
        radius = max(4, self.tile_size // 4)
        pygame.draw.circle(surface, settings.COLOR_GOAL_RING, center, radius, 2)

    def _draw_fragile_tile(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, settings.COLOR_FRAGILE, rect)
        # Full-span diagonal hazard warning stripes covering 100% of tile rect using clipline
        step = max(6, self.tile_size // 6)
        for offset in range(step, rect.width + rect.height, step):
            p1 = (rect.left + offset, rect.top)
            p2 = (rect.left, rect.top + offset)
            clipped = rect.clipline(p1, p2)
            if clipped:
                pygame.draw.line(surface, settings.COLOR_FRAGILE_STRIPE, clipped[0], clipped[1], 2)
        # Crisp perimeter warning border
        pygame.draw.rect(surface, settings.COLOR_FRAGILE_BORDER, rect, 2)

    def _draw_bridge_tile(self, surface: pygame.Surface, rect: pygame.Rect, is_open: bool) -> None:
        if is_open:
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_OPEN, rect)
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_OPEN_BORDER, rect, 2)
            # Subtle cross pattern indicating deployed bridge planks
            center = rect.center
            pygame.draw.line(surface, settings.COLOR_BRIDGE_OPEN_BORDER, (rect.left + 2, center[1]), (rect.right - 2, center[1]), 2)
        else:
            # Closed bridge: dark void abyss, recessed docking rail wireframe, and corner docking pins
            # (No crimson red-X, which is strictly reserved for Heavy Switch)
            pygame.draw.rect(surface, (16, 20, 28), rect)
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_CLOSED_BORDER, rect, 1)

            # Recessed docking rail at pit depth
            inner_rect = rect.inflate(-8, -8)
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_DOCK_RAIL, inner_rect, 1)

            # 4 corner docking guide pins
            pin_size = max(2, min(4, self.tile_size // 10))
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_DOCK_PIN, (rect.left + 2, rect.top + 2, pin_size, pin_size))
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_DOCK_PIN, (rect.right - 2 - pin_size, rect.top + 2, pin_size, pin_size))
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_DOCK_PIN, (rect.left + 2, rect.bottom - 2 - pin_size, pin_size, pin_size))
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_DOCK_PIN, (rect.right - 2 - pin_size, rect.bottom - 2 - pin_size, pin_size, pin_size))

    def _draw_switch(self, surface: pygame.Surface, rect: pygame.Rect, switch: Switch, is_pressed: bool = False) -> None:
        center = rect.center
        rad = max(6, self.tile_size // 3)

        if switch.type == "soft":
            # Cylindrical base pedestal shadow ring
            pygame.draw.circle(surface, settings.COLOR_SWITCH_PEDESTAL, center, rad + 2)
            # Tactile circular button cap (brightens when pressed)
            cap_color = (255, 245, 130) if is_pressed else settings.COLOR_SWITCH_SOFT
            pygame.draw.circle(surface, cap_color, center, rad)
            rim_color = (200, 175, 30) if is_pressed else (160, 130, 10)
            pygame.draw.circle(surface, rim_color, center, rad, 1 if is_pressed else 2)
        elif switch.type == "heavy":
            # Cast-metal square subplate base
            sub_size = max(14, int(self.tile_size * 0.65))
            sub_rect = pygame.Rect(center[0] - sub_size // 2, center[1] - sub_size // 2, sub_size, sub_size)
            pygame.draw.rect(surface, settings.COLOR_SWITCH_HEAVY_BASE, sub_rect)
            pygame.draw.rect(surface, (30, 35, 45), sub_rect, 1)

            # Bold crimson X arms (brightens when pressed)
            arm = max(4, sub_size // 2 - 2)
            p1 = (center[0] - arm, center[1] - arm)
            p2 = (center[0] + arm, center[1] + arm)
            p3 = (center[0] - arm, center[1] + arm)
            p4 = (center[0] + arm, center[1] - arm)
            x_color = (255, 110, 110) if is_pressed else settings.COLOR_SWITCH_HEAVY
            pygame.draw.line(surface, x_color, p1, p2, 5)
            pygame.draw.line(surface, x_color, p3, p4, 5)
        elif switch.type == "split":
            # Split switch: twin curved brackets "( )" and dual cyan gem pips
            bracket_h = rad
            bracket_w = max(4, rad // 2)
            l_cx = center[0] - bracket_w
            r_cx = center[0] + bracket_w
            split_color = (120, 215, 255) if is_pressed else settings.COLOR_SWITCH_SPLIT

            # Twin brackets
            pygame.draw.arc(surface, split_color, (l_cx - 4, center[1] - bracket_h, 8, bracket_h * 2), 1.57, 4.71, 3)
            pygame.draw.arc(surface, split_color, (r_cx - 4, center[1] - bracket_h, 8, bracket_h * 2), -1.57, 1.57, 3)

            # Dual cyan gem pips
            pip_rad = max(2, rad // 4)
            pip_offset = max(3, rad // 3)
            pygame.draw.circle(surface, split_color, (center[0] - pip_offset, center[1]), pip_rad)
            pygame.draw.circle(surface, split_color, (center[0] + pip_offset, center[1]), pip_rad)


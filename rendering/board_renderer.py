"""
2D Top-down Board Renderer for Bloxorz.
Draws floor, goal, fragile tiles, bridges (open/closed), and switches (soft, heavy, split).
Decoupled from input and game logic per IDD plan.
"""
from __future__ import annotations

import pygame
from core.game_state import GameState
from core.board import Switch
from entities.tile import TileType
from levels.level_loader import Level
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

    def get_cell_rect(self, x_coord: int, y_coord: int) -> pygame.Rect:
        """Return the screen rectangle for a core ``(x, y)`` cell."""
        x = self.origin_x + x_coord * self.tile_size
        y = self.origin_y + y_coord * self.tile_size
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

        board = state.board
        # Bridge status comes from the core state, not from a UI-local bitmask.
        bridge_cell_status: dict[tuple[int, int], bool] = {}
        for b_id, bridge in board.bridges.items():
            is_open = state.bridge_map.get(b_id, bridge.initial_state) == "open"
            for cell in bridge.tiles:
                bridge_cell_status[cell] = is_open

        # 1. Draw all cells from the authoritative Board.
        cells = set(board.tiles)
        for bridge in board.bridges.values():
            cells.update(bridge.tiles)
        for x, y in cells:
            cell_rect = self.get_cell_rect(x, y)
            tile = board.tile_at((x, y))
            if tile.type is TileType.BRIDGE:
                self._draw_bridge_tile(surface, cell_rect, bridge_cell_status.get((x, y), False))
            elif tile.type is TileType.GOAL:
                self._draw_goal_tile(surface, cell_rect)
            elif tile.type is TileType.FRAGILE:
                self._draw_fragile_tile(surface, cell_rect)
            elif tile.type is TileType.FLOOR:
                self._draw_floor_tile(surface, cell_rect)

        # 2. Draw switches
        for sw in board.switches.values():
            cell_rect = self.get_cell_rect(sw.position[0], sw.position[1])
            self._draw_switch(surface, cell_rect, sw)

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
        pygame.draw.rect(surface, settings.COLOR_FRAGILE_BORDER, rect, 2)
        # Draw subtle warning diagonal lines to signify fragile surface
        gap = max(8, self.tile_size // 4)
        for offset in range(gap, self.tile_size, gap):
            p1 = (rect.left + offset, rect.top)
            p2 = (rect.left, rect.top + offset)
            pygame.draw.line(surface, settings.COLOR_FRAGILE_BORDER, p1, p2, 1)

    def _draw_bridge_tile(self, surface: pygame.Surface, rect: pygame.Rect, is_open: bool) -> None:
        if is_open:
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_OPEN, rect)
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_OPEN_BORDER, rect, 2)
            # Subtle cross pattern indicating deployed bridge planks
            center = rect.center
            pygame.draw.line(surface, settings.COLOR_BRIDGE_OPEN_BORDER, (rect.left + 4, center[1]), (rect.right - 4, center[1]), 1)
        else:
            # Closed bridge: appears like void/transparent with dashed outline
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_CLOSED, rect)
            pygame.draw.rect(surface, settings.COLOR_BRIDGE_CLOSED_BORDER, rect, 1)
            # Red dotted cross to clearly mark inactive bridge
            pygame.draw.line(surface, (120, 50, 60), (rect.left + 6, rect.top + 6), (rect.right - 6, rect.bottom - 6), 1)
            pygame.draw.line(surface, (120, 50, 60), (rect.left + 6, rect.bottom - 6), (rect.right - 6, rect.top + 6), 1)

    def _draw_switch(self, surface: pygame.Surface, rect: pygame.Rect, switch: Switch) -> None:
        center = rect.center
        rad = max(6, self.tile_size // 3)

        if switch.type == "soft":
            # Octagon/Circle in yellow
            pygame.draw.circle(surface, settings.COLOR_SWITCH_SOFT, center, rad)
            pygame.draw.circle(surface, (160, 130, 10), center, rad, 2)
        elif switch.type == "heavy":
            # Heavy switch: Bold 'X' shape in crimson
            arm = rad - 2
            p1 = (center[0] - arm, center[1] - arm)
            p2 = (center[0] + arm, center[1] + arm)
            p3 = (center[0] - arm, center[1] + arm)
            p4 = (center[0] + arm, center[1] - arm)
            pygame.draw.line(surface, settings.COLOR_SWITCH_HEAVY, p1, p2, 5)
            pygame.draw.line(surface, settings.COLOR_SWITCH_HEAVY, p3, p4, 5)
        elif switch.type == "split":
            # Split switch: "( )" bracket shape in bright cyan
            bracket_h = rad
            bracket_w = max(4, rad // 2)
            # Left bracket "("
            l_cx = center[0] - bracket_w
            r_cx = center[0] + bracket_w
            pygame.draw.arc(surface, settings.COLOR_SWITCH_SPLIT, (l_cx - 4, center[1] - bracket_h, 8, bracket_h * 2), 1.57, 4.71, 3)
            # Right bracket ")"
            pygame.draw.arc(surface, settings.COLOR_SWITCH_SPLIT, (r_cx - 4, center[1] - bracket_h, 8, bracket_h * 2), -1.57, 1.57, 3)

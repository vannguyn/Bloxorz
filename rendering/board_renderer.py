"""
2D Top-down Board Renderer for Bloxorz.
Draws floor, goal, fragile tiles, bridges (open/closed), and switches (soft, heavy, split).
Decoupled from input and game logic per IDD plan.
"""
from __future__ import annotations

import math
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
        # Solid orange fragile body
        pygame.draw.rect(surface, settings.COLOR_FRAGILE, rect)

        # Diagonal hazard warning stripes (shorter loop, trimmed at bottom right)
        gap = max(6, self.tile_size // 6)
        for offset in range(gap, rect.width, gap):
            p1 = (rect.left + offset, rect.top)
            p2 = (rect.left, rect.top + offset)
            pygame.draw.line(surface, settings.COLOR_FRAGILE_STRIPE, p1, p2, 2)

        # Perimeter warning border
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
        if switch.type == "soft":
            center = rect.center
            rad = max(6, self.tile_size // 3)
            # Cylindrical base pedestal shadow ring
            pygame.draw.circle(surface, settings.COLOR_SWITCH_PEDESTAL, center, rad + 2)
            # Tactile circular button cap (brightens when pressed)
            cap_color = (255, 245, 130) if is_pressed else settings.COLOR_SWITCH_SOFT
            pygame.draw.circle(surface, cap_color, center, rad)
            rim_color = (200, 175, 30) if is_pressed else (160, 130, 10)
            pygame.draw.circle(surface, rim_color, center, rad, 1 if is_pressed else 2)
        elif switch.type == "heavy":
            # Industrial cast-metal base plate with rounded corners
            sub_rect = rect.inflate(-10, -10)
            pygame.draw.rect(surface, settings.COLOR_HEAVY_BASE, sub_rect, border_radius=4)
            pygame.draw.rect(surface, (148, 163, 184), sub_rect, 1, border_radius=4)

            # 4 corner rivets
            rivet_offset = 3
            rivets = [
                (sub_rect.left + rivet_offset, sub_rect.top + rivet_offset),
                (sub_rect.right - rivet_offset, sub_rect.top + rivet_offset),
                (sub_rect.left + rivet_offset, sub_rect.bottom - rivet_offset),
                (sub_rect.right - rivet_offset, sub_rect.bottom - rivet_offset),
            ]
            for rx, ry in rivets:
                pygame.draw.circle(surface, (148, 163, 184), (rx, ry), 2)

            # 12-point closed polygon cross
            cx, cy = rect.centerx, rect.centery
            s = max(7, min(14, self.tile_size // 4))
            w = max(2, s // 3)
            points = [
                (cx - s, cy - s + w), (cx - s + w, cy - s), (cx, cy - w),
                (cx + s - w, cy - s), (cx + s, cy - s + w), (cx + w, cy),
                (cx + s, cy + s - w), (cx + s - w, cy + s), (cx, cy + w),
                (cx - s + w, cy + s), (cx - s, cy + s - w), (cx - w, cy),
            ]
            color = (255, 120, 120) if is_pressed else settings.COLOR_HEAVY_RED
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, settings.COLOR_HEAVY_DARKRED, points, 1)
        elif switch.type == "split":
            # Split switch: dual arched wings with dynamic gap compression
            cx, cy = rect.centerx, rect.centery
            gap = 2 if is_pressed else 6
            sw_w = max(8, self.tile_size // 4)
            sw_h = max(10, self.tile_size // 3)

            left_wing = [
                (cx - gap - sw_w, cy - sw_h), (cx - gap - sw_w // 3, cy - sw_h),
                (cx - gap - sw_w // 3, cy - sw_h // 3), (cx - gap, cy),
                (cx - gap - sw_w // 3, cy + sw_h // 3), (cx - gap - sw_w // 3, cy + sw_h),
                (cx - gap - sw_w, cy + sw_h), (cx - gap - sw_w * 2 // 3, cy),
            ]
            right_wing = [
                (cx + gap + sw_w, cy - sw_h), (cx + gap + sw_w // 3, cy - sw_h),
                (cx + gap + sw_w // 3, cy - sw_h // 3), (cx + gap, cy),
                (cx + gap + sw_w // 3, cy + sw_h // 3), (cx + gap + sw_w // 3, cy + sw_h),
                (cx + gap + sw_w, cy + sw_h), (cx + gap + sw_w * 2 // 3, cy),
            ]
            color = (200, 240, 255) if is_pressed else settings.COLOR_SPLIT_CYAN

            pygame.draw.polygon(surface, color, left_wing)
            pygame.draw.polygon(surface, settings.COLOR_SPLIT_DARK, left_wing, 1)
            pygame.draw.polygon(surface, color, right_wing)
            pygame.draw.polygon(surface, settings.COLOR_SPLIT_DARK, right_wing, 1)
            pygame.draw.line(surface, (15, 23, 42), (cx, cy - sw_h - 2), (cx, cy + sw_h + 2), 2)


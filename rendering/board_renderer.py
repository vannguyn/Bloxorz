"""Isometric 3D-style board renderer built from Pygame polygons."""

from __future__ import annotations

import math

import pygame

from config import settings
from core.board import Switch
from core.game_state import GameState
from entities.tile import TileType
from levels.level_loader import Level


class BoardRenderer:
    """Projects board coordinates onto an isometric diamond grid."""

    HEIGHT_RATIO = 0.52
    DEPTH_RATIO = 0.13

    def __init__(self, viewport_width: int, viewport_height: int):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.tile_size = settings.TILE_SIZE
        self.origin_x = 0.0
        self.origin_y = 0.0
        self.board_width = 0
        self.area_rect = pygame.Rect(0, 0, viewport_width, viewport_height)
        self.switch_font = pygame.font.SysFont(None, 16, bold=True)

    @property
    def tile_height(self) -> float:
        return self.tile_size * self.HEIGHT_RATIO

    @property
    def elevation(self) -> float:
        return self.tile_size * 0.55

    @property
    def tile_depth(self) -> float:
        return self.tile_size * self.DEPTH_RATIO

    def compute_layout(self, level: Level, area_rect: pygame.Rect | None = None) -> tuple[int, int, int]:
        rect = area_rect or pygame.Rect(0, 0, self.viewport_width, self.viewport_height)
        padding = max(12, round(settings.BOARD_MARGIN * 0.45))
        available_width = max(1, rect.width - padding * 2)
        available_height = max(1, rect.height - padding * 2)

        width_units = (level.width + level.height) * 0.5
        height_units = (level.width + level.height) * self.HEIGHT_RATIO * 0.5 + 0.62
        tile_size = min(
            settings.TILE_SIZE * 2.0,
            available_width / max(width_units, 1),
            available_height / max(height_units, 1),
        )
        self.tile_size = max(14, tile_size)
        self.area_rect = pygame.Rect(rect)
        self.board_width = level.width
        self.switch_font = pygame.font.SysFont(
            None, max(16, round(self.tile_size * 0.22)), bold=True
        )

        projected_height = (level.width + level.height) * self.tile_height * 0.5
        rotated_width = level.height
        rotated_height = level.width
        self.origin_x = rect.centerx - (rotated_width - rotated_height) * self.tile_size * 0.25
        self.origin_y = rect.centery - projected_height * 0.5 + self.elevation * 0.7
        return round(self.origin_x), round(self.origin_y), round(self.tile_size)

    def project(self, x: float, y: float, z: float = 0.0) -> tuple[int, int]:
        rotated_x = y
        rotated_y = self.board_width - x
        px = self.origin_x + (rotated_x - rotated_y) * self.tile_size * 0.5
        py = self.origin_y + (rotated_x + rotated_y) * self.tile_height * 0.5 - z * self.elevation
        return round(px), round(py)

    def cell_center(self, position: tuple[float, float], z: float = 0.0) -> tuple[int, int]:
        return self.project(position[0] + 0.5, position[1] + 0.5, z)

    def tile_corners(self, x: float, y: float, z: float = 0.0) -> list[tuple[int, int]]:
        return [
            self.project(x, y, z),
            self.project(x + 1, y, z),
            self.project(x + 1, y + 1, z),
            self.project(x, y + 1, z),
        ]

    def get_cell_rect(self, x_coord: int, y_coord: int) -> pygame.Rect:
        points = self.tile_corners(x_coord, y_coord)
        return pygame.Rect(
            min(point[0] for point in points),
            min(point[1] for point in points),
            max(point[0] for point in points) - min(point[0] for point in points),
            max(point[1] for point in points) - min(point[1] for point in points),
        )

    def draw(
        self,
        surface: pygame.Surface,
        level: Level,
        state: GameState,
        area_rect: pygame.Rect | None = None,
        bridge_transition: tuple[GameState, GameState, float] | None = None,
    ) -> None:
        self.compute_layout(level, area_rect)
        self._draw_backdrop(surface)

        board = state.board
        bridge_states = state.bridge_map
        cells = set(board.tiles)
        for bridge in board.bridges.values():
            cells.update(bridge.tiles)

        all_cells = {
            (x, y)
            for y in range(board.height)
            for x in range(board.width)
        }
        void_cells = all_cells.difference(cells)
        for x, y in sorted(void_cells, key=lambda cell: (cell[1] + board.width - cell[0], cell[0])):
            self._draw_void(surface, x, y)

        for x, y in sorted(cells, key=lambda cell: (cell[1] + board.width - cell[0], cell[0])):
            tile = board.tile_at((x, y))
            is_open = tile.bridge_id is not None and bridge_states.get(
                tile.bridge_id, board.bridges[tile.bridge_id].initial_state
            ) == "open"
            transition = self._bridge_tile_transition(tile.bridge_id, bridge_transition)
            if transition is not None and transition[0] != transition[1]:
                self._draw_folding_bridge(surface, x, y, transition[0], transition[1], transition[2])
            else:
                self._draw_tile(surface, x, y, tile.type, is_open)

        for switch in sorted(
            board.switches.values(),
            key=lambda item: item.position[1] + board.width - item.position[0],
        ):
            self._draw_switch(surface, switch)

        self._draw_board_glow(surface)

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        surface.fill(settings.COLOR_BG)
        rect = self.area_rect
        pygame.draw.rect(surface, (17, 23, 38), rect)
        pygame.draw.ellipse(
            surface,
            (22, 32, 50),
            (rect.left + 30, rect.top + 30, max(1, rect.width - 60), max(1, rect.height - 60)),
        )

    def _draw_board_glow(self, surface: pygame.Surface) -> None:
        rect = self.area_rect
        pygame.draw.line(
            surface,
            (36, 75, 105),
            (rect.left + 24, rect.bottom - 24),
            (rect.right - 24, rect.bottom - 24),
            1,
        )

    def _draw_tile(self, surface: pygame.Surface, x: int, y: int, kind: TileType, is_open: bool) -> None:
        top = self.tile_corners(x, y)
        bottom_south = [top[2], top[3], self.project(x, y + 1, -self.DEPTH_RATIO), self.project(x + 1, y + 1, -self.DEPTH_RATIO)]
        bottom_east = [top[1], top[2], self.project(x + 1, y + 1, -self.DEPTH_RATIO), self.project(x + 1, y, -self.DEPTH_RATIO)]

        if kind is TileType.BRIDGE and not is_open:
            pygame.draw.polygon(surface, (12, 17, 28), bottom_south)
            pygame.draw.polygon(surface, (19, 25, 39), bottom_east)
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_CLOSED, top)
            pygame.draw.polygon(surface, settings.COLOR_BRIDGE_CLOSED_BORDER, top, 1)
            self._draw_diamond_cross(surface, top, (112, 54, 70))
            return

        if kind is TileType.GOAL:
            top_color, side_color, edge_color = (38, 50, 62), (29, 38, 53), settings.COLOR_GOAL_RING
        elif kind is TileType.FRAGILE:
            top_color, side_color, edge_color = (180, 82, 46), (102, 48, 37), (255, 157, 77)
        elif kind is TileType.BRIDGE:
            top_color, side_color, edge_color = (67, 160, 151), (36, 99, 101), (127, 229, 203)
        else:
            shade = 0 if (x + y) % 2 else 9
            top_color = (66 + shade, 91 + shade, 116 + shade)
            side_color = (38 + shade, 56 + shade, 77 + shade)
            edge_color = (107, 146, 176)

        pygame.draw.polygon(surface, side_color, bottom_south)
        pygame.draw.polygon(surface, self._shade(side_color, 0.78), bottom_east)
        pygame.draw.polygon(surface, top_color, top)
        pygame.draw.polygon(surface, edge_color, top, max(1, round(self.tile_size / 28)))
        self._draw_stone_surface(surface, top, x, y, kind)

        if kind is TileType.GOAL:
            center = self._average(top)
            pygame.draw.circle(surface, settings.COLOR_GOAL_RING, center, max(4, round(self.tile_size * 0.14)), 2)
            pygame.draw.circle(surface, (255, 227, 128), center, max(2, round(self.tile_size * 0.045)))
        elif kind is TileType.FRAGILE:
            self._draw_diamond_cross(surface, top, (247, 144, 80))
        elif kind is TileType.BRIDGE:
            self._draw_planks(surface, top)

    def _draw_void(self, surface: pygame.Surface, x: int, y: int) -> None:
        corners = self.tile_corners(x, y)
        back = self._average(corners)
        rim = [self._lerp(back, corner, 0.92) for corner in corners]
        cavity = [self._lerp(back, corner, 0.76) for corner in corners]
        pygame.draw.polygon(surface, (8, 12, 20), corners)
        pygame.draw.polygon(surface, (23, 33, 47), rim)
        pygame.draw.polygon(surface, (2, 4, 8), cavity)
        pygame.draw.polygon(surface, (43, 55, 72), rim, max(1, round(self.tile_size / 32)))
        pygame.draw.line(surface, (13, 18, 27), rim[0], rim[1], 1)

    def _draw_stone_surface(
        self,
        surface: pygame.Surface,
        corners: list[tuple[int, int]],
        x: int,
        y: int,
        kind: TileType,
    ) -> None:
        if kind not in {TileType.FLOOR, TileType.FRAGILE}:
            return

        center = self._average(corners)
        inset = [self._lerp(center, corner, 0.84) for corner in corners]
        highlight = (105, 137, 164) if kind is TileType.FLOOR else (255, 174, 101)
        shadow = (47, 69, 91) if kind is TileType.FLOOR else (124, 61, 42)
        pygame.draw.polygon(surface, shadow, inset, max(1, round(self.tile_size / 45)))
        inner = [self._lerp(center, corner, 0.95) for corner in corners]
        pygame.draw.line(surface, highlight, inner[0], inner[1], 1)
        pygame.draw.line(surface, highlight, inner[0], inner[3], 1)

        grain_color = (81, 108, 132) if kind is TileType.FLOOR else (221, 119, 69)
        edge_a = self._lerp(corners[0], corners[1], 0.35)
        edge_b = self._lerp(corners[0], corners[1], 0.65)
        edge_c = self._lerp(corners[2], corners[3], 0.35)
        edge_d = self._lerp(corners[2], corners[3], 0.65)
        offset = ((x * 3 + y * 5) % 3) - 1
        pygame.draw.line(
            surface,
            grain_color,
            (edge_a[0] + offset, edge_a[1] + 1),
            (edge_b[0] + offset, edge_b[1] + 1),
            1,
        )
        if (x + y) % 3 == 0:
            pygame.draw.circle(surface, highlight, center, max(1, round(self.tile_size * 0.018)))

    @staticmethod
    def _bridge_tile_transition(
        bridge_id: str | None,
        transition: tuple[GameState, GameState, float] | None,
    ) -> tuple[bool, bool, float] | None:
        if bridge_id is None or transition is None:
            return None
        start, end, progress = transition
        bridge = start.board.bridges[bridge_id]
        before = start.bridge_map.get(bridge_id, bridge.initial_state) == "open"
        after = end.bridge_map.get(bridge_id, bridge.initial_state) == "open"
        return before, after, min(1.0, max(0.0, progress))

    def _draw_folding_bridge(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        was_open: bool,
        will_open: bool,
        progress: float,
    ) -> None:
        eased = progress * progress * (3 - 2 * progress)
        fold = (1.0 - eased if will_open else eased) * 1.50
        cosine = max(0.0, math.cos(fold))
        sine = math.sin(fold)

        hinge_a = self.project(x, y, 0.02)
        hinge_b = self.project(x + 1, y, 0.02)
        far_b = self.project(x + 1, y + cosine, sine)
        far_a = self.project(x, y + cosine, sine)
        top = [hinge_a, hinge_b, far_b, far_a]

        pygame.draw.polygon(surface, (10, 17, 27), self.tile_corners(x, y))
        thickness = self.tile_depth
        bottom = [
            hinge_a,
            hinge_b,
            self.project(x + 1, y + cosine, sine - thickness / self.elevation),
            self.project(x, y + cosine, sine - thickness / self.elevation),
        ]
        pygame.draw.polygon(surface, (29, 83, 91), [bottom[1], bottom[2], top[2], top[1]])
        pygame.draw.polygon(surface, (21, 59, 70), [bottom[3], bottom[0], top[0], top[3]])
        color = settings.COLOR_BRIDGE_OPEN if will_open else settings.COLOR_BRIDGE_CLOSED
        pygame.draw.polygon(surface, color, top)
        pygame.draw.polygon(surface, settings.COLOR_BRIDGE_OPEN_BORDER, top, 2)

        if progress > 0.16:
            self._draw_planks(surface, top)
        if progress < 0.88:
            hinge_mid = self._average([hinge_a, hinge_b])
            pygame.draw.circle(surface, (213, 235, 225), hinge_mid, max(2, round(self.tile_size * 0.035)))

    def _draw_switch(self, surface: pygame.Surface, switch: Switch) -> None:
        corners = self.tile_corners(*switch.position)
        center = self._average(corners)
        width = max(7, round(self.tile_size * 0.28))
        height = max(4, round(width * 0.45))
        colors = {
            "soft": settings.COLOR_SWITCH_SOFT,
            "heavy": settings.COLOR_SWITCH_HEAVY,
            "split": settings.COLOR_SWITCH_SPLIT,
        }
        color = colors[switch.type]
        plate_center = self.project(switch.position[0] + 0.5, switch.position[1] + 0.5, 0.07)
        center = plate_center
        shadow = pygame.Rect(center[0] - width, center[1] - height // 2 + 5, width * 2, height * 2)
        pygame.draw.ellipse(surface, (16, 22, 32), shadow)
        plate = [
            (center[0] - width, center[1]),
            (center[0], center[1] - height),
            (center[0] + width, center[1]),
            (center[0], center[1] + height),
        ]
        pygame.draw.polygon(surface, self._shade(color, 0.48), [(px, py + 4) for px, py in plate])
        pygame.draw.polygon(surface, color, plate)
        pygame.draw.polygon(surface, (255, 247, 215), plate, 1)
        for layer in range(3):
            layer_rect = pygame.Rect(
                center[0] - width + layer * 2,
                center[1] - height + layer,
                max(2, width * 2 - layer * 4),
                max(2, height * 2 - layer * 2),
            )
            pygame.draw.ellipse(surface, self._shade(color, 0.75 + 0.12 * layer), layer_rect)
        glyph = {"soft": "S", "heavy": "H", "split": "X"}[switch.type]
        glyph_surface = self.switch_font.render(glyph, True, (27, 34, 43))
        surface.blit(glyph_surface, glyph_surface.get_rect(center=center))

    def _draw_planks(self, surface: pygame.Surface, corners: list[tuple[int, int]]) -> None:
        rail_color = (172, 247, 221)
        rail_width = max(2, round(self.tile_size / 20))
        pygame.draw.line(surface, rail_color, corners[0], corners[3], rail_width)
        pygame.draw.line(surface, rail_color, corners[1], corners[2], rail_width)
        for ratio in (0.3, 0.5, 0.7):
            left = self._lerp(corners[0], corners[3], ratio)
            right = self._lerp(corners[1], corners[2], ratio)
            pygame.draw.line(surface, (35, 107, 112), left, right, max(1, round(self.tile_size / 28)))

    @staticmethod
    def _draw_diamond_cross(
        surface: pygame.Surface,
        corners: list[tuple[int, int]],
        color: tuple[int, int, int],
    ) -> None:
        center = BoardRenderer._average(corners)
        pygame.draw.line(surface, color, corners[0], corners[2], 1)
        pygame.draw.line(surface, color, corners[1], corners[3], 1)
        pygame.draw.circle(surface, color, center, 2)

    @staticmethod
    def _average(points: list[tuple[int, int]]) -> tuple[int, int]:
        return round(sum(point[0] for point in points) / len(points)), round(
            sum(point[1] for point in points) / len(points)
        )

    @staticmethod
    def _lerp(
        start: tuple[int, int],
        end: tuple[int, int],
        amount: float,
    ) -> tuple[int, int]:
        return round(start[0] + (end[0] - start[0]) * amount), round(
            start[1] + (end[1] - start[1]) * amount
        )

    @staticmethod
    def _lerp(start: tuple[int, int], end: tuple[int, int], amount: float) -> tuple[int, int]:
        return round(start[0] + (end[0] - start[0]) * amount), round(
            start[1] + (end[1] - start[1]) * amount
        )

    @staticmethod
    def _shade(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return tuple(max(0, min(255, round(channel * amount))) for channel in color)

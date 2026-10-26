"""
Block Renderer for Bloxorz.
Draws the 1x1x2 rectangular block across all orientations (Standing, Lying_H, Lying_V)
and split 1x1x1 cubes with active cube indicators.
"""
from __future__ import annotations

import pygame
from core.interfaces import BlockState, GameState, Orientation
from config import settings
from rendering.board_renderer import BoardRenderer


class BlockRenderer:
    """Renders the player block or split cubes atop the board."""

    def __init__(self, board_renderer: BoardRenderer):
        self.board_renderer = board_renderer

    def draw(self, surface: pygame.Surface, state: GameState) -> None:
        block = state.block
        if block.is_split and block.cube_positions:
            self._draw_split_cubes(surface, block)
        else:
            self._draw_solid_block(surface, block)

    def _draw_solid_block(self, surface: pygame.Surface, block: BlockState) -> None:
        r, c = block.r, block.c
        cell_rect = self.board_renderer.get_cell_rect(r, c)
        ts = self.board_renderer.tile_size
        pad = max(2, ts // 14)

        if block.orientation == Orientation.STANDING:
            # 1x1 upright block: draw with prominent 3D bevel to convey height
            b_rect = cell_rect.inflate(-pad * 2, -pad * 2)
            pygame.draw.rect(surface, settings.COLOR_BLOCK, b_rect, border_radius=4)
            # Inset bevel
            inner_rect = b_rect.inflate(-ts // 4, -ts // 4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_TOP, inner_rect, border_radius=3)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, b_rect, 2, border_radius=4)

        elif block.orientation == Orientation.LYING_H:
            # 2x1 horizontal block
            rect_right = self.board_renderer.get_cell_rect(r, c + 1)
            full_w = cell_rect.width + rect_right.width
            full_rect = pygame.Rect(cell_rect.left + pad, cell_rect.top + pad, full_w - pad * 2, cell_rect.height - pad * 2)

            pygame.draw.rect(surface, settings.COLOR_BLOCK, full_rect, border_radius=4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, full_rect, 2, border_radius=4)

            # Center seam
            mid_x = cell_rect.right
            pygame.draw.line(surface, settings.COLOR_BLOCK_BORDER, (mid_x, full_rect.top + 2), (mid_x, full_rect.bottom - 2), 2)
            # Subtle top highlights
            pygame.draw.line(surface, settings.COLOR_BLOCK_TOP, (full_rect.left + 3, full_rect.top + 3), (full_rect.right - 3, full_rect.top + 3), 1)

        elif block.orientation == Orientation.LYING_V:
            # 1x2 vertical block
            rect_down = self.board_renderer.get_cell_rect(r + 1, c)
            full_h = cell_rect.height + rect_down.height
            full_rect = pygame.Rect(cell_rect.left + pad, cell_rect.top + pad, cell_rect.width - pad * 2, full_h - pad * 2)

            pygame.draw.rect(surface, settings.COLOR_BLOCK, full_rect, border_radius=4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, full_rect, 2, border_radius=4)

            # Center seam
            mid_y = cell_rect.bottom
            pygame.draw.line(surface, settings.COLOR_BLOCK_BORDER, (full_rect.left + 2, mid_y), (full_rect.right - 2, mid_y), 2)
            # Subtle top highlight
            pygame.draw.line(surface, settings.COLOR_BLOCK_TOP, (full_rect.left + 3, full_rect.top + 3), (full_rect.right - 3, full_rect.top + 3), 1)

    def _draw_split_cubes(self, surface: pygame.Surface, block: BlockState) -> None:
        if not block.cube_positions:
            return
        ts = self.board_renderer.tile_size
        pad = max(4, ts // 8)

        for i, pos in enumerate(block.cube_positions):
            is_active = (i == block.active_cube)
            cell_rect = self.board_renderer.get_cell_rect(pos[0], pos[1])
            cube_rect = cell_rect.inflate(-pad * 2, -pad * 2)

            if is_active:
                # Active cube: glowing border & bright fill
                pygame.draw.rect(surface, settings.COLOR_BLOCK_TOP, cube_rect, border_radius=4)
                pygame.draw.rect(surface, settings.COLOR_BLOCK_ACTIVE, cube_rect, 3, border_radius=4)
                # Draw small 'A' or active dot inside
                center = cube_rect.center
                pygame.draw.circle(surface, (255, 255, 255), center, max(3, ts // 10))
            else:
                # Inactive cube: dimmed fill
                pygame.draw.rect(surface, settings.COLOR_BLOCK_INACTIVE, cube_rect, border_radius=4)
                pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, cube_rect, 1, border_radius=4)

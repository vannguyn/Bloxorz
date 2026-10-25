"""
Block Renderer for Bloxorz.
Draws the 1x1x2 rectangular block across all orientations (Standing, Lying_H, Lying_V)
and split 1x1x1 cubes with active cube indicators.
"""
from __future__ import annotations

import pygame
from core.block import Block, Cube, Orientation
from core.game_state import GameState
from config import settings
from entities.block_entity import BlockEntity
from rendering.board_renderer import BoardRenderer


class BlockRenderer:
    """Renders the player block or split cubes atop the board."""

    def __init__(self, board_renderer: BoardRenderer):
        self.board_renderer = board_renderer

    def draw(
        self,
        surface: pygame.Surface,
        state: GameState,
        *,
        transition_to: GameState | None = None,
        progress: float = 0.0,
    ) -> None:
        if transition_to is not None and self._draw_transition(
            surface, state, transition_to, min(1.0, max(0.0, progress))
        ):
            return
        block = state.block
        if state.is_split:
            self._draw_split_cubes(surface, state)
        else:
            entity = BlockEntity(block)
            if not isinstance(entity.piece, Block):
                raise TypeError("A non-split game state must contain a solid block")
            self._draw_solid_block(surface, entity.piece)

    def _draw_transition(
        self,
        surface: pygame.Surface,
        start: GameState,
        end: GameState,
        progress: float,
    ) -> bool:
        if start.is_split != end.is_split:
            return False
        if start.is_split:
            if (
                start.controlled_index != end.controlled_index
                and sorted(piece.position for piece in start.pieces)
                == sorted(piece.position for piece in end.pieces)
            ):
                return False
            start_pieces = start.pieces
            end_pieces = end.pieces
            if len(start_pieces) != len(end_pieces):
                return False
            start_positions = [piece.position for piece in start_pieces]
            end_positions = [piece.position for piece in end_pieces]
            direct = sum(
                abs(a[0] - b[0]) + abs(a[1] - b[1])
                for a, b in zip(start_positions, end_positions)
            )
            swapped = sum(
                abs(a[0] - b[1]) + abs(a[1] - b[0])
                for a, b in zip(start_positions, reversed(end_positions))
            )
            if swapped < direct:
                end_positions.reverse()
            for index, (origin, target) in enumerate(zip(start_positions, end_positions)):
                origin_rect = self.board_renderer.get_cell_rect(*origin)
                target_rect = self.board_renderer.get_cell_rect(*target)
                rect = pygame.Rect(
                    round(origin_rect.x + (target_rect.x - origin_rect.x) * progress),
                    round(origin_rect.y + (target_rect.y - origin_rect.y) * progress),
                    origin_rect.width,
                    origin_rect.height,
                )
                self._draw_cube_rect(surface, rect, active=index == 0)
            return True

        start_piece = start.block
        end_piece = end.block
        if not isinstance(start_piece, Block) or not isinstance(end_piece, Block):
            return False
        start_rect = self._block_rect(start_piece)
        end_rect = self._block_rect(end_piece)
        rect = pygame.Rect(
            round(start_rect.x + (end_rect.x - start_rect.x) * progress),
            round(start_rect.y + (end_rect.y - start_rect.y) * progress),
            round(start_rect.width + (end_rect.width - start_rect.width) * progress),
            round(start_rect.height + (end_rect.height - start_rect.height) * progress),
        )
        pad = max(2, self.board_renderer.tile_size // 14)
        body = rect.inflate(-pad * 2, -pad * 2)
        pygame.draw.rect(surface, settings.COLOR_BLOCK, body, border_radius=4)
        pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, body, 2, border_radius=4)
        return True

    def _block_rect(self, block: Block) -> pygame.Rect:
        cells = block.cells
        left = min(position[0] for position in cells)
        top = min(position[1] for position in cells)
        right = max(position[0] for position in cells)
        bottom = max(position[1] for position in cells)
        first = self.board_renderer.get_cell_rect(left, top)
        last = self.board_renderer.get_cell_rect(right, bottom)
        return pygame.Rect(first.left, first.top, last.right - first.left, last.bottom - first.top)

    def _draw_cube_entity(self, surface: pygame.Surface, entity: BlockEntity) -> None:
        cell_rect = self.board_renderer.get_cell_rect(*entity.piece.position)
        self._draw_cube_rect(surface, cell_rect, entity.active)

    def _draw_cube_rect(self, surface: pygame.Surface, cell_rect: pygame.Rect, active: bool) -> None:
        ts = self.board_renderer.tile_size
        pad = max(4, ts // 8)
        cube_rect = cell_rect.inflate(-pad * 2, -pad * 2)
        if active:
            pygame.draw.rect(surface, settings.COLOR_BLOCK_TOP, cube_rect, border_radius=4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_ACTIVE, cube_rect, 3, border_radius=4)
            pygame.draw.circle(surface, (255, 255, 255), cube_rect.center, max(3, ts // 10))
        else:
            pygame.draw.rect(surface, settings.COLOR_BLOCK_INACTIVE, cube_rect, border_radius=4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, cube_rect, 1, border_radius=4)

    def _draw_solid_block(self, surface: pygame.Surface, block: Block) -> None:
        x, y = block.position
        cell_rect = self.board_renderer.get_cell_rect(x, y)
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

        elif block.orientation is Orientation.HORIZONTAL:
            # 2x1 horizontal block
            rect_right = self.board_renderer.get_cell_rect(x + 1, y)
            full_w = cell_rect.width + rect_right.width
            full_rect = pygame.Rect(cell_rect.left + pad, cell_rect.top + pad, full_w - pad * 2, cell_rect.height - pad * 2)

            pygame.draw.rect(surface, settings.COLOR_BLOCK, full_rect, border_radius=4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, full_rect, 2, border_radius=4)

            # Center seam
            mid_x = cell_rect.right
            pygame.draw.line(surface, settings.COLOR_BLOCK_BORDER, (mid_x, full_rect.top + 2), (mid_x, full_rect.bottom - 2), 2)
            # Subtle top highlights
            pygame.draw.line(surface, settings.COLOR_BLOCK_TOP, (full_rect.left + 3, full_rect.top + 3), (full_rect.right - 3, full_rect.top + 3), 1)

        elif block.orientation is Orientation.VERTICAL:
            # 1x2 vertical block
            rect_down = self.board_renderer.get_cell_rect(x, y + 1)
            full_h = cell_rect.height + rect_down.height
            full_rect = pygame.Rect(cell_rect.left + pad, cell_rect.top + pad, cell_rect.width - pad * 2, full_h - pad * 2)

            pygame.draw.rect(surface, settings.COLOR_BLOCK, full_rect, border_radius=4)
            pygame.draw.rect(surface, settings.COLOR_BLOCK_BORDER, full_rect, 2, border_radius=4)

            # Center seam
            mid_y = cell_rect.bottom
            pygame.draw.line(surface, settings.COLOR_BLOCK_BORDER, (full_rect.left + 2, mid_y), (full_rect.right - 2, mid_y), 2)
            # Subtle top highlight
            pygame.draw.line(surface, settings.COLOR_BLOCK_TOP, (full_rect.left + 3, full_rect.top + 3), (full_rect.right - 3, full_rect.top + 3), 1)

    def _draw_split_cubes(self, surface: pygame.Surface, state: GameState) -> None:
        # GameState.pieces orders the controlled cube first.
        for i, piece in enumerate(state.pieces):
            assert isinstance(piece, Cube)
            entity = BlockEntity(piece, active=i == 0)
            self._draw_cube_entity(surface, entity)

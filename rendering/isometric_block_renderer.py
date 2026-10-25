"""
3D Isometric Block Renderer for Bloxorz.
Draws the extruded 1x1x2 block across Standing, Lying_H, and Lying_V orientations,
and split 1x1x1 cubes with active cube indicators and lightweight hop/slide interpolation.
"""
from __future__ import annotations

import math
import pygame
from core.interfaces import BlockState, GameState, Orientation
from config import settings
from rendering.isometric_board_renderer import IsometricBoardRenderer


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Applies a lighting shade factor (0.0 to 1.0) to an RGB tuple."""
    return (
        max(0, min(255, round(color[0] * factor))),
        max(0, min(255, round(color[1] * factor))),
        max(0, min(255, round(color[2] * factor))),
    )


class IsometricBlockRenderer:
    """Renders the player block in 3D isometric projection with smooth transitions."""

    def __init__(self, board_renderer: IsometricBoardRenderer):
        self.board_renderer = board_renderer

    def draw(
        self,
        surface: pygame.Surface,
        state: GameState,
        transition_to: GameState | None = None,
        progress: float = 0.0,
    ) -> None:
        """
        Draws the block or split cubes atop the isometric board.

        If transition_to is provided and progress is between 0.0 and 1.0:
        - Applies linear position interpolation (LERP).
        - Applies a parabolic vertical hop lift: 0.35 * sin(pi * t).
        - Snaps orientation at t = 0.5.
        """
        if transition_to is not None:
            t = max(0.0, min(1.0, float(progress)))
        else:
            t = 0.0

        # Handle split state transitions vs solid block transitions
        is_curr_split = state.block.is_split and bool(state.block.cube_positions)
        is_next_split = (
            transition_to is not None
            and transition_to.block.is_split
            and bool(transition_to.block.cube_positions)
        )

        if is_curr_split and is_next_split:
            self._draw_split_transition(surface, state, transition_to, t)
        elif is_curr_split and not is_next_split:
            # Transition from split to merged solid block
            if t < 0.5:
                self._draw_split_cubes(surface, state.block, lift=0.35 * math.sin(math.pi * t))
            else:
                target = transition_to if transition_to is not None else state
                self._draw_solid_block_interpolated(surface, target.block, target.block, 1.0, lift=0.35 * math.sin(math.pi * t))
        elif not is_curr_split and is_next_split:
            # Transition from solid block to split cubes
            if t < 0.5:
                self._draw_solid_block_interpolated(surface, state.block, state.block, 0.0, lift=0.35 * math.sin(math.pi * t))
            else:
                self._draw_split_cubes(surface, transition_to.block, lift=0.35 * math.sin(math.pi * t))
        elif is_curr_split:
            self._draw_split_cubes(surface, state.block, lift=0.0)
        else:
            # Both are solid block states
            target_block = transition_to.block if transition_to is not None else state.block
            lift = 0.35 * math.sin(math.pi * t) if transition_to is not None else 0.0
            self._draw_solid_block_interpolated(surface, state.block, target_block, t, lift=lift)

    def _draw_solid_block_interpolated(
        self,
        surface: pygame.Surface,
        start_block: BlockState,
        end_block: BlockState,
        t: float,
        lift: float = 0.0,
    ) -> None:
        """Draws a solid block interpolated between start_block and end_block."""
        sr, sc = start_block.r, start_block.c
        er, ec = end_block.r, end_block.c

        # Linear position interpolation
        r = (1.0 - t) * sr + t * er
        c = (1.0 - t) * sc + t * ec

        # Snap orientation at t = 0.5
        ori = start_block.orientation if t < 0.5 else end_block.orientation

        if ori == Orientation.STANDING:
            dr, dc, h = 1.0, 1.0, 2.0
        elif ori == Orientation.LYING_H:
            dr, dc, h = 1.0, 2.0, 1.0
        elif ori == Orientation.LYING_V:
            dr, dc, h = 2.0, 1.0, 1.0
        else:
            dr, dc, h = 1.0, 1.0, 2.0

        self._draw_cuboid(
            surface,
            r=r,
            c=c,
            z=lift,
            dr=dr,
            dc=dc,
            h=h,
            base_color=settings.COLOR_BLOCK,
            top_color=settings.COLOR_BLOCK_TOP,
            border_color=settings.COLOR_BLOCK_BORDER,
            orientation=ori,
        )

    def _draw_split_cubes(
        self,
        surface: pygame.Surface,
        block: BlockState,
        lift: float = 0.0,
    ) -> None:
        """Renders static or lifted split cubes with depth sorting."""
        if not block.cube_positions:
            return

        cubes_info = []
        for i, (r, c) in enumerate(block.cube_positions):
            is_active = (i == block.active_cube)
            cubes_info.append((r, c, lift if is_active else 0.0, is_active))

        # Depth sort by (r + c, r) ascending (painter's algorithm)
        cubes_info.sort(key=lambda item: (item[0] + item[1], item[0]))

        for r, c, z, is_active in cubes_info:
            self._draw_split_cube(surface, float(r), float(c), z, is_active)

    def _draw_split_transition(
        self,
        surface: pygame.Surface,
        curr_state: GameState,
        next_state: GameState,
        t: float,
    ) -> None:
        """Renders smoothly moving split cubes."""
        curr_positions = curr_state.block.cube_positions or ()
        next_positions = next_state.block.cube_positions or ()
        active_idx = curr_state.block.active_cube if t < 0.5 else next_state.block.active_cube

        cubes_info = []
        for i in range(len(curr_positions)):
            sr, sc = curr_positions[i]
            er, ec = next_positions[i] if i < len(next_positions) else (sr, sc)

            moved = (sr != er or sc != ec)
            r = (1.0 - t) * sr + t * er if moved else float(sr)
            c = (1.0 - t) * sc + t * ec if moved else float(sc)
            lift = 0.35 * math.sin(math.pi * t) if moved else 0.0
            is_active = (i == active_idx)
            cubes_info.append((r, c, lift, is_active))

        # Depth sort by (r + c, r) ascending
        cubes_info.sort(key=lambda item: (item[0] + item[1], item[0]))

        for r, c, z, is_active in cubes_info:
            self._draw_split_cube(surface, r, c, z, is_active)

    def _draw_split_cube(
        self,
        surface: pygame.Surface,
        r: float,
        c: float,
        z: float,
        is_active: bool,
    ) -> None:
        """Draws an individual 1x1x1 cube in split mode with active highlight."""
        if is_active:
            base_col = settings.COLOR_BLOCK
            top_col = settings.COLOR_BLOCK_TOP
        else:
            base_col = settings.COLOR_BLOCK_INACTIVE
            top_col = settings.COLOR_BLOCK_INACTIVE

        self._draw_cuboid(
            surface,
            r=r,
            c=c,
            z=z,
            dr=1.0,
            dc=1.0,
            h=1.0,
            base_color=base_col,
            top_color=top_col,
            border_color=settings.COLOR_BLOCK_BORDER,
        )

        if is_active:
            # Active badge and golden accent on the top face
            ts = self.board_renderer.tile_size
            top_corners = [
                self.board_renderer.project(r, c, z + 1.0),
                self.board_renderer.project(r, c + 1.0, z + 1.0),
                self.board_renderer.project(r + 1.0, c + 1.0, z + 1.0),
                self.board_renderer.project(r + 1.0, c, z + 1.0),
            ]
            # Glowing golden outline on top diamond
            pygame.draw.polygon(surface, settings.COLOR_BLOCK_ACTIVE, top_corners, 2)

            # Circular active badge in center
            cx, cy = self.board_renderer.project(r + 0.5, c + 0.5, z + 1.0)
            badge_r = max(4, round(ts * 0.16))
            pygame.draw.circle(surface, settings.COLOR_BLOCK_ACTIVE, (cx, cy), badge_r)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(2, round(badge_r * 0.5)))

    def _draw_cuboid(
        self,
        surface: pygame.Surface,
        r: float,
        c: float,
        z: float,
        dr: float,
        dc: float,
        h: float,
        base_color: tuple[int, int, int],
        top_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
        orientation: Orientation | None = None,
    ) -> None:
        """
        Draws a 3D isometric cuboid spanning [r, r+dr] x [c, c+dc] x [z, z+h].
        Visible faces:
        - Top face: z + h
        - Left side face: facing +r (down-left)
        - Right side face: facing +c (down-right)
        """
        # Top vertices at elevation z + h
        t_top = self.board_renderer.project(r, c, z + h)
        t_right = self.board_renderer.project(r, c + dc, z + h)
        t_bottom = self.board_renderer.project(r + dr, c + dc, z + h)
        t_left = self.board_renderer.project(r + dr, c, z + h)

        # Bottom vertices at elevation z
        b_right = self.board_renderer.project(r, c + dc, z)
        b_bottom = self.board_renderer.project(r + dr, c + dc, z)
        b_left = self.board_renderer.project(r + dr, c, z)

        # 1. Left side face: [t_left, t_bottom, b_bottom, b_left]
        left_poly = [t_left, t_bottom, b_bottom, b_left]
        color_left = _shade(base_color, 0.75)
        pygame.draw.polygon(surface, color_left, left_poly)
        pygame.draw.polygon(surface, border_color, left_poly, 2)

        # 2. Right side face: [t_bottom, t_right, b_right, b_bottom]
        right_poly = [t_bottom, t_right, b_right, b_bottom]
        color_right = _shade(base_color, 0.55)
        pygame.draw.polygon(surface, color_right, right_poly)
        pygame.draw.polygon(surface, border_color, right_poly, 2)

        # Center vertical corner edge
        pygame.draw.line(surface, border_color, t_bottom, b_bottom, 2)

        # 3. Top face: [t_top, t_right, t_bottom, t_left]
        top_poly = [t_top, t_right, t_bottom, t_left]
        pygame.draw.polygon(surface, top_color, top_poly)
        pygame.draw.polygon(surface, border_color, top_poly, 2)

        # Subtle bevel highlight on top back edges
        highlight_color = (min(255, top_color[0] + 30), min(255, top_color[1] + 30), min(255, top_color[2] + 30))
        pygame.draw.line(surface, highlight_color, t_left, t_top, 1)
        pygame.draw.line(surface, highlight_color, t_top, t_right, 1)

        # Internal block seams indicating unit-cube composition
        if orientation == Orientation.STANDING and h >= 1.5:
            # Horizontal seam around standing block at z + 1.0
            mid_left = self.board_renderer.project(r + dr, c, z + 1.0)
            mid_bottom = self.board_renderer.project(r + dr, c + dc, z + 1.0)
            mid_right = self.board_renderer.project(r, c + dc, z + 1.0)
            pygame.draw.line(surface, border_color, mid_left, mid_bottom, 2)
            pygame.draw.line(surface, border_color, mid_bottom, mid_right, 2)

        elif orientation == Orientation.LYING_H and dc >= 1.5:
            # Seam splitting horizontal block at c + 1.0
            st_top = self.board_renderer.project(r, c + 1.0, z + h)
            st_bottom = self.board_renderer.project(r + dr, c + 1.0, z + h)
            sb_bottom = self.board_renderer.project(r + dr, c + 1.0, z)
            pygame.draw.line(surface, border_color, st_top, st_bottom, 2)
            pygame.draw.line(surface, border_color, st_bottom, sb_bottom, 2)

        elif orientation == Orientation.LYING_V and dr >= 1.5:
            # Seam splitting vertical block at r + 1.0
            st_left = self.board_renderer.project(r + 1.0, c, z + h)
            st_bottom = self.board_renderer.project(r + 1.0, c + dc, z + h)
            sb_bottom = self.board_renderer.project(r + 1.0, c + dc, z)
            pygame.draw.line(surface, border_color, st_left, st_bottom, 2)
            pygame.draw.line(surface, border_color, st_bottom, sb_bottom, 2)

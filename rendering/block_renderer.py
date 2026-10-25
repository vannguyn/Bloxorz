"""Isometric 3D cuboid renderer for Bloxorz blocks and split cubes."""

from __future__ import annotations

import math

import pygame

from config import settings
from core.block import Block, Cube, Orientation, Piece
from core.game_state import GameState
from rendering.board_renderer import BoardRenderer

Vector3 = tuple[float, float, float]


class BlockRenderer:
    """Draws extruded cuboids and animates roll transitions in 3D space."""

    CAMERA = (-1.0, 1.0, 1.4)

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
        progress = self._ease(min(1.0, max(0.0, progress)))
        if transition_to is not None and self._draw_transition(
            surface, state, transition_to, progress
        ):
            return

        if state.is_split:
            for index, piece in enumerate(state.pieces):
                if isinstance(piece, Cube):
                    self._draw_cube(surface, piece.position, index == 0, 0.0)
        elif isinstance(state.block, Block):
            self._draw_block(surface, state.block, settings.COLOR_BLOCK, 0.0)

    def _draw_transition(
        self,
        surface: pygame.Surface,
        start: GameState,
        end: GameState,
        progress: float,
    ) -> bool:
        if start.is_split or end.is_split:
            if start.is_split and end.is_split:
                if (
                    start.controlled_index != end.controlled_index
                    and sorted(piece.position for piece in start.pieces)
                    == sorted(piece.position for piece in end.pieces)
                ):
                    return False
                old = list(start.pieces)
                new = list(end.pieces)
                if len(old) != len(new):
                    return False
                if self._match_swapped_cubes(old, new):
                    new.reverse()
                for index, (first, second) in enumerate(zip(old, new)):
                    if not isinstance(first, Cube) or not isinstance(second, Cube):
                        return False
                    position = self._lerp3(
                        (first.position[0] + 0.5, first.position[1] + 0.5, 0.55),
                        (second.position[0] + 0.5, second.position[1] + 0.5, 0.55),
                        progress,
                    )
                    self._draw_cube(surface, (position[0] - 0.5, position[1] - 0.5), index == 0, math.sin(progress * math.pi) * 0.12)
                return True
            return False

        if not isinstance(start.block, Block) or not isinstance(end.block, Block):
            return False
        if start.block == end.block:
            return False

        start_center = self._piece_center(start.block)
        end_center = self._piece_center(end.block)
        old_axis = self._long_axis(start.block.orientation)
        new_axis = self._long_axis(end.block.orientation)
        axis, angle = self._rotation_between(old_axis, new_axis)
        center = self._lerp3(start_center, end_center, progress)
        center = (center[0], center[1], center[2] + math.sin(progress * math.pi) * 0.28)
        roll_progress = progress * progress * (3 - 2 * progress)
        self._draw_oriented_block(
            surface,
            center,
            old_axis,
            axis,
            angle * roll_progress,
            settings.COLOR_BLOCK,
        )
        return True

    def _draw_block(
        self,
        surface: pygame.Surface,
        block: Block,
        color: tuple[int, int, int],
        lift: float,
    ) -> None:
        self._draw_oriented_block(
            surface,
            self._piece_center(block, lift),
            self._long_axis(block.orientation),
            (0.0, 0.0, 0.0),
            0.0,
            color,
        )

    def _draw_oriented_block(
        self,
        surface: pygame.Surface,
        center: Vector3,
        start_axis: Vector3,
        roll_axis: Vector3,
        roll_angle: float,
        color: tuple[int, int, int],
    ) -> None:
        half_extents = (0.5, 0.5, 1.0)
        vertices: list[Vector3] = []
        for x_sign in (-1, 1):
            for y_sign in (-1, 1):
                for z_sign in (-1, 1):
                    local = (
                        x_sign * half_extents[0],
                        y_sign * half_extents[1],
                        z_sign * half_extents[2],
                    )
                    oriented = self._rotate_between(local, (0.0, 0.0, 1.0), start_axis)
                    if roll_angle:
                        oriented = self._rotate(oriented, roll_axis, roll_angle)
                    vertices.append(
                        (center[0] + oriented[0], center[1] + oriented[1], center[2] + oriented[2])
                    )
        self._draw_shadow(surface, center)
        self._draw_cuboid_faces(surface, vertices, color)
        seam = []
        for x_sign, y_sign in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            local = (x_sign * half_extents[0], y_sign * half_extents[1], 0.0)
            oriented = self._rotate_between(local, (0.0, 0.0, 1.0), start_axis)
            if roll_angle:
                oriented = self._rotate(oriented, roll_axis, roll_angle)
            seam.append(self._project((
                center[0] + oriented[0],
                center[1] + oriented[1],
                center[2] + oriented[2],
            )))
        pygame.draw.polygon(
            surface,
            self._shade(settings.COLOR_BLOCK_BORDER, 0.82),
            seam,
            max(1, round(self.board_renderer.tile_size / 38)),
        )

    def _draw_cube(self, surface: pygame.Surface, position: tuple[float, float], active: bool, lift: float) -> None:
        center = (position[0] + 0.5, position[1] + 0.5, 0.5 + lift)
        self._draw_shadow(surface, center)
        vertices = [
            (center[0] + x * 0.42, center[1] + y * 0.42, center[2] + z * 0.42)
            for x in (-1, 1)
            for y in (-1, 1)
            for z in (-1, 1)
        ]
        color = settings.COLOR_BLOCK_TOP if active else settings.COLOR_BLOCK_INACTIVE
        self._draw_cuboid_faces(surface, vertices, color, active=active)

    def _draw_shadow(self, surface: pygame.Surface, center: Vector3) -> None:
        shadow_center = self.board_renderer.project(center[0], center[1], 0.015)
        width = max(8, round(self.board_renderer.tile_size * 1.25))
        height = max(5, round(self.board_renderer.tile_height * 0.58))
        shadow = pygame.Surface((width + 4, height + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (4, 8, 15, 112), (2, 2, width, height))
        surface.blit(shadow, shadow.get_rect(center=shadow_center))

    def _draw_cuboid_faces(
        self,
        surface: pygame.Surface,
        vertices: list[Vector3],
        color: tuple[int, int, int],
        *,
        active: bool = False,
    ) -> None:
        sign_index = {
            (x, y, z): index
            for index, (x, y, z) in enumerate(
                ( (xs, ys, zs) for xs in (-1, 1) for ys in (-1, 1) for zs in (-1, 1) )
            )
        }
        face_specs = (
            ((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)], 0.76),
            ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)], 0.6),
            ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)], 0.86),
            ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], 0.68),
            ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], 1.12),
            ((0, 0, -1), [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)], 0.48),
        )
        faces = []
        for _, corners, shade in face_specs:
            points3d = [vertices[sign_index[corner]] for corner in corners]
            first_edge = tuple(points3d[1][i] - points3d[0][i] for i in range(3))
            second_edge = tuple(points3d[2][i] - points3d[0][i] for i in range(3))
            normal = self._cross(first_edge, second_edge)
            if self._dot(normal, self.CAMERA) <= 0:
                continue
            depth = sum(self._dot(point, self.CAMERA) for point in points3d) / 4
            points2d = [self._project(point) for point in points3d]
            faces.append((depth, points2d, self._shade(color, shade)))

        for _, points, face_color in sorted(faces, key=lambda face: face[0]):
            pygame.draw.polygon(surface, face_color, points)
            outline = settings.COLOR_BLOCK_ACTIVE if active else settings.COLOR_BLOCK_BORDER
            pygame.draw.polygon(surface, outline, points, max(1, round(self.board_renderer.tile_size / 35)))

    def _project(self, point: Vector3) -> tuple[int, int]:
        x, y, z = point
        return self.board_renderer.project(x, y, z)

    def _piece_center(self, block: Block, lift: float = 0.0) -> Vector3:
        if block.orientation is Orientation.STANDING:
            x, y = block.position[0] + 0.5, block.position[1] + 0.5
            z = 1.0
        elif block.orientation is Orientation.HORIZONTAL:
            x, y = block.position[0] + 1.0, block.position[1] + 0.5
            z = 0.5
        else:
            x, y = block.position[0] + 0.5, block.position[1] + 1.0
            z = 0.5
        return (x, y, z + lift)

    @staticmethod
    def _long_axis(orientation: Orientation) -> Vector3:
        if orientation is Orientation.HORIZONTAL:
            return (1.0, 0.0, 0.0)
        if orientation is Orientation.VERTICAL:
            return (0.0, 1.0, 0.0)
        return (0.0, 0.0, 1.0)

    @classmethod
    def _rotation_between(cls, start: Vector3, end: Vector3) -> tuple[Vector3, float]:
        axis = cls._cross(start, end)
        length = math.sqrt(cls._dot(axis, axis))
        if length < 1e-8:
            return (1.0, 0.0, 0.0), 0.0
        axis = (axis[0] / length, axis[1] / length, axis[2] / length)
        angle = math.acos(max(-1.0, min(1.0, cls._dot(start, end))))
        return axis, angle

    @classmethod
    def _rotate_between(cls, vector: Vector3, start: Vector3, end: Vector3) -> Vector3:
        axis, angle = cls._rotation_between(start, end)
        return cls._rotate(vector, axis, angle)

    @classmethod
    def _rotate(cls, vector: Vector3, axis: Vector3, angle: float) -> Vector3:
        if angle == 0:
            return vector
        cosine = math.cos(angle)
        sine = math.sin(angle)
        cross = cls._cross(axis, vector)
        dot = cls._dot(axis, vector)
        return (
            vector[0] * cosine + cross[0] * sine + axis[0] * dot * (1 - cosine),
            vector[1] * cosine + cross[1] * sine + axis[1] * dot * (1 - cosine),
            vector[2] * cosine + cross[2] * sine + axis[2] * dot * (1 - cosine),
        )

    @staticmethod
    def _cross(first: Vector3, second: Vector3) -> Vector3:
        return (
            first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0],
        )

    @staticmethod
    def _dot(first: Vector3, second: Vector3) -> float:
        return sum(a * b for a, b in zip(first, second))

    @staticmethod
    def _lerp3(start: Vector3, end: Vector3, amount: float) -> Vector3:
        return (
            start[0] + (end[0] - start[0]) * amount,
            start[1] + (end[1] - start[1]) * amount,
            start[2] + (end[2] - start[2]) * amount,
        )

    @staticmethod
    def _ease(amount: float) -> float:
        return amount * amount * (3 - 2 * amount)

    @staticmethod
    def _shade(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return tuple(max(0, min(255, round(channel * amount))) for channel in color)

    @staticmethod
    def _match_swapped_cubes(old: list[Piece], new: list[Piece]) -> bool:
        if len(old) != 2 or len(new) != 2:
            return False
        direct = sum(
            abs(first.position[0] - second.position[0]) + abs(first.position[1] - second.position[1])
            for first, second in zip(old, new)
            if isinstance(first, Cube) and isinstance(second, Cube)
        )
        swapped = sum(
            abs(first.position[0] - second.position[0]) + abs(first.position[1] - second.position[1])
            for first, second in zip(old, reversed(new))
            if isinstance(first, Cube) and isinstance(second, Cube)
        )
        return swapped < direct

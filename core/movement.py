"""Các hàm chuyển động thuần (không phụ thuộc board hoặc GUI)."""

from __future__ import annotations

from .block import Block, Cube, Direction


def move_block(block: Block, direction: Direction | str) -> Block:
    """Tính orientation/vị trí mới theo đúng bảng roll của Bloxorz."""
    return block.moved(direction)


def move_cube(cube: Cube, direction: Direction | str) -> Cube:
    """Di chuyển một cube đã split đúng một ô."""
    return cube.moved(direction)


def successors_for_piece(piece: Block | Cube) -> dict[Direction, Block | Cube]:
    """Sinh candidate cho cả bốn hướng; validation thuộc về game rules."""
    return {direction: piece.moved(direction) for direction in Direction.values()}


"""Các hàm chuyển động thuần (không phụ thuộc board hoặc GUI)."""

from __future__ import annotations

from .block import Block, Cube, Direction, Orientation


def move_block(block: Block, direction: Direction | str) -> Block:
    """Tính orientation/vị trí mới theo đúng bảng roll của Bloxorz."""
    direction = Direction.coerce(direction)
    x, y = block.position
    if block.orientation is Orientation.STANDING:
        transitions = {
            Direction.UP: ((x, y - 2), Orientation.VERTICAL),
            Direction.DOWN: ((x, y + 1), Orientation.VERTICAL),
            Direction.LEFT: ((x - 2, y), Orientation.HORIZONTAL),
            Direction.RIGHT: ((x + 1, y), Orientation.HORIZONTAL),
        }
    elif block.orientation is Orientation.HORIZONTAL:
        transitions = {
            Direction.UP: ((x, y - 1), Orientation.HORIZONTAL),
            Direction.DOWN: ((x, y + 1), Orientation.HORIZONTAL),
            Direction.LEFT: ((x - 1, y), Orientation.STANDING),
            Direction.RIGHT: ((x + 2, y), Orientation.STANDING),
        }
    else:
        transitions = {
            Direction.UP: ((x, y - 1), Orientation.STANDING),
            Direction.DOWN: ((x, y + 2), Orientation.STANDING),
            Direction.LEFT: ((x - 1, y), Orientation.VERTICAL),
            Direction.RIGHT: ((x + 1, y), Orientation.VERTICAL),
        }
    position, orientation = transitions[direction]
    return Block(position, orientation)


def move_cube(cube: Cube, direction: Direction | str) -> Cube:
    """Di chuyển một cube đã split đúng một ô."""
    direction = Direction.coerce(direction)
    x, y = cube.position
    offsets = {
        Direction.UP: (0, -1),
        Direction.DOWN: (0, 1),
        Direction.LEFT: (-1, 0),
        Direction.RIGHT: (1, 0),
    }
    dx, dy = offsets[direction]
    return Cube((x + dx, y + dy))


def successors_for_piece(piece: Block | Cube) -> dict[Direction, Block | Cube]:
    """Sinh candidate cho cả bốn hướng; validation thuộc về game rules."""
    return {direction: piece.moved(direction) for direction in Direction.values()}

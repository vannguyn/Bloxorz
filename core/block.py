"""Các kiểu dữ liệu hình học của Bloxorz.

Tọa độ trong project dùng dạng ``(x, y)``: x tăng sang phải và y tăng
xuống dưới. Với block nằm, ``position`` luôn là ô bên trái (horizontal)
hoặc ô phía trên (vertical).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple, Union


Position = Tuple[int, int]


class Orientation(str, Enum):
    STANDING = "standing"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    @classmethod
    def values(cls) -> tuple["Direction", ...]:
        return cls.UP, cls.DOWN, cls.LEFT, cls.RIGHT

    @classmethod
    def coerce(cls, value: "Direction | str") -> "Direction":
        if isinstance(value, cls):
            return value
        aliases = {
            "u": cls.UP, "up": cls.UP, "w": cls.UP,
            "d": cls.DOWN, "down": cls.DOWN, "s": cls.DOWN,
            "l": cls.LEFT, "left": cls.LEFT, "a": cls.LEFT,
            "r": cls.RIGHT, "right": cls.RIGHT, "e": cls.RIGHT,
        }
        try:
            return aliases[str(value).strip().lower()]
        except KeyError as exc:
            raise ValueError(f"Unknown direction: {value!r}") from exc


@dataclass(frozen=True, slots=True)
class Block:
    """Block 1 x 1 x 2 ở một trong ba orientation hợp lệ."""

    position: Position
    orientation: Orientation = Orientation.STANDING

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", tuple(self.position))
        if not isinstance(self.orientation, Orientation):
            object.__setattr__(self, "orientation", Orientation(self.orientation))
        if len(self.position) != 2 or not all(isinstance(v, int) for v in self.position):
            raise ValueError("Block position must be a pair of integers")

    @property
    def cells(self) -> tuple[Position, ...]:
        x, y = self.position
        if self.orientation is Orientation.STANDING:
            return ((x, y),)
        if self.orientation is Orientation.HORIZONTAL:
            return ((x, y), (x + 1, y))
        return ((x, y), (x, y + 1))

    @property
    def is_standing(self) -> bool:
        return self.orientation is Orientation.STANDING

    def moved(self, direction: Direction | str) -> "Block":
        """Return the rolled block; board validation belongs to ``game_rules``."""
        from .movement import move_block

        return move_block(self, direction)

    def as_key(self) -> tuple[int, int, str]:
        return (*self.position, self.orientation.value)


@dataclass(frozen=True, slots=True)
class Cube:
    """Một khối lập phương 1 x 1 sau khi block bị split."""

    position: Position

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", tuple(self.position))
        if len(self.position) != 2 or not all(isinstance(v, int) for v in self.position):
            raise ValueError("Cube position must be a pair of integers")

    @property
    def cells(self) -> tuple[Position, ...]:
        return (self.position,)

    def moved(self, direction: Direction | str) -> "Cube":
        from .movement import move_cube

        return move_cube(self, direction)

    def as_key(self) -> tuple[int, int, str]:
        return (*self.position, "cube")


Piece = Union[Block, Cube]


def cells_of(pieces: Iterable[Piece]) -> tuple[Position, ...]:
    """Lấy các ô bị chiếm, loại bỏ trùng lặp theo thứ tự ổn định."""
    result: list[Position] = []
    for piece in pieces:
        for cell in piece.cells:
            if cell not in result:
                result.append(cell)
    return tuple(result)

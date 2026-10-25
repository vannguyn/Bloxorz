"""
Temporary, pending M1 merge.
Authoritative Data Contracts as defined in docs/parallel-engineering-plan.en.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Orientation(Enum):
    STANDING = 0   # occupies single cell (r, c)
    LYING_H = 1    # occupies (r, c) and (r, c+1)
    LYING_V = 2    # occupies (r, c) and (r+1, c)

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            v = value.strip().upper()
            if v in ("STANDING", "STAND", "0"):
                return cls.STANDING
            if v in ("HORIZONTAL", "LYING_H", "H", "1"):
                return cls.LYING_H
            if v in ("VERTICAL", "LYING_V", "V", "2"):
                return cls.LYING_V
        return None


class TileType(Enum):
    VOID = 0
    FLOOR = 1
    GOAL = 2
    FRAGILE = 3    # orange — only supports lying block
    BRIDGE = 4     # passability controlled by switches
    SWITCH = 5

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            v = value.strip().upper()
            if v in cls.__members__:
                return cls.__members__[v]
        return None


@dataclass(frozen=True)
class BlockState:
    r: int
    c: int  # anchor: standing cell OR top/left of lying block
    orientation: Orientation
    # Split extension (PDF §2.5):
    is_split: bool = False
    cube_positions: tuple[tuple[int, int], tuple[int, int]] | None = None
    active_cube: int = 0  # 0 or 1, toggled by SPACE

    def occupied_cells(self) -> list[tuple[int, int]]:
        if self.is_split and self.cube_positions:
            return list(self.cube_positions)
        if self.orientation == Orientation.STANDING:
            return [(self.r, self.c)]
        if self.orientation == Orientation.LYING_H:
            return [(self.r, self.c), (self.r, self.c + 1)]
        if self.orientation == Orientation.LYING_V:
            return [(self.r, self.c), (self.r + 1, self.c)]
        return [(self.r, self.c)]


@dataclass(frozen=True)
class GameState:
    block: BlockState
    bridge_mask: int  # bitmask: bit i = 1 -> bridge i open, 0 -> closed

    def occupied_cells(self) -> list[tuple[int, int]]:
        return self.block.occupied_cells()


@dataclass
class Switch:
    id: str
    type: str  # "soft" | "heavy" | "split"
    position: tuple[int, int]
    bridge_ids: list[str]
    mode: str  # "toggle" | "permanent"
    destinations: tuple[tuple[int, int], tuple[int, int]] | None = None


@dataclass
class Level:
    width: int
    height: int
    tiles: dict[tuple[int, int], TileType]
    goal: tuple[int, int]
    start: BlockState
    bridges: dict[str, list[tuple[int, int]]]  # id -> tiles
    switches: list[Switch]
    split_rules: dict
    id: str = "level_01"
    name: str = "Level"
    initial_bridge_mask: int = 0


@dataclass
class SolverResult:
    path: list[str] | None       # e.g. ["R","R","U","SPACE"] or None if unsolvable
    expanded_nodes: int          # number of states dequeued/expanded
    search_time_ms: float        # wall-clock via time.perf_counter()
    peak_memory_kb: int          # via tracemalloc.get_traced_memory()[1]
    solution_length: int         # len(path) or -1 if None
    cost: float                  # sum of step_costs
    success: bool                # path is not None

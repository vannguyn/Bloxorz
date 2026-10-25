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


class TileType(Enum):
    VOID = 0
    FLOOR = 1
    GOAL = 2
    FRAGILE = 3    # orange — only supports lying block
    BRIDGE = 4     # passability controlled by switches


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
    # Runtime-only information kept by the UI adapter.  The original public
    # contract intentionally remains compatible with callers that only pass
    # ``block`` and ``bridge_mask``.
    locked_switches: frozenset[str] = frozenset()
    moves: int = 0

    def occupied_cells(self) -> list[tuple[int, int]]:
        return self.block.occupied_cells()


@dataclass
class Switch:
    id: str
    type: str  # "soft" | "heavy" | "split"
    position: tuple[int, int]
    bridge_ids: list[str]
    mode: str  # "toggle" | "permanent"
    effect_type: str = "bridge"
    state: str | None = None
    trigger: str = "enter"
    destinations: tuple[tuple[int, int], tuple[int, int]] | None = None
    lock_after_activation: bool = False


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
    difficulty: str = "basic"
    description: str = ""
    advanced_controls: tuple[str, ...] = ()
    bridge_initial_states: dict[str, str] | None = None


@dataclass
class SolverResult:
    path: list[str] | None       # e.g. ["R","R","U","SPACE"] or None if unsolvable
    expanded_nodes: int          # number of states dequeued/expanded
    search_time_ms: float        # wall-clock via time.perf_counter()
    peak_memory_kb: int          # via tracemalloc.get_traced_memory()[1]
    solution_length: int         # len(path) or -1 if None
    cost: float                  # sum of step_costs
    success: bool                # path is not None

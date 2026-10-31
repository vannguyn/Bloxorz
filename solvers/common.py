"""
Shared solver interfaces and execution metrics harness.
docs/parallel-engineering-plan.en.md §2.4 & §3.4
"""
from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod

from core.interfaces import BlockState, GameState, Level, Orientation, SolverResult, TileType


class StepCost:
    """Shared transition-cost policy used by UCS and A*.

    A* prepares the policy with ``StepCost(level)``. UCS inherits it and
    prepares the map penalties at the start of each solve.
    """

    COST_TIP_OVER = 1.0
    COST_STAND_UP = 1.5
    COST_ROLL_LYING = 1.2
    COST_CUBE_MOVE = 0.8
    COST_SWITCH_CUBE = 0.3
    PENALTY_FRAGILE = 0.5
    PENALTY_BRIDGE = 0.3
    PENALTY_EDGE = 0.1
    PENALTY_TOGGLE = 0.5

    # Lower bound for the default policy: all destination penalties are >= 0.
    MIN_EDGE_COST = min(
        COST_TIP_OVER, COST_STAND_UP, COST_ROLL_LYING,
        COST_CUBE_MOVE, COST_SWITCH_CUBE,
    )

    def __init__(self, level: Level | None = None) -> None:
        self._cell_penalty: dict[tuple[int, int], float] | None = None
        if level is not None:
            self._precompute_cell_penalty(level)

    def __call__(self, state: GameState, action: str, next_state: GameState, level: Level) -> float:
        return self.step_cost(state, action, next_state, level)

    def step_cost(self, state: GameState, action: str, next_state: GameState, level: Level) -> float:
        """Cost of one transition = move effort + risk of the destination cells. Always > 0."""
        if self._cell_penalty is None:
            raise RuntimeError("StepCost must be prepared with a level before use")

        cost = self._move_effort(state.block, action, next_state.block)

        for cell in next_state.occupied_cells():
            cost += self._cell_penalty.get(cell, 0.0)

        if next_state.bridge_mask != state.bridge_mask:
            cost += self.PENALTY_TOGGLE
        return cost

    def _move_effort(self, block: BlockState, action: str, next_block: BlockState) -> float:
        if action == "SPACE":
            return self.COST_SWITCH_CUBE
        if block.is_split:
            return self.COST_CUBE_MOVE
        before_standing = block.orientation == Orientation.STANDING
        after_standing = next_block.orientation == Orientation.STANDING and not next_block.is_split
        if before_standing:
            return self.COST_TIP_OVER
        if after_standing:
            return self.COST_STAND_UP
        return self.COST_ROLL_LYING

    def _precompute_cell_penalty(self, level: Level) -> None:
        """Cell risk depends only on the map, so compute it once per solve."""
        bridge_cells = {cell for cells in level.bridges.values() for cell in cells} if level.bridges else set()
        self._cell_penalty: dict[tuple[int, int], float] = {}
        for cell in set(level.tiles) | bridge_cells:
            penalty = 0.0
            if level.tiles.get(cell) == TileType.FRAGILE:
                penalty += self.PENALTY_FRAGILE
            if cell in bridge_cells:
                penalty += self.PENALTY_BRIDGE
            if self._next_to_void(cell, level, bridge_cells):
                penalty += self.PENALTY_EDGE
            if penalty:
                self._cell_penalty[cell] = penalty

    @staticmethod
    def _next_to_void(cell: tuple[int, int], level: Level, bridge_cells: set[tuple[int, int]]) -> bool:
        r, c = cell
        for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            tile = level.tiles.get(nb)
            if nb not in bridge_cells and (tile is None or tile == TileType.VOID):
                return True
        return False


def reconstruct_path(
    came_from: dict[GameState, tuple[GameState, str] | None],
    goal: GameState,
) -> list[str]:
    """Reconstructs the action sequence from the start state to ``goal``."""
    path: list[str] = []
    current = goal

    while came_from[current] is not None:
        edge = came_from[current]
        if edge is None:  # Kept for type checkers; the loop guards this case.
            break
        previous, action = edge
        path.append(action)
        current = previous

    path.reverse()
    return path


def make_result(
    path: list[str] | None,
    expanded_nodes: int,
    cost: float | None = None,
) -> SolverResult:
    """Creates the shared result object returned by every search algorithm."""
    if path is None:
        solution_length = -1
        total_cost = 0.0
    else:
        solution_length = len(path)
        total_cost = float(len(path)) if cost is None else float(cost)

    return SolverResult(
        path=path,
        expanded_nodes=expanded_nodes,
        search_time_ms=0.0,
        peak_memory_kb=0,
        solution_length=solution_length,
        cost=total_cost,
        success=path is not None,
    )


def normalize_start_state(
    level: Level,
    start: GameState | BlockState | tuple | list | None = None,
    *,
    position: tuple[int, int] | list[int] | None = None,
    orientation: Orientation | str | None = None,
    bridge_mask: int | None = None,
) -> GameState:
    """
    Normalizes any brick representation into an authoritative GameState.

    Accepts:
    - start is None (and position is None): defaults to level.start and level.initial_bridge_mask.
    - start is GameState: used directly, overriding bridge_mask if explicitly provided.
    - start is BlockState: wrapped with bridge_mask (defaulting to level.initial_bridge_mask).
    - start is (r, c): standing brick at (r, c).
    - start is (r, c, orientation): brick at (r, c) with given orientation.
    - start is (r, c, orientation, mask): full specification tuple.
    - start is ((r1, c1), (r2, c2)): two cell coordinates (lying block or split cubes).
    - position=(r, c) keyword: combined with orientation and bridge_mask.
    """
    default_mask = getattr(level, "initial_bridge_mask", 0)

    # 1. Explicit position keyword has top priority for coordinates
    if position is not None:
        r, c = int(position[0]), int(position[1])
        ori = Orientation(orientation) if orientation is not None else Orientation.STANDING
        mask = bridge_mask if bridge_mask is not None else default_mask
        return GameState(block=BlockState(r=r, c=c, orientation=ori), bridge_mask=mask)

    # 2. start is None -> default from level
    if start is None:
        mask = bridge_mask if bridge_mask is not None else default_mask
        return GameState(block=level.start, bridge_mask=mask)

    # 3. start is already GameState
    if isinstance(start, GameState):
        if bridge_mask is not None:
            return GameState(block=start.block, bridge_mask=bridge_mask)
        return start

    # 4. start is BlockState
    if isinstance(start, BlockState):
        mask = bridge_mask if bridge_mask is not None else default_mask
        return GameState(block=start, bridge_mask=mask)

    # 5. start is tuple or list
    if isinstance(start, (tuple, list)):
        mask = bridge_mask if bridge_mask is not None else default_mask

        # Subcase: ((r1, c1), (r2, c2))
        if len(start) == 2 and isinstance(start[0], (tuple, list)) and isinstance(start[1], (tuple, list)):
            p1 = (int(start[0][0]), int(start[0][1]))
            p2 = (int(start[1][0]), int(start[1][1]))
            dr = abs(p1[0] - p2[0])
            dc = abs(p1[1] - p2[1])
            if dr == 0 and dc == 1:
                min_c = min(p1[1], p2[1])
                block = BlockState(r=p1[0], c=min_c, orientation=Orientation.LYING_H)
            elif dr == 1 and dc == 0:
                min_r = min(p1[0], p2[0])
                block = BlockState(r=min_r, c=p1[1], orientation=Orientation.LYING_V)
            else:
                block = BlockState(
                    r=p1[0],
                    c=p1[1],
                    orientation=Orientation.STANDING,
                    is_split=True,
                    cube_positions=(p1, p2),
                    active_cube=0,
                )
            return GameState(block=block, bridge_mask=mask)

        # Subcase: (r, c)
        if len(start) == 2:
            r, c = int(start[0]), int(start[1])
            ori = Orientation(orientation) if orientation is not None else Orientation.STANDING
            return GameState(block=BlockState(r=r, c=c, orientation=ori), bridge_mask=mask)

        # Subcase: (r, c, orientation)
        if len(start) == 3:
            r, c = int(start[0]), int(start[1])
            ori = Orientation(start[2])
            return GameState(block=BlockState(r=r, c=c, orientation=ori), bridge_mask=mask)

        # Subcase: (r, c, orientation, mask)
        if len(start) == 4:
            r, c = int(start[0]), int(start[1])
            ori = Orientation(start[2])
            m = int(start[3]) if bridge_mask is None else bridge_mask
            return GameState(block=BlockState(r=r, c=c, orientation=ori), bridge_mask=m)

    raise TypeError(f"Cannot normalize start state from {type(start).__name__}: {start!r}")


class Solver(ABC):
    """Abstract Base Class for all search algorithms. Pygame is forbidden here."""

    @abstractmethod
    def solve(
        self,
        level: Level,
        start: GameState | BlockState | tuple | None = None,
        *,
        position: tuple[int, int] | None = None,
        orientation: Orientation | str | None = None,
        bridge_mask: int | None = None,
    ) -> SolverResult:
        ...

    def heuristic(self, state: GameState, level: Level) -> float:
        return 0.0


def run_solver(
    solver: Solver,
    level: Level,
    start: GameState | BlockState | tuple | None = None,
    *,
    position: tuple[int, int] | None = None,
    orientation: Orientation | str | None = None,
    bridge_mask: int | None = None,
) -> SolverResult:
    """Executes a solver while collecting memory and execution time metrics."""
    start_state = normalize_start_state(
        level, start, position=position, orientation=orientation, bridge_mask=bridge_mask
    )
    tracemalloc.start()
    t0 = time.perf_counter()
    result = solver.solve(level, start_state)
    dt = (time.perf_counter() - t0) * 1000.0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.search_time_ms = dt
    result.peak_memory_kb = peak // 1024
    return result


def is_valid_state(state: GameState, level: Level) -> bool:
    """
    Evaluates whether the given GameState has full floor/bridge support
    and does not violate fragile tile constraints or overlap split cubes.
    """
    if not getattr(level, "tiles", None) and not getattr(level, "bridges", None):
        return True

    if state.block.is_split and state.block.cube_positions:
        pos0, pos1 = state.block.cube_positions
        if pos0 == pos1:
            return False

    bridge_index = getattr(level, "_bridge_index", None)
    if bridge_index is None:
        if not level.bridges:
            bridge_index = {}
        else:
            bridge_index = {b_id: i for i, b_id in enumerate(level.bridges.keys())}

    for cell in state.block.occupied_cells():
        tile = level.tiles.get(cell) if level.tiles else None

        in_bridge = False
        bridge_open = False
        if level.bridges:
            for b_id, b_tiles in level.bridges.items():
                if cell in b_tiles:
                    in_bridge = True
                    idx = bridge_index.get(b_id)
                    if idx is not None and (state.bridge_mask & (1 << idx)) != 0:
                        bridge_open = True
                    break

        if in_bridge:
            if not bridge_open:
                return False
        else:
            if tile is None or tile == TileType.VOID or tile == TileType.BRIDGE:
                return False

        if tile == TileType.FRAGILE:
            if state.block.is_split or state.block.orientation == Orientation.STANDING:
                return False

    return True

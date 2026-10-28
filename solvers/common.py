"""
Shared solver interfaces and execution metrics harness.
docs/parallel-engineering-plan.en.md §2.4 & §3.4
"""
from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod

from core.interfaces import GameState, Level, SolverResult


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


class Solver(ABC):
    """Abstract Base Class for all search algorithms. Pygame is forbidden here."""

    @abstractmethod
    def solve(self, level: Level, start: GameState) -> SolverResult:
        ...

    def heuristic(self, state: GameState, level: Level) -> float:
        return 0.0


def run_solver(solver: Solver, level: Level, start: GameState) -> SolverResult:
    """Executes a solver while collecting memory and execution time metrics."""
    tracemalloc.start()
    t0 = time.perf_counter()
    result = solver.solve(level, start)
    dt = (time.perf_counter() - t0) * 1000.0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.search_time_ms = dt
    result.peak_memory_kb = peak // 1024
    return result
class StepCost:
    """Shared UCS cost policy, copied without changing its formula.

    Prepare map penalties once per solve with StepCost(level). The optional
    constructor also preserves UCSSolver() and its existing prepare/method API
    when UCS inherits this policy. A policy instance belongs to one map at a
    time; do not share a prepared instance across concurrent solves.
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
        if level is not None:
            self._precompute_cell_penalty(level)

    def __call__(self, state: GameState, action: str, next_state: GameState, level: Level) -> float:
        return self.step_cost(state, action, next_state, level)

    def step_cost(self, state: GameState, action: str, next_state: GameState, level: Level) -> float:
        """Cost of one transition = move effort + risk of the destination cells. Always > 0."""
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
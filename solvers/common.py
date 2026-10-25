"""
Shared solver interfaces and execution metrics harness.
docs/parallel-engineering-plan.en.md §2.4 & §3.4
"""
from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod
from typing import Any, Iterable

from core.block import Direction
from core.game_state import GameState
from core.interfaces import SolverResult


class Solver(ABC):
    """Abstract Base Class for all search algorithms. Pygame is forbidden here."""

    @abstractmethod
    def solve(self, level: Any, start: GameState) -> SolverResult:
        ...

    def heuristic(self, state: GameState, level: Any) -> float:
        return 0.0


def successors(state: GameState) -> Iterable[tuple[str, GameState]]:
    """Generate transitions exclusively through the authoritative core API."""
    for direction in Direction.values():
        next_state = state.move(direction)
        if next_state is not None:
            yield direction.value[0].upper(), next_state
    if state.is_split:
        yield "SPACE", state.switch_control()


def make_result(path: list[str] | None, expanded_nodes: int) -> SolverResult:
    return SolverResult(
        path=path,
        expanded_nodes=expanded_nodes,
        search_time_ms=0.0,
        peak_memory_kb=0,
        solution_length=len(path) if path is not None else -1,
        cost=float(len(path)) if path is not None else float("inf"),
        success=path is not None,
    )


def run_solver(solver: Solver, level: Any, start: GameState) -> SolverResult:
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

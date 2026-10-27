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

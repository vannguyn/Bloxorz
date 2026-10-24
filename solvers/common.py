"""
Shared solver interfaces and execution metrics harness.
docs/parallel-engineering-plan.en.md §2.4 & §3.4
"""
from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod

from core.interfaces import GameState, Level, SolverResult


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

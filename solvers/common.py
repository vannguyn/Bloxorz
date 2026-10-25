"""
Shared solver interfaces and execution metrics harness.
docs/parallel-engineering-plan.en.md §2.4 & §3.4
"""
from __future__ import annotations

import time
import tracemalloc
from abc import ABC, abstractmethod

from core.interfaces import GameState, Level, SolverResult
from core.legacy_adapter import apply_move, is_goal, state_key


class Solver(ABC):
    """Abstract Base Class for all search algorithms. Pygame is forbidden here."""

    ACTIONS = ("U", "D", "L", "R", "SPACE")

    @abstractmethod
    def solve(self, level: Level, start: GameState) -> SolverResult:
        ...

    def heuristic(self, state: GameState, level: Level) -> float:
        return 0.0

    def successors(self, state: GameState, level: Level):
        """Yield legal (action, state) pairs for every search algorithm."""
        for action in self.ACTIONS:
            next_state = apply_move(state, action, level)
            if next_state is not None:
                yield action, next_state

    @staticmethod
    def state_key(state: GameState) -> tuple:
        return state_key(state)

    @staticmethod
    def is_goal(state: GameState, level: Level) -> bool:
        return is_goal(state, level)

    @staticmethod
    def make_result(path: list[str] | None, expanded: int) -> SolverResult:
        return SolverResult(
            path=path,
            expanded_nodes=expanded,
            search_time_ms=0.0,
            peak_memory_kb=0,
            solution_length=len(path) if path is not None else -1,
            cost=float(len(path)) if path is not None else float("inf"),
            success=path is not None,
        )


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

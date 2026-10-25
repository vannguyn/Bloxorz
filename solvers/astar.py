"""A* solver extension point; algorithm code is intentionally not included."""
from __future__ import annotations

from core.interfaces import GameState, Level, SolverResult
from .common import Solver


class AStarSolver(Solver):
    """Placeholder for an A* implementation to be merged later."""

    def solve(self, level: Level, start: GameState) -> SolverResult:
        raise NotImplementedError("A* implementation is not merged yet")

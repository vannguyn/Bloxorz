"""BFS solver extension point; algorithm code is intentionally not included."""
from __future__ import annotations

from core.interfaces import GameState, Level, SolverResult
from .common import Solver


class BFSSolver(Solver):
    """Placeholder for a BFS implementation to be merged later."""

    def solve(self, level: Level, start: GameState) -> SolverResult:
        raise NotImplementedError("BFS implementation is not merged yet")

"""UCS solver extension point; algorithm code is intentionally not included."""
from __future__ import annotations

from core.interfaces import GameState, Level, SolverResult
from .common import Solver


class UCSSolver(Solver):
    """Placeholder for a UCS implementation to be merged later."""

    def solve(self, level: Level, start: GameState) -> SolverResult:
        raise NotImplementedError("UCS implementation is not merged yet")

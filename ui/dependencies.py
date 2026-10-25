"""Runtime integration boundary between Pygame and the real core modules."""
from __future__ import annotations

from core.interfaces import Level
from core.legacy_adapter import apply_move, initial_state, is_goal, would_break_fragile
from levels.level_loader import load_all_levels
from solvers.common import Solver, run_solver
from solvers.BFS import BFSSolver
from solvers.DFS import DFSSolver
from solvers.UCS import UCSSolver
from solvers.astar import AStarSolver

IS_MOCK_CORE: bool = False
IS_MOCK_SOLVERS: bool = False

IS_MOCK_MODE: bool = IS_MOCK_CORE or IS_MOCK_SOLVERS


def get_levels() -> list[Level]:
    """Load every JSON stage in deterministic order."""
    return load_all_levels()


def get_solver(algo: str) -> Solver:
    name = algo.strip().upper()
    if name == "BFS":
        return BFSSolver()
    if name == "DFS":
        return DFSSolver()
    if name == "UCS":
        return UCSSolver()
    if name in ("ASTAR", "A*"):
        return AStarSolver()
    raise ValueError(f"Unknown solver algorithm: {algo}")


def get_mode_badge_text() -> str:
    """Returns a badge indicating that the GUI uses the real core rules."""
    if not IS_MOCK_CORE and not IS_MOCK_SOLVERS:
        return "[REAL]"
    if IS_MOCK_CORE and IS_MOCK_SOLVERS:
        return "[MOCK CORE+SOLVERS]"
    if IS_MOCK_CORE:
        return "[MOCK CORE]"
    return "[MOCK SOLVERS]"


__all__ = [
    "IS_MOCK_CORE",
    "IS_MOCK_SOLVERS",
    "IS_MOCK_MODE",
    "apply_move",
    "initial_state",
    "is_goal",
    "would_break_fragile",
    "get_levels",
    "get_solver",
    "run_solver",
    "get_mode_badge_text",
]

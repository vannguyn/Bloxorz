"""Production adapters used by the Pygame layer.

The UI calls this module so it never reimplements a transition rule. Every
move, switch action, goal check, level and solver now comes from the real core
and level files.
"""

from __future__ import annotations

from core.block import Direction
from core.game_state import GameState
from levels.level_loader import Level, load_levels
from solvers.common import Solver, run_solver
from solvers.BFS import BFSSolver
from solvers.DFS import DFSSolver
from solvers.UCS import UCSSolver
from solvers.astar import AStarSolver


IS_MOCK_CORE = False
IS_MOCK_SOLVERS = False
IS_MOCK_MODE = False


def get_levels() -> list[Level]:
    return load_levels()


def get_solver(algo: str) -> Solver:
    name = algo.strip().upper()
    if name == "BFS":
        return BFSSolver()
    if name == "DFS":
        return DFSSolver()
    if name == "UCS":
        return UCSSolver()
    if name in {"ASTAR", "A*"}:
        return AStarSolver()
    raise ValueError(f"Unknown solver algorithm: {algo}")


def apply_move(state: GameState, action: str, level: Level | None = None) -> GameState | None:
    """Apply a keyboard/replay action through ``core.GameState``."""
    if action == "SPACE":
        return state.switch_control()
    return state.move(Direction.coerce(action))


def is_goal(state: GameState, level: Level | None = None) -> bool:
    return state.is_won()


def get_mode_badge_text() -> str:
    return "[REAL]"


__all__ = [
    "IS_MOCK_CORE",
    "IS_MOCK_SOLVERS",
    "IS_MOCK_MODE",
    "apply_move",
    "is_goal",
    "get_solver",
    "get_levels",
    "run_solver",
    "get_mode_badge_text",
]

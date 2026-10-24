"""
Centralized Integration Adapter.
Decouples UI and animation layers from mock vs real implementations of
Core transition rules and Solvers.
"""
from __future__ import annotations

from core.interfaces import GameState, Level, SolverResult
from solvers.common import Solver, run_solver

# --- Core Transition & Levels (Toggle to real core when M1 lands) ---
from tests.mocks import (
    apply_move,
    is_goal,
    mock_level_simple,
    mock_level_with_fragile,
    mock_level_with_bridge,
    mock_level_split,
)
IS_MOCK_CORE: bool = True

# --- Search Solvers & Harness (Toggle to real solvers when M3-M5 land) ---
from tests.mocks import (
    MockBFSSolver,
    MockDFSSolver,
    MockUCSSolver,
    MockAStarSolver,
)
IS_MOCK_SOLVERS: bool = True

IS_MOCK_MODE: bool = IS_MOCK_CORE or IS_MOCK_SOLVERS


def get_levels() -> list[Level]:
    """Returns the list of playable levels."""
    return [
        mock_level_simple(),
        mock_level_with_fragile(),
        mock_level_with_bridge(),
        mock_level_split(),
    ]


def get_solver(algo: str) -> Solver:
    """Returns an instantiated solver instance for the given algorithm name."""
    name = algo.strip().upper()
    if name == "BFS":
        return MockBFSSolver()
    elif name == "DFS":
        return MockDFSSolver()
    elif name == "UCS":
        return MockUCSSolver()
    elif name in ("ASTAR", "A*"):
        return MockAStarSolver()
    raise ValueError(f"Unknown solver algorithm: {algo}")


def get_mode_badge_text() -> str:
    """Returns badge text indicating whether real or mock modules are active."""
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
    "is_goal",
    "get_levels",
    "get_solver",
    "run_solver",
    "get_mode_badge_text",
]

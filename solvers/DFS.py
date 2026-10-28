"""
Depth-First Search solver for Bloxorz (iterative, no recursion).

- LIFO stack + visited set to avoid cycles (state includes bridge bitmask
  and split/active-cube info, so revisiting is judged on the full state).
- A state is marked visited when it is POPPED, and its parent edge is
  recorded at that moment, so the returned path is the real DFS tree path.
- DFS does NOT guarantee the shortest solution; the path can be long.
- Successors are pushed in reverse so the first action in the
  get_successors order is explored first (deterministic behaviour).
- expanded_nodes = number of states popped and actually expanded
  (duplicates skipped are not counted).
"""
from __future__ import annotations

from core.game_rules import get_successors, is_goal
from core.interfaces import GameState, Level, SolverResult
from solvers.common import Solver, make_result, reconstruct_path


class DFSSolver(Solver):
    def solve(self, level: Level, start: GameState) -> SolverResult:
        came_from: dict[GameState, tuple[GameState, str] | None] = {}
        # Stack entries: (state, parent_state_or_None, action_or_None)
        stack: list[tuple[GameState, GameState | None, str | None]] = [
            (start, None, None)
        ]
        expanded = 0

        while stack:
            state, parent, action = stack.pop()
            if state in came_from:
                continue
            came_from[state] = None if parent is None else (parent, action)  # type: ignore[assignment]

            if is_goal(state, level):
                return make_result(reconstruct_path(came_from, state), expanded)

            expanded += 1
            for act, nxt in reversed(get_successors(state, level)):
                if nxt not in came_from:
                    stack.append((nxt, state, act))

        return make_result(None, expanded)

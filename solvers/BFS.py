"""
Breadth-First Search solver for Bloxorz.

- FIFO queue + visited set (state = block placement/orientation/split info
  + bridge bitmask, all contained in GameState).
- Every action costs 1, so BFS returns a shortest solution (fewest moves,
  where SPACE in split mode also counts as one action).
- expanded_nodes = number of states popped from the queue and expanded.
- The goal test is applied when a successor is generated (saves memory/time
  and keeps optimality because all step costs are equal).
"""
from __future__ import annotations

from collections import deque

from core.game_rules import get_successors, is_goal
from core.interfaces import GameState, Level, SolverResult
from solvers.common import Solver, make_result, reconstruct_path


class BFSSolver(Solver):
    def solve(self, level: Level, start: GameState) -> SolverResult:
        if is_goal(start, level):
            return make_result([], 0)

        came_from: dict[GameState, tuple[GameState, str] | None] = {start: None}
        queue: deque[GameState] = deque([start])
        expanded = 0

        while queue:
            state = queue.popleft()
            expanded += 1

            for action, nxt in get_successors(state, level):
                if nxt in came_from:
                    continue
                came_from[nxt] = (state, action)
                if is_goal(nxt, level):
                    return make_result(reconstruct_path(came_from, nxt), expanded)
                queue.append(nxt)

        # Queue exhausted: the level has no solution.
        return make_result(None, expanded)

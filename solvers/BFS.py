"""
Breadth-First Search solver for Bloxorz.

- FIFO queue + visited set (state = block placement/orientation/split info
  + bridge bitmask, all contained in GameState).
- Supports any initial brick placement/standing position via `start` or `position`.
- Every action costs 1, so BFS returns a shortest solution (fewest moves,
  where SPACE in split mode also counts as one action).
- expanded_nodes = number of states popped from the queue and expanded.
- The goal test is applied when a successor is generated (saves memory/time
  and keeps optimality because all step costs are equal).
"""
from __future__ import annotations

from collections import deque

from core.game_rules import get_successors, is_goal
from core.interfaces import BlockState, GameState, Level, Orientation, SolverResult
from solvers.common import Solver, is_valid_state, make_result, normalize_start_state, reconstruct_path


class BFSSolver(Solver):
    def solve(
        self,
        level: Level,
        start: GameState | BlockState | tuple | None = None,
        *,
        position: tuple[int, int] | None = None,
        orientation: Orientation | str | None = None,
        bridge_mask: int | None = None,
    ) -> SolverResult:
        start_state = normalize_start_state(
            level, start, position=position, orientation=orientation, bridge_mask=bridge_mask
        )
        if not is_valid_state(start_state, level):
            return make_result(None, 0)
        if is_goal(start_state, level):
            return make_result([], 0)

        came_from: dict[GameState, tuple[GameState, str] | None] = {start_state: None}
        queue: deque[GameState] = deque([start_state])
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

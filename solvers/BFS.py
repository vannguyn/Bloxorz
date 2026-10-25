"""Breadth-first search over the real core.GameState graph."""

from __future__ import annotations

from collections import deque
from typing import Any

from core.game_state import GameState
from .common import Solver, make_result, successors


class BFSSolver(Solver):
    def solve(self, level: Any, start: GameState):
        queue = deque([(start, [])])
        visited = {start.key()}
        expanded = 0
        while queue:
            state, path = queue.popleft()
            expanded += 1
            if state.is_won():
                return make_result(path, expanded)
            for action, next_state in successors(state):
                key = next_state.key()
                if key not in visited:
                    visited.add(key)
                    queue.append((next_state, path + [action]))
        return make_result(None, expanded)


__all__ = ["BFSSolver"]

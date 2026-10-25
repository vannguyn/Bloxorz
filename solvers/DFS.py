"""Depth-first search over the real core.GameState graph."""

from __future__ import annotations

from typing import Any

from core.game_state import GameState
from .common import Solver, make_result, successors


class DFSSolver(Solver):
    def solve(self, level: Any, start: GameState):
        stack = [(start, [])]
        visited = {start.key()}
        expanded = 0
        while stack:
            state, path = stack.pop()
            expanded += 1
            if state.is_won():
                return make_result(path, expanded)
            next_items = list(successors(state))
            for action, next_state in reversed(next_items):
                key = next_state.key()
                if key not in visited:
                    visited.add(key)
                    stack.append((next_state, path + [action]))
        return make_result(None, expanded)


__all__ = ["DFSSolver"]

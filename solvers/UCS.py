"""Uniform-cost search over the real core.GameState graph."""

from __future__ import annotations

import heapq
from itertools import count
from typing import Any

from core.game_state import GameState
from .common import Solver, make_result, successors


class UCSSolver(Solver):
    def solve(self, level: Any, start: GameState):
        sequence = count()
        heap = [(0.0, next(sequence), start, [])]
        best_cost = {start.key(): 0.0}
        expanded = 0
        while heap:
            cost, _, state, path = heapq.heappop(heap)
            if cost != best_cost.get(state.key()):
                continue
            expanded += 1
            if state.is_won():
                return make_result(path, expanded)
            for action, next_state in successors(state):
                next_cost = cost + 1.0
                key = next_state.key()
                if next_cost < best_cost.get(key, float("inf")):
                    best_cost[key] = next_cost
                    heapq.heappush(heap, (next_cost, next(sequence), next_state, path + [action]))
        return make_result(None, expanded)


__all__ = ["UCSSolver"]

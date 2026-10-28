"""
Uniform-Cost Search solver for Bloxorz.
Always expands the frontier state with the lowest accumulated path cost g(n).
"""
from __future__ import annotations

import heapq
import itertools

from core.game_rules import get_successors, is_goal
from core.interfaces import GameState, Level, SolverResult
from solvers.common import Solver, StepCost, reconstruct_path


class UCSSolver(StepCost, Solver):
    """Uniform-Cost Search using a priority queue ordered by g(n).

    Edge costs come from the shared StepCost policy in solvers/common.py.
    """

    def solve(self, level: Level, start: GameState) -> SolverResult:
        self._precompute_cell_penalty(level)
        counter = itertools.count()  # tie-breaker so GameState is never compared
        frontier: list[tuple[float, int, GameState]] = [(0.0, next(counter), start)]
        best_cost: dict[GameState, float] = {start: 0.0}
        came_from: dict[GameState, tuple[GameState, str] | None] = {start: None}
        expanded: set[GameState] = set()
        expanded_nodes = 0

        while frontier:
            g, _, state = heapq.heappop(frontier)
            if state in expanded or g > best_cost[state]:
                continue  # stale queue entry
            expanded.add(state)
            expanded_nodes += 1

            if is_goal(state, level):
                path = reconstruct_path(came_from, state)
                return SolverResult(
                    path=path,
                    expanded_nodes=expanded_nodes,
                    search_time_ms=0.0,
                    peak_memory_kb=0,
                    solution_length=len(path),
                    cost=g,
                    success=True,
                )

            for action, next_state in get_successors(state, level):
                if next_state in expanded:
                    continue
                new_g = g + self.step_cost(state, action, next_state, level)
                if new_g < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = new_g
                    came_from[next_state] = (state, action)
                    heapq.heappush(frontier, (new_g, next(counter), next_state))

        return SolverResult(
            path=None,
            expanded_nodes=expanded_nodes,
            search_time_ms=0.0,
            peak_memory_kb=0,
            solution_length=-1,
            cost=float("inf"),
            success=False,
        )


if __name__ == "__main__":
    # Usage: python3 -m solvers.UCS            -> run every level
    #        python3 -m solvers.UCS 1 8        -> run level_01 and level_08 only
    import sys

    from levels.level_loader import load_all_levels
    from solvers.common import run_solver

    levels = load_all_levels()
    if len(sys.argv) > 1:
        levels = [levels[int(n) - 1] for n in sys.argv[1:]]

    for level in levels:
        result = run_solver(UCSSolver(), level, GameState(level.start, level.initial_bridge_mask))
        print(
            f"{level.id}: success={result.success} steps={result.solution_length} "
            f"cost={result.cost:.1f} nodes={result.expanded_nodes} "
            f"time={result.search_time_ms:.1f}ms mem={result.peak_memory_kb}KB"
        )
        print("   path:", " ".join(result.path or []))

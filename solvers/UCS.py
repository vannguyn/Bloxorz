"""
Uniform-Cost Search solver for Bloxorz.
Always expands the frontier state with the lowest accumulated path cost g(n).
"""
from __future__ import annotations

import heapq
import itertools

from core.game_rules import get_successors, is_goal
from core.interfaces import BlockState, GameState, Level, Orientation, SolverResult, TileType
from solvers.common import Solver, make_result, reconstruct_path


class UCSSolver(Solver):
    """Uniform-Cost Search using a priority queue ordered by g(n)."""

    # Effort of the move itself
    COST_TIP_OVER = 1.0       # STANDING -> LYING
    COST_STAND_UP = 1.5       # LYING -> STANDING (lifting the block is harder)
    COST_ROLL_LYING = 1.2     # LYING -> LYING (rolling the long side)
    COST_CUBE_MOVE = 0.8      # moving a single split cube (half the weight)
    COST_SWITCH_CUBE = 0.3    # SPACE: change the controlled cube
    # Risk / extra penalties on the destination
    PENALTY_FRAGILE = 0.5     # per occupied fragile cell
    PENALTY_BRIDGE = 0.3      # per occupied bridge cell
    PENALTY_EDGE = 0.1        # per occupied cell next to void
    PENALTY_TOGGLE = 0.5      # pressing a switch that changes the bridges

    def step_cost(self, state: GameState, action: str, next_state: GameState, level: Level) -> float:
        """Cost of one transition = move effort + risk of the destination cells. Always > 0."""
        cost = self._move_effort(state.block, action, next_state.block)

        for cell in next_state.occupied_cells():
            cost += self._cell_penalty.get(cell, 0.0)

        if next_state.bridge_mask != state.bridge_mask:
            cost += self.PENALTY_TOGGLE
        return cost

    def _move_effort(self, block: BlockState, action: str, next_block: BlockState) -> float:
        if action == "SPACE":
            return self.COST_SWITCH_CUBE
        if block.is_split:
            return self.COST_CUBE_MOVE
        before_standing = block.orientation == Orientation.STANDING
        after_standing = next_block.orientation == Orientation.STANDING and not next_block.is_split
        if before_standing:
            return self.COST_TIP_OVER
        if after_standing:
            return self.COST_STAND_UP
        return self.COST_ROLL_LYING

    def _precompute_cell_penalty(self, level: Level) -> None:
        """Cell risk depends only on the map, so compute it once per solve."""
        bridge_cells = {cell for cells in level.bridges.values() for cell in cells} if level.bridges else set()
        self._cell_penalty: dict[tuple[int, int], float] = {}
        for cell in set(level.tiles) | bridge_cells:
            penalty = 0.0
            if level.tiles.get(cell) == TileType.FRAGILE:
                penalty += self.PENALTY_FRAGILE
            if cell in bridge_cells:
                penalty += self.PENALTY_BRIDGE
            if self._next_to_void(cell, level, bridge_cells):
                penalty += self.PENALTY_EDGE
            if penalty:
                self._cell_penalty[cell] = penalty

    @staticmethod
    def _next_to_void(cell: tuple[int, int], level: Level, bridge_cells: set[tuple[int, int]]) -> bool:
        r, c = cell
        for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            tile = level.tiles.get(nb)
            if nb not in bridge_cells and (tile is None or tile == TileType.VOID):
                return True
        return False

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
                return make_result(reconstruct_path(came_from, state), expanded_nodes, cost=g)

            for action, next_state in get_successors(state, level):
                if next_state in expanded:
                    continue
                new_g = g + self.step_cost(state, action, next_state, level)
                if new_g < best_cost.get(next_state, float("inf")):
                    best_cost[next_state] = new_g
                    came_from[next_state] = (state, action)
                    heapq.heappush(frontier, (new_g, next(counter), next_state))

        return make_result(None, expanded_nodes)


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

"""
Collects UCS experiment data for the report (typst/sections/UCS.typ).

For every level the script runs:
  - UCS with the shared StepCost policy (the submitted solver);
  - UCS with unit cost 1 per move (baseline, same search order as BFS).
Each configuration gets one warm-up run, then REPEATS measured runs through
run_solver(); the CSV stores the median time and memory. Every solution is
replayed with apply_move to check legality, the goal and the reported cost.

Usage (from the repository root):
    python3 typst/collect_ucs_results.py
"""
from __future__ import annotations

import csv
import gc
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.game_rules import apply_move, is_goal
from core.interfaces import GameState, Level
from levels.level_loader import load_all_levels
from solvers.common import run_solver
from solvers.UCS import UCSSolver

REPEATS = 5
OUT_PATH = Path(__file__).resolve().parent / "data" / "ucs_results.csv"


class UnitCostUCS(UCSSolver):
    """Baseline: every move costs 1, so UCS orders states like BFS."""

    def step_cost(self, state, action, next_state, level) -> float:
        return 1.0


def replay(solver: UCSSolver, level: Level, start: GameState, path: list[str]) -> float:
    """Replays path with the game rules and returns the recomputed cost."""
    solver._precompute_cell_penalty(level)
    state, total = start, 0.0
    for action in path:
        nxt = apply_move(state, action, level)
        if nxt is None:
            raise AssertionError(f"{level.id}: illegal action {action!r} in solution")
        total += solver.step_cost(state, action, nxt, level)
        state = nxt
    if not is_goal(state, level):
        raise AssertionError(f"{level.id}: solution does not reach the goal")
    return total


def measure(solver_cls: type[UCSSolver], level: Level, start: GameState) -> dict:
    run_solver(solver_cls(), level, start)  # warm-up, not recorded
    runs = []
    for _ in range(REPEATS):
        gc.collect()
        runs.append(run_solver(solver_cls(), level, start))
    first = runs[0]
    for r in runs[1:]:
        if r.path != first.path or r.expanded_nodes != first.expanded_nodes:
            raise AssertionError(f"{level.id}: non-deterministic result")
    if first.success:
        cost = replay(solver_cls(), level, start, first.path)
        if abs(cost - first.cost) > 1e-9:
            raise AssertionError(f"{level.id}: replayed cost {cost} != reported {first.cost}")
    return {
        "success": first.success,
        "steps": first.solution_length,
        "cost": first.cost,
        "nodes": first.expanded_nodes,
        "time_ms": statistics.median(r.search_time_ms for r in runs),
        "memory_kb": statistics.median(r.peak_memory_kb for r in runs),
        "path": " ".join(first.path or []),
    }


def main() -> None:
    rows = []
    for level in load_all_levels():
        start = GameState(level.start, level.initial_bridge_mask)
        ucs = measure(UCSSolver, level, start)
        unit = measure(UnitCostUCS, level, start)
        rows.append({
            "level": level.id,
            "success": ucs["success"],
            "steps": ucs["steps"],
            "cost": round(ucs["cost"], 4),
            "nodes": ucs["nodes"],
            "time_ms": round(ucs["time_ms"], 2),
            "memory_kb": ucs["memory_kb"],
            "unit_steps": unit["steps"],
            "unit_cost_stepcost": round(replay(UCSSolver(), level, start, unit["path"].split()), 4)
            if unit["success"] else "",
            "unit_nodes": unit["nodes"],
            "unit_time_ms": round(unit["time_ms"], 2),
            "path": ucs["path"],
        })
        print(f"{level.id}: steps={ucs['steps']} cost={ucs['cost']:.2f} nodes={ucs['nodes']} "
              f"| unit steps={unit['steps']} nodes={unit['nodes']}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] wrote {OUT_PATH.relative_to(PROJECT_ROOT)} ({REPEATS} measured runs per configuration)")


if __name__ == "__main__":
    main()

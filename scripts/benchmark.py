"""
Standalone Benchmark Script for Bloxorz Solvers.
Runs BFS, DFS, UCS, and A* sequentially to collect clean experimental metrics
without any GUI, Pygame, or GIL interference.
Generates tabular console output and exports CSV for the report experiments (§3.6).
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.interfaces import GameState, Level
from levels.level_loader import load_all_levels
from solvers.common import Solver, run_solver

from solvers.BFS import BFSSolver
from solvers.DFS import DFSSolver
from solvers.UCS import UCSSolver
from solvers.astar import AStarSolver
from tests.mocks import (
    mock_level_simple,
    mock_level_with_fragile,
    mock_level_with_bridge,
    mock_level_split,
)


def get_benchmark_solvers() -> dict[str, Solver]:
    return {
        "BFS": BFSSolver(),
        "DFS": DFSSolver(),
        "UCS": UCSSolver(),
        "A*": AStarSolver(),
    }


def get_benchmark_levels() -> list[Level]:
    try:
        levels = load_all_levels()
        if levels:
            return levels
    except Exception as exc:
        print(f"[WARN] Failed to load real levels ({exc}), falling back to mock levels.")
    return [
        mock_level_simple(),
        mock_level_with_fragile(),
        mock_level_with_bridge(),
        mock_level_split(),
    ]


def run_benchmarks(export_csv_path: Path | None = None) -> list[dict]:
    solvers = get_benchmark_solvers()
    levels = get_benchmark_levels()
    results = []

    print("=" * 84)
    print(f"{'Level':<24} | {'Algo':<6} | {'Time (ms)':<10} | {'Mem (KB)':<9} | {'Nodes':<7} | {'Len':<5} | {'Cost':<5}")
    print("-" * 84)

    for level in levels:
        init_mask = getattr(level, "initial_bridge_mask", 0)
        start_state = GameState(block=level.start, bridge_mask=init_mask)
        for name, solver in solvers.items():
            res = run_solver(solver, level, start_state)
            row = {
                "level_id": level.id,
                "level_name": level.name,
                "algorithm": name,
                "success": res.success,
                "time_ms": round(res.search_time_ms, 3),
                "memory_kb": res.peak_memory_kb,
                "expanded_nodes": res.expanded_nodes,
                "solution_length": res.solution_length,
                "cost": res.cost,
            }
            results.append(row)
            print(
                f"{level.name[:24]:<24} | {name:<6} | {res.search_time_ms:10.3f} | "
                f"{res.peak_memory_kb:9d} | {res.expanded_nodes:7d} | {res.solution_length:5d} | {res.cost:5.1f}"
            )
    print("=" * 84)

    if export_csv_path:
        export_csv_path.parent.mkdir(parents=True, exist_ok=True)
        keys = ["level_id", "level_name", "algorithm", "success", "time_ms", "memory_kb", "expanded_nodes", "solution_length", "cost"]
        with open(export_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
            writer.writeheader()
            writer.writerows(results)
        print(f"\n[OK] Benchmark results exported to: {export_csv_path}")

    return results


if __name__ == "__main__":
    csv_out = PROJECT_ROOT / "experiments" / "results.csv"
    run_benchmarks(export_csv_path=csv_out)

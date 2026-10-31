"""Collect a common, validated benchmark for BFS, DFS, UCS, and A*.

Run from any directory with:
    python typst/collect_all_results.py [--repeats 3]
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.game_rules import apply_move, get_successors, is_goal
from core.interfaces import GameState, Level, SolverResult, TileType
from levels.level_loader import load_all_levels
from solvers.BFS import BFSSolver
from solvers.DFS import DFSSolver
from solvers.UCS import UCSSolver
from solvers.astar import AStarSolver, _relaxed_landmarks
from solvers.common import Solver, StepCost

SolverFactory = Callable[[], Solver]
SOLVERS: dict[str, SolverFactory] = {
    "BFS": BFSSolver,
    "DFS": DFSSolver,
    "UCS": UCSSolver,
    "A*": AStarSolver,
}


def level_group(level: Level) -> str:
    has_fragile = TileType.FRAGILE in level.tiles.values()
    has_switches = bool(level.switches)
    if has_fragile and has_switches:
        return "Kết hợp"
    if has_fragile:
        return "Ô dễ vỡ"
    if has_switches:
        return "Công tắc/cầu"
    return "Cơ bản"


def solver_signature(result: SolverResult) -> tuple:
    return result.success, result.solution_length, result.expanded_nodes, result.cost, result.path


def timed_solve(factory: SolverFactory, level: Level, start: GameState) -> SolverResult:
    solver = factory()
    started = time.perf_counter()
    result = solver.solve(level, start)
    result.search_time_ms = (time.perf_counter() - started) * 1000.0
    return result


def memory_solve(factory: SolverFactory, level: Level, start: GameState) -> SolverResult:
    if tracemalloc.is_tracing():
        raise RuntimeError("Memory measurement requires tracemalloc to be stopped")
    gc.collect()
    tracemalloc.start()
    try:
        result = factory().solve(level, start)
        _, peak = tracemalloc.get_traced_memory()
        result.peak_memory_kb = peak // 1024
        return result
    finally:
        tracemalloc.stop()


def validate_result(level: Level, start: GameState, algorithm: str, result: SolverResult) -> None:
    if result.success != (result.path is not None):
        raise RuntimeError(f"{level.id}/{algorithm}: success and path disagree")
    if not result.success:
        raise RuntimeError(f"{level.id}/{algorithm}: expected a solution for this test level")
    if result.path is None or result.solution_length != len(result.path):
        raise RuntimeError(f"{level.id}/{algorithm}: solution length does not match path")

    state = start
    step_cost = StepCost(level)
    total_cost = 0.0
    for action in result.path:
        next_state = apply_move(state, action, level)
        if next_state is None:
            raise RuntimeError(f"{level.id}/{algorithm}: illegal replay action {action!r}")
        if algorithm in ("UCS", "A*"):
            total_cost += step_cost(state, action, next_state, level)
        state = next_state

    if not is_goal(state, level):
        raise RuntimeError(f"{level.id}/{algorithm}: replay did not reach the goal")
    if algorithm in ("UCS", "A*") and abs(total_cost - result.cost) > 1e-9:
        raise RuntimeError(
            f"{level.id}/{algorithm}: replay cost {total_cost} != reported {result.cost}"
        )


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"Refusing to write an empty result file: {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def collect(repeats: int) -> None:
    if repeats < 1:
        raise ValueError("--repeats must be at least 1")
    if tracemalloc.is_tracing():
        raise RuntimeError("Run the collector in a process without active tracemalloc")

    levels = load_all_levels(ROOT / "levels")
    if not levels:
        raise RuntimeError("No levels found in the levels directory")

    details: list[dict] = []
    raw_runs: list[dict] = []
    for level in levels:
        start = GameState(level.start, level.initial_bridge_mask)
        get_successors(start, level)
        samples: dict[str, list[SolverResult]] = {name: [] for name in SOLVERS}
        expected: dict[str, tuple] = {}

        for algorithm, factory in SOLVERS.items():
            if algorithm == "A*":
                _relaxed_landmarks.cache_clear()
            result = factory().solve(level, start)
            validate_result(level, start, algorithm, result)
            expected[algorithm] = solver_signature(result)

        if abs(expected["UCS"][3] - expected["A*"][3]) > 1e-9:
            raise RuntimeError(f"{level.id}: UCS and A* returned different optimal costs")

        for algorithm, factory in SOLVERS.items():
            if algorithm == "A*":
                _relaxed_landmarks.cache_clear()
            warmup = factory().solve(level, start)
            validate_result(level, start, algorithm, warmup)
            if solver_signature(warmup) != expected[algorithm]:
                raise RuntimeError(f"{level.id}/{algorithm}: warm-up result is inconsistent")

        for repetition in range(1, repeats + 1):
            names = list(SOLVERS)
            offset = (repetition - 1) % len(names)
            names = names[offset:] + names[:offset]
            for order, algorithm in enumerate(names, 1):
                if algorithm == "A*":
                    _relaxed_landmarks.cache_clear()
                gc.collect()
                result = timed_solve(SOLVERS[algorithm], level, start)
                validate_result(level, start, algorithm, result)
                if solver_signature(result) != expected[algorithm]:
                    raise RuntimeError(
                        f"{level.id}/{algorithm}: output changed between benchmark runs"
                    )
                samples[algorithm].append(result)
                raw_runs.append({
                    "level": level.id,
                    "group": level_group(level),
                    "algorithm": algorithm,
                    "repetition": repetition,
                    "order": order,
                    "run_type": "time",
                    "success": result.success,
                    "solution_length": result.solution_length,
                    "cost": f"{result.cost:.9f}" if algorithm in ("UCS", "A*") else "",
                    "expanded_nodes": result.expanded_nodes,
                    "time_ms": f"{result.search_time_ms:.6f}",
                    "peak_memory_kb": "",
                })

        for algorithm in SOLVERS:
            results = samples[algorithm]
            first = results[0]
            memory_result = memory_solve(SOLVERS[algorithm], level, start)
            validate_result(level, start, algorithm, memory_result)
            if solver_signature(memory_result) != expected[algorithm]:
                raise RuntimeError(f"{level.id}/{algorithm}: memory run returned a different result")
            raw_runs.append({
                "level": level.id,
                "group": level_group(level),
                "algorithm": algorithm,
                "repetition": 0,
                "order": 0,
                "run_type": "memory",
                "success": memory_result.success,
                "solution_length": memory_result.solution_length,
                "cost": f"{memory_result.cost:.9f}" if algorithm in ("UCS", "A*") else "",
                "expanded_nodes": memory_result.expanded_nodes,
                "time_ms": "",
                "peak_memory_kb": memory_result.peak_memory_kb,
            })
            details.append({
                "level": level.id,
                "group": level_group(level),
                "algorithm": algorithm,
                "success": str(first.success),
                "solution_length": first.solution_length,
                "cost": f"{first.cost:.6f}" if algorithm in ("UCS", "A*") else "",
                "expanded_nodes": first.expanded_nodes,
                "time_ms_median": f"{statistics.median(r.search_time_ms for r in results):.6f}",
                "time_ms_stdev": (
                    f"{statistics.stdev(r.search_time_ms for r in results):.6f}"
                    if len(results) > 1 else "0.000000"
                ),
                "peak_memory_kb_median": f"{memory_result.peak_memory_kb:.1f}",
                "repeats": repeats,
                "memory_runs": 1,
            })
        print(
            f"{level.id}: all four algorithms validated, {repeats} timed runs "
            "and one memory run each",
            flush=True,
        )

    summary: list[dict] = []
    for algorithm in SOLVERS:
        rows = [row for row in details if row["algorithm"] == algorithm]
        summary.append({
            "algorithm": algorithm,
            "solved_levels": sum(row["success"] == "True" for row in rows),
            "total_levels": len(rows),
            "median_time_ms": f"{statistics.median(float(row['time_ms_median']) for row in rows):.6f}",
            "median_peak_memory_kb": f"{statistics.median(float(row['peak_memory_kb_median']) for row in rows):.1f}",
            "median_expanded_nodes": f"{statistics.median(int(row['expanded_nodes']) for row in rows):.1f}",
            "median_solution_length": f"{statistics.median(int(row['solution_length']) for row in rows):.1f}",
            "repeats_per_level": repeats,
        })

    output = ROOT / "typst" / "data"
    output.mkdir(exist_ok=True)
    write_csv(output / "all_algorithms.csv", details)
    write_csv(output / "algorithm_summary.csv", summary)
    write_csv(output / "all_algorithms_raw.csv", raw_runs)

    source_files = [
        Path(__file__).resolve(),
        ROOT / "solvers" / "BFS.py",
        ROOT / "solvers" / "DFS.py",
        ROOT / "solvers" / "UCS.py",
        ROOT / "solvers" / "astar.py",
        ROOT / "solvers" / "common.py",
        ROOT / "core" / "interfaces.py",
        ROOT / "core" / "game_rules.py",
        ROOT / "core" / "movement.py",
        ROOT / "levels" / "level_loader.py",
        *sorted((ROOT / "levels").glob("level_*.json")),
    ]
    metadata = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "level_count": len(levels),
        "algorithms": list(SOLVERS),
        "repeats_per_level_algorithm": repeats,
        "timed_runs": repeats * len(levels) * len(SOLVERS),
        "memory_runs": len(levels) * len(SOLVERS),
        "total_solver_runs": len(raw_runs),
        "warmup": "one unmeasured, validated run per level and algorithm",
        "aggregation": "median and sample standard deviation of timed runs; one separate peak-allocation run",
        "timing": "perf_counter around solver.solve; tracemalloc disabled",
        "memory": "one separate tracemalloc peak-allocation run per level and algorithm; bytes // 1024",
        "validation": "replay every measured path; check goal, legality, length, and UCS/A* cost",
        "optimal_cost_cross_check": "UCS and A* reported costs must match on every level",
        "test_groups": {
            "Cơ bản": "no fragile tiles and no switches",
            "Ô dễ vỡ": "fragile tiles, no switches",
            "Công tắc/cầu": "one or more switches, no fragile tiles",
            "Kết hợp": "fragile tiles and one or more switches",
        },
        "sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"):
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_files
        },
    }
    (output / "all_algorithms_environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Saved {len(raw_runs)} measurements for {len(levels)} levels "
        f"and {len(SOLVERS)} algorithms in typst/data/",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3, help="measured runs per level/algorithm")
    collect(parser.parse_args().repeats)

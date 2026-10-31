"""Legacy A* and h=0 diagnostic; this script does not feed the final report.

Use collect_all_results.py to refresh the common four-solver report tables.
This legacy script still writes validation.csv and raw_runs.csv.

Usage: python typst/collect_results.py [--repeats 5]
Sequential, cold heuristic cache, one unmeasured warm-up per configuration.
Replay/validation and gc.collect are outside the measured solve interval.
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
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.game_rules import apply_move, get_successors, is_goal
from core.interfaces import GameState, SolverResult
from levels.level_loader import load_all_levels
from solvers.astar import AStarSolver, _relaxed_landmarks
from solvers.common import StepCost, run_solver


def validate(level, start: GameState, result: SolverResult) -> None:
    if result.success != (result.path is not None):
        raise RuntimeError(f"{level.id}: inconsistent result")
    if not result.success:
        return
    state, total, policy = start, 0.0, StepCost(level)
    if result.solution_length != len(result.path):
        raise RuntimeError(f"{level.id}: solution length mismatch")
    for action in result.path:
        child = apply_move(state, action, level)
        if child is None:
            raise RuntimeError(f"{level.id}: invalid replay")
        total += policy(state, action, child, level)
        state = child
    if not is_goal(state, level) or abs(total - result.cost) > 1e-9:
        raise RuntimeError(f"{level.id}: replay cost/goal mismatch")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def collect(repeats: int = 5) -> None:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if tracemalloc.is_tracing():
        raise RuntimeError("Run this script in a process without active tracemalloc")
    levels = load_all_levels(ROOT / "levels")
    if not levels:
        raise RuntimeError("No levels to measure")
    rows, raw = [], []
    for level in levels:
        start = GameState(level.start, level.initial_bridge_mask)
        # Populate core's static bridge-index cache outside measurements for
        # both configurations. Heuristic and StepCost preprocessing stay inside.
        get_successors(start, level)
        factories = {
            "astar": lambda: AStarSolver(),
            "h0": lambda: AStarSolver(heuristic=lambda state, level: 0.0),
        }
        signatures = {}
        for name, factory in factories.items():
            _relaxed_landmarks.cache_clear()
            result = factory().solve(level, start)
            validate(level, start, result)
            signatures[name] = (result.success, result.cost, result.solution_length,
                                result.expanded_nodes, result.path)
        if signatures["astar"][0] != signatures["h0"][0]:
            raise RuntimeError(f"{level.id}: reachability mismatch")
        if signatures["astar"][0] and abs(signatures["astar"][1] - signatures["h0"][1]) > 1e-9:
            raise RuntimeError(f"{level.id}: optimal cost mismatch")

        samples = {name: [] for name in factories}
        for repetition in range(1, repeats + 1):
            # Alternate order to reduce systematic order bias.
            order = ("astar", "h0") if repetition % 2 else ("h0", "astar")
            for order_index, name in enumerate(order, 1):
                _relaxed_landmarks.cache_clear()
                gc.collect()
                solver = factories[name]()
                try:
                    result = run_solver(solver, level, start)
                finally:
                    # run_solver currently lacks finally cleanup on exceptions.
                    # This script owns each tracing session and stops on errors.
                    if tracemalloc.is_tracing():
                        tracemalloc.stop()
                validate(level, start, result)
                signature = (result.success, result.cost, result.solution_length,
                             result.expanded_nodes, result.path)
                if signature != signatures[name]:
                    raise RuntimeError(f"{level.id}/{name}: result changed between runs")
                samples[name].append(result)
                raw.append({
                    "level": level.id, "algorithm": name, "repetition": repetition,
                    "order": order_index, "success": result.success,
                    "actions": result.solution_length, "cost": f"{result.cost:.9f}",
                    "expanded_nodes": result.expanded_nodes,
                    "time_ms": f"{result.search_time_ms:.6f}",
                    "peak_memory_kb": result.peak_memory_kb,
                })
        guided, baseline = samples["astar"][0], samples["h0"][0]
        row = {
            "level": level.id, "success": str(guided.success),
            "actions": guided.solution_length, "cost_astar": f"{guided.cost:.6f}",
            "cost_h0": f"{baseline.cost:.6f}", "expanded_astar": guided.expanded_nodes,
            "expanded_h0": baseline.expanded_nodes, "repeats": repeats,
        }
        for name in factories:
            row[f"time_ms_{name}"] = f"{statistics.median(r.search_time_ms for r in samples[name]):.6f}"
            row[f"memory_kb_{name}"] = f"{statistics.median(r.peak_memory_kb for r in samples[name]):.1f}"
        rows.append(row)
        print(f"{level.id}: {repeats} runs/config; "
              f"A* {row['time_ms_astar']} ms, {row['memory_kb_astar']} KB", flush=True)

    output = ROOT / "typst" / "data"
    output.mkdir(exist_ok=True)
    write_csv(output / "validation.csv", rows)
    write_csv(output / "raw_runs.csv", raw)
    files = [Path(__file__).resolve(), ROOT / "solvers" / "astar.py",
             ROOT / "solvers" / "common.py", ROOT / "core" / "interfaces.py",
             ROOT / "core" / "game_rules.py", ROOT / "core" / "movement.py",
             ROOT / "levels" / "level_loader.py",
             *sorted((ROOT / "levels").glob("level_*.json"))]
    metadata = {
        "python": platform.python_version(), "platform": platform.platform(),
        "purpose": "cost/replay validation and repeated time/memory measurement",
        "reference": "same AStarSolver with h=0 (uniform-cost ordering)",
        "level_count": len(rows), "repeats": repeats, "measured_runs": len(raw),
        "aggregation": "median of each metric per level/configuration",
        "warmup_runs_per_configuration": 1, "execution": "sequential, alternating order",
        "heuristic_cache": "cleared before each warm-up and measured run, outside timer",
        "core_bridge_index_cache": "prepared once per level, before timing",
        "gc": "collect before each measured run, outside timer; automatic GC enabled",
        "time": "perf_counter in common.run_solver; milliseconds; includes solve preprocessing",
        "memory": "tracemalloc peak Python allocations, integer bytes // 1024 from run_solver",
        "loading_rendering_replay": "excluded from measurements",
        "limits": "no timeout/node limit; exceptions stop collection, no partial CSV published",
        "sha256": {str(path.relative_to(ROOT)).replace("\\", "/"):
                   hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
    }
    (output / "environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved {len(raw)} measured runs for {len(rows)} levels in typst/data/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5, help="Measured runs per level/configuration")
    collect(parser.parse_args().repeats)

"""Generate per-solver and cross-solver plots from the unified benchmark CSV.

Run after collect_all_results.py:
    python typst/make_charts.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data" / "all_algorithms.csv"
FIGURES = HERE / "figures"
ALGORITHMS = ("BFS", "DFS", "UCS", "A*")
FILE_STEMS = {"BFS": "bfs", "DFS": "dfs", "UCS": "ucs", "A*": "astar"}
COLORS = {"BFS": "#005CA9", "DFS": "#FF9800", "UCS": "#4CAF50", "A*": "#8E44AD"}
METRICS = (
    ("time_ms_median", "Thời gian tìm kiếm", "ms"),
    ("peak_memory_kb_median", "Bộ nhớ đỉnh", "KB"),
    ("expanded_nodes", "Số nút mở rộng", "nút"),
    ("solution_length", "Độ dài lời giải", "số bước"),
)


def load_rows() -> list[dict[str, str]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"{DATA_FILE} not found; run collect_all_results.py first"
        )
    with DATA_FILE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No benchmark rows found in {DATA_FILE}")
    return rows


def draw_metric(ax, rows: list[dict[str, str]], metric: tuple[str, str, str], algorithms: tuple[str, ...]) -> None:
    column, title, ylabel = metric
    levels = list(dict.fromkeys(row["level"] for row in rows))
    width = 0.8 / len(algorithms)
    positions = np.arange(len(levels))
    for index, algorithm in enumerate(algorithms):
        by_level = {row["level"]: row for row in rows if row["algorithm"] == algorithm}
        values = [
            float(by_level[level][column]) if by_level[level]["success"] == "True" else 0
            for level in levels
        ]
        bars = ax.bar(
            positions + (index - (len(algorithms) - 1) / 2) * width,
            values,
            width,
            label=algorithm,
            color=COLORS[algorithm],
        )
        if len(algorithms) == 1:
            for bar in bars:
                bar.set_width(0.65)
    positive = [
        float(row[column])
        for row in rows
        if row["success"] == "True" and float(row[column]) > 0
    ]
    if positive and max(positive) / min(positive) > 30:
        ax.set_yscale("log")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions)
    ax.set_xticklabels([level.replace("level_", "") for level in levels])
    ax.set_xlabel("Màn chơi")
    ax.grid(axis="y", alpha=0.25)
    if len(algorithms) > 1:
        ax.legend(frameon=False, ncol=4, fontsize=8)


def save_overview(rows: list[dict[str, str]], algorithms: tuple[str, ...], filename: str) -> None:
    selected = [row for row in rows if row["algorithm"] in algorithms]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, metric in zip(axes.flat, METRICS):
        draw_metric(ax, selected, metric, algorithms)
    fig.suptitle("So sánh hiệu năng thuật toán trên cùng bộ màn chơi", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGURES / filename, dpi=200)
    plt.close(fig)
    print(f"Saved {FIGURES / filename}")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    for algorithm in ALGORITHMS:
        save_overview(rows, (algorithm,), f"{FILE_STEMS[algorithm]}_overview.png")
    save_overview(rows, ALGORITHMS, "algorithm_comparison.png")


if __name__ == "__main__":
    main()

"""
Generate charts for the BFS and DFS report sections.
Reads data/bfs_results.csv and data/dfs_results.csv (next to this script) and
writes PNG files into figures/:
  - bfs_overview.png, dfs_overview.png: 2x2 panels (time, memory, nodes, length)

Run from anywhere:  python make_charts_bfs_dfs.py
Requires: pip install matplotlib
"""
from __future__ import annotations

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
FIG_DIR = os.path.join(HERE, "figures")

PANELS = [
    # (csv column, title, y label)
    ("time_ms_mean", "Thời gian tìm kiếm", "ms"),
    ("peak_memory_kb", "Bộ nhớ đỉnh", "KB"),
    ("expanded_nodes", "Số nút mở rộng", "nút"),
    ("solution_length", "Độ dài lời giải", "số bước"),
]
COLORS = {"BFS": "#005CA9", "DFS": "#FF9800"}


def read_rows(algo: str) -> list[dict]:
    path = os.path.join(DATA_DIR, f"{algo.lower()}_results.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def overview(algo: str) -> None:
    rows = read_rows(algo)
    levels = [r["level"] for r in rows]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (column, title, ylabel) in zip(axes.flat, PANELS):
        values = [float(r[column]) if r["success"] == "True" else 0.0 for r in rows]
        ax.bar(range(len(levels)), values, color=COLORS[algo])
        positive = [v for v in values if v > 0]
        # Log scale only when values span a wide range (keeps narrow ranges readable)
        if positive and max(positive) / min(positive) > 30:
            ax.set_yscale("log")
        ax.set_title(f"{title} ({algo})")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(len(levels)))
        ax.set_xticklabels([lv.replace("level_", "") for lv in levels])
        ax.set_xlabel("Màn chơi")
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, f"{algo.lower()}_overview.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print("Saved", out)


def main() -> None:
    os.makedirs(FIG_DIR, exist_ok=True)
    overview("BFS")
    overview("DFS")


if __name__ == "__main__":
    main()

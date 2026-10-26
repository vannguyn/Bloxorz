"""JSON Level Loader for Bloxorz.

Loads stage configurations from JSON files, mapping them to authoritative
Level, BlockState, Switch, and TileType data structures.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from core.interfaces import BlockState, Level, Orientation, Switch, TileType

_DEFAULT_LEVELS_DIR = Path(__file__).resolve().parent


def compute_initial_bridge_mask(
    level_data: dict[str, Any],
    bridges: dict[str, list[tuple[int, int]]] | None = None,
) -> int:
    """Computes initial bridge bitmask from level data.

    Bit i = 1 if the i-th bridge is "open", 0 if "closed".
    If `bridges` dict is provided, indices correspond to the keys order of `bridges`.
    """
    mask = 0
    raw_bridges = level_data.get("bridges", [])

    if bridges is not None:
        bridge_keys = list(bridges.keys())
        state_by_id = {
            b["id"]: b.get("initial_state", "closed")
            for b in raw_bridges
            if "id" in b
        }
        for i, b_id in enumerate(bridge_keys):
            if state_by_id.get(b_id, "closed").strip().lower() == "open":
                mask |= (1 << i)
    else:
        for i, b in enumerate(raw_bridges):
            if b.get("initial_state", "closed").strip().lower() == "open":
                mask |= (1 << i)

    return mask


def _resolve_level_path(path_or_id: str | Path) -> Path:
    """Resolves a level identifier or path to an absolute existing Path."""
    path = Path(path_or_id)

    # 1. Exact existing path
    if path.exists():
        return path.resolve()

    # 2. Check in current working directory / levels
    cwd_levels = Path.cwd() / "levels"

    candidates: list[Path] = []
    # If path_or_id is just an id like 'level_01'
    name_str = str(path_or_id).strip()
    if not name_str.endswith(".json"):
        candidates.extend([
            cwd_levels / f"{name_str}.json",
            _DEFAULT_LEVELS_DIR / f"{name_str}.json",
            Path.cwd() / f"{name_str}.json",
        ])
        if name_str.isdigit():
            padded = f"level_{int(name_str):02d}.json"
            candidates.extend([
                cwd_levels / padded,
                _DEFAULT_LEVELS_DIR / padded,
            ])
    else:
        candidates.extend([
            cwd_levels / path.name,
            _DEFAULT_LEVELS_DIR / path.name,
            Path.cwd() / path,
        ])

    for cand in candidates:
        if cand.exists():
            return cand.resolve()

    raise FileNotFoundError(f"Could not find level file for identifier: {path_or_id}")


def load_level(path_or_id: str | Path) -> Level:
    """Loads a single Level from a JSON file path or level identifier."""
    level_path = _resolve_level_path(path_or_id)

    with open(level_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    level_id = str(data.get("id", level_path.stem))
    name = str(data.get("name", level_id))
    width = int(data["width"])
    height = int(data["height"])

    # Parse start state
    start_data = data["start"]
    start_pos = (int(start_data["position"][0]), int(start_data["position"][1]))
    start_orientation = Orientation(start_data.get("orientation", "standing"))
    start_block = BlockState(r=start_pos[0], c=start_pos[1], orientation=start_orientation)

    # Parse goal
    goal = (int(data["goal"][0]), int(data["goal"][1]))

    # Parse tiles
    tiles: dict[tuple[int, int], TileType] = {}

    # 1. Regular floor tiles
    for t in data.get("tiles", []):
        tiles[(int(t[0]), int(t[1]))] = TileType.FLOOR

    # 2. Bridges metadata and tiles
    bridges: dict[str, list[tuple[int, int]]] = {}
    for b in data.get("bridges", []):
        b_id = b["id"]
        b_tiles = [(int(t[0]), int(t[1])) for t in b.get("tiles", [])]
        bridges[b_id] = b_tiles
        for cell in b_tiles:
            tiles[cell] = TileType.BRIDGE

    # 3. Fragile tiles
    for t in data.get("fragile_tiles", []):
        tiles[(int(t[0]), int(t[1]))] = TileType.FRAGILE

    # 4. Goal tile
    tiles[goal] = TileType.GOAL

    # Parse switches
    switches: list[Switch] = []
    for s in data.get("switches", []):
        effect = s.get("effect", {})
        destinations = None
        if "destinations" in effect and effect["destinations"]:
            destinations = tuple(
                (int(d[0]), int(d[1])) for d in effect["destinations"]
            )
        mode = effect.get("mode", "toggle")
        bridge_ids = list(effect.get("bridge_ids", []))
        pos = (int(s["position"][0]), int(s["position"][1]))
        switches.append(
            Switch(
                id=s["id"],
                type=s["type"],
                position=pos,
                bridge_ids=bridge_ids,
                mode=mode,
                destinations=destinations,
            )
        )

    split_rules = data.get("split_rules", {})
    initial_bridge_mask = compute_initial_bridge_mask(data, bridges)

    return Level(
        width=width,
        height=height,
        tiles=tiles,
        goal=goal,
        start=start_block,
        bridges=bridges,
        switches=switches,
        split_rules=split_rules,
        id=level_id,
        name=name,
        initial_bridge_mask=initial_bridge_mask,
    )


def load_all_levels(directory: str | Path | None = None) -> list[Level]:
    """Finds all level_*.json files in directory, sorted naturally, and loads them."""
    if directory is not None:
        target_dir = Path(directory).resolve()
    else:
        # Check cwd/levels then default levels directory
        cwd_levels = Path.cwd() / "levels"
        if cwd_levels.exists() and cwd_levels.is_dir():
            target_dir = cwd_levels
        else:
            target_dir = _DEFAULT_LEVELS_DIR

    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Levels directory not found: {target_dir}")

    files = list(target_dir.glob("level_*.json"))

    def _natural_sort_key(path: Path) -> tuple[int, str]:
        match = re.search(r"\d+", path.stem)
        return (int(match.group()), path.name) if match else (999999, path.name)

    files.sort(key=_natural_sort_key)
    return [load_level(f) for f in files]

"""Load and validate JSON stages for both the core adapter and the GUI.

The renderer still consumes the small ``core.interfaces.Level`` contract.  This
module is the single place where JSON is converted into that contract, so the
UI never needs to know about file paths or raw JSON dictionaries.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from core.interfaces import BlockState, Level, Orientation, Switch, TileType


LEVELS_DIR = Path(__file__).resolve().parent


def _position(value: Any, field: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field} must be [row, column]")
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in value):
        raise ValueError(f"{field} must contain integers")
    return int(value[0]), int(value[1])


def _positions(values: Iterable[Any], field: str) -> list[tuple[int, int]]:
    return [_position(value, f"{field}[{index}]") for index, value in enumerate(values)]


def _orientation(value: Any) -> Orientation:
    aliases = {
        "standing": Orientation.STANDING,
        "horizontal": Orientation.LYING_H,
        "lying_h": Orientation.LYING_H,
        "vertical": Orientation.LYING_V,
        "lying_v": Orientation.LYING_V,
    }
    try:
        return aliases[str(value).strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown start orientation: {value!r}") from exc


def load_level(path: str | Path) -> Level:
    """Read one level file and fail early with a useful validation message."""
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Level file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{source} must contain a JSON object")
    required = ("id", "name", "width", "height", "start", "goal", "tiles")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"{source} is missing required fields: {', '.join(missing)}")

    width, height = data["width"], data["height"]
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError(f"{source} width and height must be positive integers")

    tiles_list = _positions(data["tiles"], "tiles")
    tiles = set(tiles_list)
    if len(tiles) != len(tiles_list):
        raise ValueError(f"{source} contains duplicate tile coordinates")

    def check_in_bounds(position: tuple[int, int], field: str) -> None:
        row, col = position
        if not (0 <= row < height and 0 <= col < width):
            raise ValueError(f"{source} {field} coordinate {position} is outside the board")

    for position in tiles:
        check_in_bounds(position, "tile")
    goal = _position(data["goal"], "goal")
    check_in_bounds(goal, "goal")
    if goal not in tiles and not any(goal in bridge.get("tiles", []) for bridge in data.get("bridges", [])):
        raise ValueError(f"{source} goal {goal} is not a tile or bridge tile")

    raw_start = data["start"]
    if not isinstance(raw_start, dict) or "position" not in raw_start or "orientation" not in raw_start:
        raise ValueError(f"{source} start must contain position and orientation")
    start_position = _position(raw_start["position"], "start.position")
    check_in_bounds(start_position, "start")
    start_orientation = _orientation(raw_start["orientation"])
    is_split = bool(raw_start.get("is_split", False))
    cube_positions = None
    if is_split:
        raw_cubes = raw_start.get("cube_positions")
        if not isinstance(raw_cubes, list) or len(raw_cubes) != 2:
            raise ValueError(f"{source} split start needs two cube_positions")
        cube_positions = tuple(_position(item, "start.cube_positions") for item in raw_cubes)
        for item in cube_positions:
            check_in_bounds(item, "start.cube_positions")
    start = BlockState(
        start_position[0], start_position[1], start_orientation,
        is_split=is_split, cube_positions=cube_positions,
        active_cube=int(raw_start.get("active_cube", 0)),
    )
    if not set(start.occupied_cells()).issubset(tiles):
        raise ValueError(f"{source} start block is not fully supported by tiles")

    fragile = _positions(data.get("fragile_tiles", []), "fragile_tiles")
    if len(fragile) % 2:
        raise ValueError(f"{source} fragile_tiles must contain pairs of coordinates")
    for position in fragile:
        check_in_bounds(position, "fragile_tiles")
        if position not in tiles:
            raise ValueError(f"{source} fragile tile {position} is not listed in tiles")
    for index in range(0, len(fragile), 2):
        first, second = fragile[index:index + 2]
        if first == second or abs(first[0] - second[0]) + abs(first[1] - second[1]) != 1:
            raise ValueError(f"{source} fragile_tiles[{index}:{index + 2}] must be two distinct adjacent cells")

    bridges: dict[str, list[tuple[int, int]]] = {}
    bridge_cells: set[tuple[int, int]] = set()
    for index, raw_bridge in enumerate(data.get("bridges", [])):
        if not isinstance(raw_bridge, dict) or "id" not in raw_bridge or "tiles" not in raw_bridge:
            raise ValueError(f"{source} bridges[{index}] must contain id and tiles")
        bridge_id = str(raw_bridge["id"])
        if bridge_id in bridges:
            raise ValueError(f"{source} has duplicate bridge id {bridge_id!r}")
        state = raw_bridge.get("initial_state", "closed")
        if state not in {"open", "closed"}:
            raise ValueError(f"{source} bridge {bridge_id!r} has invalid initial_state")
        bridge_tiles = _positions(raw_bridge["tiles"], f"bridges[{index}].tiles")
        if len(bridge_tiles) != 2:
            raise ValueError(f"{source} bridge {bridge_id!r} must occupy exactly two cells")
        if abs(bridge_tiles[0][0] - bridge_tiles[1][0]) + abs(bridge_tiles[0][1] - bridge_tiles[1][1]) != 1:
            raise ValueError(f"{source} bridge {bridge_id!r} cells must be adjacent")
        for position in bridge_tiles:
            check_in_bounds(position, f"bridge {bridge_id}")
            if position in bridge_cells:
                raise ValueError(f"{source} bridge tiles overlap at {position}")
            bridge_cells.add(position)
        bridges[bridge_id] = bridge_tiles

    switches: list[Switch] = []
    switch_ids: set[str] = set()
    for index, raw_switch in enumerate(data.get("switches", [])):
        if not isinstance(raw_switch, dict):
            raise ValueError(f"{source} switches[{index}] must be an object")
        switch_id = str(raw_switch.get("id", ""))
        if not switch_id or switch_id in switch_ids:
            raise ValueError(f"{source} has invalid or duplicate switch id {switch_id!r}")
        switch_ids.add(switch_id)
        switch_type = str(raw_switch.get("type", ""))
        if switch_type not in {"soft", "heavy", "split"}:
            raise ValueError(f"{source} switch {switch_id!r} has invalid type")
        position = _position(raw_switch.get("position"), f"switch {switch_id}.position")
        check_in_bounds(position, f"switch {switch_id}")
        if position not in tiles:
            raise ValueError(f"{source} switch {switch_id!r} is not on a regular tile")
        effect = raw_switch.get("effect", {})
        if not isinstance(effect, dict):
            raise ValueError(f"{source} switch {switch_id!r} effect must be an object")
        bridge_ids = [str(item) for item in effect.get("bridge_ids", [])]
        unknown = [item for item in bridge_ids if item not in bridges]
        if unknown:
            raise ValueError(f"{source} switch {switch_id!r} references unknown bridge {unknown[0]!r}")
        destinations = effect.get("destinations", [])
        parsed_destinations = tuple(_position(item, f"switch {switch_id}.destinations") for item in destinations)
        if switch_type == "split" and len(parsed_destinations) != 2:
            raise ValueError(f"{source} split switch {switch_id!r} needs two destinations")
        switches.append(
            Switch(
                switch_id,
                switch_type,
                position,
                bridge_ids,
                str(effect.get("mode", "toggle")),
                str(effect.get("type", "bridge")),
                effect.get("state"),
                str(effect.get("trigger", "enter")),
                parsed_destinations if parsed_destinations else None,
                bool(effect.get("lock_after_activation", False)),
            )
        )

    tile_types = {position: TileType.FLOOR for position in tiles}
    tile_types[goal] = TileType.GOAL
    for position in fragile:
        tile_types[position] = TileType.FRAGILE
    for bridge_tiles in bridges.values():
        for position in bridge_tiles:
            tile_types[position] = TileType.BRIDGE

    split_rules = dict(data.get("split_rules", {}))
    return Level(
        width=width,
        height=height,
        tiles=tile_types,
        goal=goal,
        start=start,
        bridges=bridges,
        switches=switches,
        split_rules=split_rules,
        id=str(data["id"]),
        name=str(data["name"]),
        difficulty=str(data.get("difficulty", "advanced" if (bridges or switches or fragile) else "basic")),
        description=str(data.get("description", "")),
        advanced_controls=tuple(str(item) for item in data.get("advanced_controls", [])),
        bridge_initial_states={
            str(item["id"]): str(item.get("initial_state", "closed"))
            for item in data.get("bridges", [])
        },
    )


def load_all_levels(directory: str | Path = LEVELS_DIR) -> list[Level]:
    files = sorted(Path(directory).glob("level_*.json"))
    if not files:
        raise ValueError(f"No level_*.json files found in {directory}")
    levels = [load_level(path) for path in files]
    ids = [level.id for level in levels]
    if len(set(ids)) != len(ids):
        raise ValueError("Level ids must be unique")
    return levels


__all__ = ["LEVELS_DIR", "load_level", "load_all_levels"]

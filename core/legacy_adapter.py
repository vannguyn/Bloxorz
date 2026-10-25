"""Compatibility adapter from the renderer contract to the authoritative core.

The Pygame layer uses row/column coordinates and a compact bitmask for legacy
rendering.  ``core.game_state.GameState`` uses x/y coordinates and explicit
bridge states.  Keeping this translation here lets both the GUI and solvers
execute exactly the same modern core rules.
"""
from __future__ import annotations

from core.block import Block, Cube, Direction, Orientation as CoreOrientation
from core.board import Board, Bridge, SplitRules, Switch as CoreSwitch, SwitchEffect
from core.game_state import GameState as CoreState
from core.interfaces import BlockState, GameState, Level, Orientation


def _to_core_position(position: tuple[int, int]) -> tuple[int, int]:
    row, column = position
    return column, row


def _from_core_position(position: tuple[int, int]) -> tuple[int, int]:
    x, y = position
    return y, x


def _to_core_orientation(orientation: Orientation) -> CoreOrientation:
    return {
        Orientation.STANDING: CoreOrientation.STANDING,
        Orientation.LYING_H: CoreOrientation.HORIZONTAL,
        Orientation.LYING_V: CoreOrientation.VERTICAL,
    }[orientation]


def _from_core_orientation(orientation: CoreOrientation) -> Orientation:
    return {
        CoreOrientation.STANDING: Orientation.STANDING,
        CoreOrientation.HORIZONTAL: Orientation.LYING_H,
        CoreOrientation.VERTICAL: Orientation.LYING_V,
    }[orientation]


def level_to_board(level: Level) -> Board:
    bridge_map = {
        bridge_id: Bridge(
            bridge_id,
            frozenset(_to_core_position(position) for position in positions),
            (level.bridge_initial_states or {}).get(bridge_id, "closed"),
        )
        for bridge_id, positions in level.bridges.items()
    }
    # The old Level contract stores bridge coordinates separately from the
    # tile map.  Initial states are inferred from the JSON loader's metadata
    # when available, and default to closed for backwards compatibility.
    switches = {}
    for switch in level.switches:
        effect = SwitchEffect(
            type=switch.effect_type,
            bridge_ids=tuple(switch.bridge_ids),
            mode=switch.mode,
            state=switch.state,
            trigger=switch.trigger,
            destinations=tuple(_to_core_position(item) for item in (switch.destinations or ())),
            lock_after_activation=switch.lock_after_activation,
        )
        switches[switch.id] = CoreSwitch(switch.id, switch.type, _to_core_position(switch.position), effect)

    split_raw = level.split_rules
    split_rules = SplitRules(
        control_switch_key=str(split_raw.get("control_switch_key", "SPACE")),
        merge_when_adjacent=bool(split_raw.get("merge_when_adjacent", True)),
        single_cube_can_win=bool(split_raw.get("single_cube_can_win", False)),
        single_cube_activates=frozenset(split_raw.get("single_cube_activates", ["soft"])),
        single_cube_cannot_activate=frozenset(split_raw.get("single_cube_cannot_activate", ["heavy", "split"])),
    )
    # Level.tile keys are row/column; core Board uses x/y.
    regular_tiles = {
        _to_core_position(position)
        for position in level.tiles
        if position not in {cell for cells in level.bridges.values() for cell in cells}
    }
    return Board(
        width=level.width,
        height=level.height,
        tiles=frozenset(regular_tiles),
        goal=_to_core_position(level.goal),
        fragile_tiles=frozenset(_to_core_position(position) for position, tile in level.tiles.items() if tile.value == 3),
        bridges=bridge_map,
        switches=switches,
        split_rules=split_rules,
    )


def _to_core_state(level: Level, state: GameState) -> CoreState:
    block = state.block
    if block.is_split and block.cube_positions:
        first, second = (_to_core_position(item) for item in block.cube_positions)
        return CoreState(
            level_to_board(level), Cube(first), Cube(second),
            controlled_index=block.active_cube,
            bridge_states=_bridge_states(level, state.bridge_mask),
            locked_switches=state.locked_switches,
            moves=state.moves,
        )
    return CoreState(
        level_to_board(level),
        Block(_to_core_position((block.r, block.c)), _to_core_orientation(block.orientation)),
        bridge_states=_bridge_states(level, state.bridge_mask),
        locked_switches=state.locked_switches,
        moves=state.moves,
    )


def _bridge_states(level: Level, mask: int) -> dict[str, str]:
    return {
        bridge_id: "open" if mask & (1 << index) else "closed"
        for index, bridge_id in enumerate(level.bridges)
    }


def _mask_from_states(level: Level, states: dict[str, str]) -> int:
    mask = 0
    for index, bridge_id in enumerate(level.bridges):
        if states.get(bridge_id) == "open":
            mask |= 1 << index
    return mask


def _from_core_state(level: Level, state: CoreState) -> GameState:
    if state.is_split:
        assert state.second_cube is not None
        positions = (_from_core_position(state.block.position), _from_core_position(state.second_cube.position))
        block = BlockState(
            positions[0][0], positions[0][1], Orientation.STANDING,
            is_split=True, cube_positions=positions, active_cube=state.controlled_index,
        )
    else:
        assert isinstance(state.block, Block)
        row, column = _from_core_position(state.block.position)
        block = BlockState(row, column, _from_core_orientation(state.block.orientation))
    return GameState(
        block=block,
        bridge_mask=_mask_from_states(level, state.bridge_map),
        locked_switches=state.locked_switches,
        moves=state.moves,
    )


def initial_state(level: Level) -> GameState:
    start = level.start
    mask = 0
    for index, bridge_id in enumerate(level.bridges):
        if (level.bridge_initial_states or {}).get(bridge_id, "closed") == "open":
            mask |= 1 << index
    return GameState(
        block=start,
        bridge_mask=mask,
    )


def apply_move(state: GameState, action: str, level: Level) -> GameState | None:
    core_state = _to_core_state(level, state)
    if str(action).upper() == "SPACE":
        if not core_state.is_split:
            return None
        return _from_core_state(level, core_state.switch_control())
    try:
        next_state = core_state.move(Direction.coerce(action))
    except (KeyError, ValueError):
        return None
    return None if next_state is None else _from_core_state(level, next_state)


def is_goal(state: GameState, level: Level) -> bool:
    return _to_core_state(level, state).is_won()


def would_break_fragile(state: GameState, action: str, level: Level) -> bool:
    """Return whether an attempted move fails specifically on fragile cells."""
    if str(action).upper() == "SPACE":
        return False
    core_state = _to_core_state(level, state)
    board = core_state.board
    try:
        if core_state.is_split:
            candidate_cells = (core_state.controlled_cube.moved(Direction.coerce(action)).position,)
            return bool(set(candidate_cells).intersection(board.fragile_tiles))
        candidate = core_state.block.moved(Direction.coerce(action))
    except (KeyError, ValueError):
        return False
    fragile_cells = set(candidate.cells).intersection(board.fragile_tiles)
    if not fragile_cells:
        return False
    return candidate.is_standing or not set(candidate.cells).issubset(board.fragile_tiles)


def state_key(state: GameState) -> tuple:
    block = state.block
    if block.is_split and block.cube_positions:
        shape = ("split", tuple(block.cube_positions), block.active_cube)
    else:
        shape = (block.r, block.c, block.orientation.value)
    return shape, state.bridge_mask, tuple(sorted(state.locked_switches))


__all__ = ["apply_move", "initial_state", "is_goal", "level_to_board", "state_key", "would_break_fragile"]

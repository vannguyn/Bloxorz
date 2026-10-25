"""
Core Game Rules & Bitmask State Transitions for Bloxorz.

Implements pure, zero-allocation game state transitions:
- Movement legality & support validation (void, grid bounds, bridges)
- Fragile tile weight distribution mechanics
- Switch activations (soft, heavy, split) and bridge bitmask manipulation
- Split cube control, movement, and adjacency merging
- Winning condition check (standing upright on goal)
"""
from __future__ import annotations

from core.interfaces import BlockState, GameState, Level, Orientation, Switch, TileType
from core.movement import roll_block

VALID_ACTIONS: frozenset[str] = frozenset({"U", "D", "L", "R", "SPACE"})


def is_goal(state: GameState, level: Level) -> bool:
    """
    Evaluates whether the given GameState satisfies the level's win condition.

    Condition:
        The block must be unsplit, oriented STANDING upright,
        and its anchor coordinates must match level.goal.
    """
    if state.block.is_split:
        return False
    if state.block.orientation != Orientation.STANDING:
        return False
    return (state.block.r, state.block.c) == level.goal


def apply_move(state: GameState, action: str, level: Level) -> GameState | None:
    """
    Applies an action to the game state and returns the resulting GameState,
    or None if the move is invalid or causes the block to fall/collapse into void.

    Args:
        state: Current immutable GameState.
        action: Move direction ('U', 'D', 'L', 'R') or 'SPACE'.
        level: Current Level configuration.

    Returns:
        Next GameState or None if move falls into void or collapses fragile tile.
    """
    # 1. Action validation
    if action not in VALID_ACTIONS:
        return None

    # SPACE is only valid when the block is currently split
    if action == "SPACE" and not state.block.is_split:
        return None

    # 2. Movement math
    next_block = roll_block(state.block, action)

    # 3. Support & fragile checks for all occupied cells
    bridge_keys = list(level.bridges.keys()) if level.bridges else []
    bridge_index = {b_id: i for i, b_id in enumerate(bridge_keys)}

    for cell in next_block.occupied_cells():
        # Check if cell belongs to a bridge
        in_bridge = False
        bridge_open = False
        if level.bridges:
            for b_id, b_tiles in level.bridges.items():
                if cell in b_tiles:
                    in_bridge = True
                    idx = bridge_index.get(b_id)
                    if idx is not None and (state.bridge_mask & (1 << idx)) != 0:
                        bridge_open = True
                    break

        if in_bridge:
            if not bridge_open:
                return None  # Closed bridge acts as void
        else:
            tile = level.tiles.get(cell) if level.tiles else None
            if tile is None or tile == TileType.VOID or tile == TileType.BRIDGE:
                return None  # Void or unlinked bridge tile -> fall into void

        # Fragile tile check: standing upright or single split cube collapses fragile tile
        tile = level.tiles.get(cell) if level.tiles else None
        if tile == TileType.FRAGILE:
            if next_block.is_split or next_block.orientation == Orientation.STANDING:
                return None  # Falls through fragile tile

    # 4. Adjacency & Merge for split cubes
    if next_block.is_split and next_block.cube_positions and len(next_block.cube_positions) == 2:
        pos0, pos1 = next_block.cube_positions
        dr = abs(pos0[0] - pos1[0])
        dc = abs(pos0[1] - pos1[1])
        if (dr == 1 and dc == 0) or (dr == 0 and dc == 1):
            min_r = min(pos0[0], pos1[0])
            min_c = min(pos0[1], pos1[1])
            if dr == 0 and dc == 1:
                next_block = BlockState(min_r, min_c, Orientation.LYING_H)
            else:
                next_block = BlockState(min_r, min_c, Orientation.LYING_V)

    # 5. Switch triggers
    entered_cells = set(next_block.occupied_cells()) - set(state.block.occupied_cells())
    new_bridge_mask = state.bridge_mask

    if level.switches and entered_cells:
        for switch in level.switches:
            if switch.position in entered_cells:
                sw_type = switch.type.lower()
                can_trigger = False
                if sw_type == "soft":
                    can_trigger = True
                elif sw_type == "heavy":
                    can_trigger = not next_block.is_split and next_block.orientation == Orientation.STANDING
                elif sw_type == "split":
                    can_trigger = not next_block.is_split and next_block.orientation == Orientation.STANDING

                if can_trigger:
                    # Split switch effect: teleport and separate into 2 cubes
                    if sw_type == "split":
                        destinations = getattr(switch, "destinations", None)
                        if destinations is None and hasattr(switch, "effect") and isinstance(switch.effect, dict):
                            destinations = switch.effect.get("destinations")
                        if destinations and len(destinations) >= 2:
                            dest0 = (int(destinations[0][0]), int(destinations[0][1]))
                            dest1 = (int(destinations[1][0]), int(destinations[1][1]))
                            next_block = BlockState(
                                r=dest0[0],
                                c=dest0[1],
                                orientation=Orientation.STANDING,
                                is_split=True,
                                cube_positions=(dest0, dest1),
                                active_cube=0,
                            )

                    # Bridge toggling / opening / closing
                    bridge_ids = getattr(switch, "bridge_ids", None)
                    if bridge_ids:
                        for b_id in bridge_ids:
                            if b_id in bridge_index:
                                idx = bridge_index[b_id]
                                mode = getattr(switch, "mode", "toggle").lower()
                                if mode == "toggle":
                                    new_bridge_mask ^= (1 << idx)
                                elif mode in ("open", "permanent"):
                                    new_bridge_mask |= (1 << idx)
                                elif mode == "close":
                                    new_bridge_mask &= ~(1 << idx)

    return GameState(block=next_block, bridge_mask=new_bridge_mask)

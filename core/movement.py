"""
Pure Rolling Movement Math for Bloxorz.
Calculates state transitions for solid blocks across 12 rolling configurations
and single-cell movements/toggling for split blocks.
"""
from __future__ import annotations

from core.interfaces import BlockState, Orientation

# Movement deltas for grid navigation: (dr, dc)
DIRECTION_DELTAS: dict[str, tuple[int, int]] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


def roll_block(block: BlockState, action: str) -> BlockState:
    """
    Computes the deterministic new BlockState resulting from rolling or moving the block.

    Args:
        block: The current BlockState (solid or split).
        action: Move direction ("U", "D", "L", "R") or "SPACE" (active cube toggle).

    Returns:
        The new BlockState after applying the action. If action is invalid or inapplicable,
        returns the original block state unchanged.
    """
    if block.is_split:
        if action == "SPACE":
            new_active = 1 - block.active_cube
            if block.cube_positions is not None:
                new_r, new_c = block.cube_positions[new_active]
            else:
                new_r, new_c = block.r, block.c
            return BlockState(
                r=new_r,
                c=new_c,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=block.cube_positions,
                active_cube=new_active,
            )

        if action in DIRECTION_DELTAS:
            dr, dc = DIRECTION_DELTAS[action]
            idx = block.active_cube
            if block.cube_positions is not None:
                cr, cc = block.cube_positions[idx]
                nr, nc = cr + dr, cc + dc
                if idx == 0:
                    new_cubes = ((nr, nc), block.cube_positions[1])
                else:
                    new_cubes = (block.cube_positions[0], (nr, nc))
                return BlockState(
                    r=nr,
                    c=nc,
                    orientation=Orientation.STANDING,
                    is_split=True,
                    cube_positions=new_cubes,
                    active_cube=idx,
                )
            else:
                return BlockState(
                    r=block.r + dr,
                    c=block.c + dc,
                    orientation=Orientation.STANDING,
                    is_split=True,
                    cube_positions=None,
                    active_cube=idx,
                )

        return block

    # Solid (unsplit) block rolling transitions:
    r, c, ori = block.r, block.c, block.orientation

    if ori == Orientation.STANDING:
        if action == "U":
            return BlockState(r - 2, c, Orientation.LYING_V)
        elif action == "D":
            return BlockState(r + 1, c, Orientation.LYING_V)
        elif action == "L":
            return BlockState(r, c - 2, Orientation.LYING_H)
        elif action == "R":
            return BlockState(r, c + 1, Orientation.LYING_H)

    elif ori == Orientation.LYING_H:
        if action == "U":
            return BlockState(r - 1, c, Orientation.LYING_H)
        elif action == "D":
            return BlockState(r + 1, c, Orientation.LYING_H)
        elif action == "L":
            return BlockState(r, c - 1, Orientation.STANDING)
        elif action == "R":
            return BlockState(r, c + 2, Orientation.STANDING)

    elif ori == Orientation.LYING_V:
        if action == "U":
            return BlockState(r - 1, c, Orientation.STANDING)
        elif action == "D":
            return BlockState(r + 2, c, Orientation.STANDING)
        elif action == "L":
            return BlockState(r, c - 1, Orientation.LYING_V)
        elif action == "R":
            return BlockState(r, c + 1, Orientation.LYING_V)

    return block

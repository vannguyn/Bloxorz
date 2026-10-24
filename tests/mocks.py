"""
Mock levels, transition rules, and stub solvers for parallel development.
Follows docs/parallel-engineering-plan.en.md §3.2. No pygame imports allowed.
"""
from __future__ import annotations

from core.interfaces import (
    BlockState,
    GameState,
    Level,
    Orientation,
    SolverResult,
    Switch,
    TileType,
)
from solvers.common import Solver


def mock_level_simple() -> Level:
    """3x7 corridor, no advanced tiles — clean corridor leading to goal."""
    tiles = {}
    for r in range(3):
        for c in range(7):
            tiles[(r, c)] = TileType.FLOOR
    goal = (1, 5)
    tiles[goal] = TileType.GOAL
    start_block = BlockState(r=1, c=1, orientation=Orientation.STANDING)
    return Level(
        width=7,
        height=3,
        tiles=tiles,
        goal=goal,
        start=start_block,
        bridges={},
        switches=[],
        split_rules={},
        id="mock_simple",
        name="Mock 1: Simple Corridor",
    )


def mock_level_with_fragile() -> Level:
    """Corridor with a fragile tile to test standing vs lying rules."""
    tiles = {}
    for r in range(3):
        for c in range(7):
            tiles[(r, c)] = TileType.FLOOR
    fragile_cell = (1, 3)
    tiles[fragile_cell] = TileType.FRAGILE
    goal = (1, 6)
    tiles[goal] = TileType.GOAL
    start_block = BlockState(r=1, c=1, orientation=Orientation.STANDING)
    return Level(
        width=7,
        height=3,
        tiles=tiles,
        goal=goal,
        start=start_block,
        bridges={},
        switches=[],
        split_rules={},
        id="mock_fragile",
        name="Mock 2: Fragile Tiles",
    )


def mock_level_with_bridge() -> Level:
    """Closed bridge + soft switch to test bridge bitmask in state identity."""
    tiles = {}
    for r in range(4):
        for c in range(8):
            tiles[(r, c)] = TileType.FLOOR
    # Void out column 4 except a bridge tile at (1, 4) and (2, 4)
    del tiles[(1, 4)]
    del tiles[(2, 4)]
    bridge_tiles = [(1, 4), (2, 4)]
    for pt in bridge_tiles:
        tiles[pt] = TileType.BRIDGE

    switch = Switch(
        id="sw_bridge",
        type="soft",
        position=(1, 2),
        bridge_ids=["north_bridge"],
        mode="toggle",
    )
    goal = (1, 6)
    tiles[goal] = TileType.GOAL
    start_block = BlockState(r=1, c=1, orientation=Orientation.STANDING)
    return Level(
        width=8,
        height=4,
        tiles=tiles,
        goal=goal,
        start=start_block,
        bridges={"north_bridge": bridge_tiles},
        switches=[switch],
        split_rules={},
        id="mock_bridge",
        name="Mock 3: Switches & Bridges",
    )


def mock_level_split() -> Level:
    """Level with split switch and split cubes."""
    tiles = {}
    for r in range(5):
        for c in range(8):
            tiles[(r, c)] = TileType.FLOOR
    goal = (2, 6)
    tiles[goal] = TileType.GOAL
    split_sw = Switch(
        id="sw_split",
        type="split",
        position=(2, 2),
        bridge_ids=[],
        mode="toggle",
    )
    start_block = BlockState(
        r=2,
        c=1,
        orientation=Orientation.STANDING,
        is_split=True,
        cube_positions=((2, 1), (3, 4)),
        active_cube=0,
    )
    return Level(
        width=8,
        height=5,
        tiles=tiles,
        goal=goal,
        start=start_block,
        bridges={},
        switches=[split_sw],
        split_rules={"control_switch_key": "SPACE", "merge_when_adjacent": True},
        id="mock_split",
        name="Mock 4: Split Cubes",
    )


# --- Core Transition & Rule Mock (TDD §2.3) ---

def roll_block(block: BlockState, action: str) -> BlockState:
    """Applies the deterministic orientation transition table."""
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


def is_legal(state: GameState, level: Level) -> bool:
    """Verifies that all occupied cells rest on valid tiles and respect fragile/bridge rules."""
    cells = state.occupied_cells()
    bridge_index_map = {b_id: i for i, b_id in enumerate(level.bridges.keys())}

    for cell in cells:
        if cell not in level.tiles:
            return False
        ttype = level.tiles[cell]
        if ttype == TileType.VOID:
            return False
        if ttype == TileType.BRIDGE:
            # Look up bridge status in bitmask
            # Find which bridge contains this cell
            for b_id, b_tiles in level.bridges.items():
                if cell in b_tiles:
                    bit = bridge_index_map.get(b_id, 0)
                    if not (state.bridge_mask & (1 << bit)):
                        return False

    # Fragile tile rule: standing upright on FRAGILE tile causes collapse
    if not state.block.is_split and state.block.orientation == Orientation.STANDING:
        stand_cell = (state.block.r, state.block.c)
        if level.tiles.get(stand_cell) == TileType.FRAGILE:
            return False

    return True


def is_goal(state: GameState, level: Level) -> bool:
    """True iff block is standing upright on goal cell and not split."""
    if state.block.is_split:
        return False
    return (
        state.block.orientation == Orientation.STANDING
        and (state.block.r, state.block.c) == level.goal
    )


def apply_move(state: GameState, action: str, level: Level) -> GameState | None:
    """Deterministic single-step transition; returns None if illegal/lost."""
    block = state.block
    new_mask = state.bridge_mask
    bridge_index_map = {b_id: i for i, b_id in enumerate(level.bridges.keys())}

    if block.is_split and block.cube_positions:
        if action == "SPACE":
            new_block = BlockState(
                r=block.r,
                c=block.c,
                orientation=block.orientation,
                is_split=True,
                cube_positions=block.cube_positions,
                active_cube=1 - block.active_cube,
            )
            return GameState(block=new_block, bridge_mask=new_mask)

        # Move active cube 1 unit
        idx = block.active_cube
        other_idx = 1 - idx
        cr, cc = block.cube_positions[idx]
        delta = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}.get(action, (0, 0))
        nr, nc = cr + delta[0], cc + delta[1]
        other_cube = block.cube_positions[other_idx]

        # Check adjacency for rejoin:
        dr = abs(nr - other_cube[0])
        dc = abs(nc - other_cube[1])
        if (dr == 1 and dc == 0) or (dr == 0 and dc == 1):
            # Merge cubes back into 1x1x2 block!
            min_r = min(nr, other_cube[0])
            min_c = min(nc, other_cube[1])
            new_ori = Orientation.LYING_V if dr == 1 else Orientation.LYING_H
            new_block = BlockState(r=min_r, c=min_c, orientation=new_ori, is_split=False)
        else:
            new_cubes = ((nr, nc), other_cube) if idx == 0 else (other_cube, (nr, nc))
            new_block = BlockState(
                r=nr,
                c=nc,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=new_cubes,
                active_cube=idx,
            )
    else:
        if action == "SPACE":
            return None
        new_block = roll_block(block, action)

    # Check switch activations
    for sw in level.switches:
        occupied = new_block.occupied_cells()
        if sw.position in occupied:
            can_trigger = False
            if sw.type == "soft":
                can_trigger = True
            elif sw.type == "heavy":
                can_trigger = not new_block.is_split and new_block.orientation == Orientation.STANDING
            elif sw.type == "split":
                can_trigger = not new_block.is_split and new_block.orientation == Orientation.STANDING

            if can_trigger:
                if sw.type == "split":
                    # Split into 2 positions
                    p1 = (sw.position[0] - 1, sw.position[1])
                    p2 = (sw.position[0] + 1, sw.position[1])
                    new_block = BlockState(
                        r=p1[0],
                        c=p1[1],
                        orientation=Orientation.STANDING,
                        is_split=True,
                        cube_positions=(p1, p2),
                        active_cube=0,
                    )
                else:
                    for b_id in sw.bridge_ids:
                        b_idx = bridge_index_map.get(b_id, 0)
                        if sw.mode == "toggle":
                            new_mask ^= (1 << b_idx)
                        elif sw.mode == "permanent":
                            new_mask |= (1 << b_idx)

    cand_state = GameState(block=new_block, bridge_mask=new_mask)
    if not is_legal(cand_state, level):
        return None
    return cand_state


def get_successors(state: GameState, level: Level) -> list[tuple[str, GameState, float]]:
    """Returns legal transitions [(action, next_state, step_cost)]."""
    actions = ["U", "D", "L", "R"]
    if state.block.is_split:
        actions.append("SPACE")

    successors = []
    for action in actions:
        nxt = apply_move(state, action, level)
        if nxt is not None:
            successors.append((action, nxt, 1.0))
    return successors


# --- Mock Solvers for GUI Integration ---

class MockBFSSolver(Solver):
    """Stub BFS solver providing fast test results for GUI integration."""
    def solve(self, level: Level, start: GameState) -> SolverResult:
        # Simple hardcoded or breadth-first search path on mock level
        # For mock corridor, goal is at (1, 5) from (1, 1): R, R, R, R
        return SolverResult(
            path=["R", "R", "R", "R"],
            expanded_nodes=12,
            search_time_ms=1.45,
            peak_memory_kb=32,
            solution_length=4,
            cost=4.0,
            success=True,
        )


class MockDFSSolver(Solver):
    def solve(self, level: Level, start: GameState) -> SolverResult:
        return SolverResult(
            path=["R", "R", "R", "R"],
            expanded_nodes=28,
            search_time_ms=2.10,
            peak_memory_kb=48,
            solution_length=4,
            cost=4.0,
            success=True,
        )


class MockUCSSolver(Solver):
    def solve(self, level: Level, start: GameState) -> SolverResult:
        return SolverResult(
            path=["R", "R", "R", "R"],
            expanded_nodes=15,
            search_time_ms=1.80,
            peak_memory_kb=40,
            solution_length=4,
            cost=4.0,
            success=True,
        )


class MockAStarSolver(Solver):
    def solve(self, level: Level, start: GameState) -> SolverResult:
        return SolverResult(
            path=["R", "R", "R", "R"],
            expanded_nodes=6,
            search_time_ms=0.92,
            peak_memory_kb=24,
            solution_length=4,
            cost=4.0,
            success=True,
        )

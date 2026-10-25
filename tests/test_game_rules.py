"""
Unit tests for Core Game Rules & Bitmask State Transitions (core/game_rules.py).
Tests void falls, fragile tiles, bridges, switches, split cubes, and win conditions.
"""
import pytest

from core.interfaces import BlockState, GameState, Level, Orientation, Switch, TileType
from core.game_rules import apply_move, is_goal


def create_simple_level(
    tiles: dict[tuple[int, int], TileType] | None = None,
    goal: tuple[int, int] = (1, 5),
    start: BlockState | None = None,
    bridges: dict[str, list[tuple[int, int]]] | None = None,
    switches: list[Switch] | None = None,
) -> Level:
    """Helper to create a test level with sensible defaults."""
    if tiles is None:
        tiles = {}
        for r in range(5):
            for c in range(8):
                tiles[(r, c)] = TileType.FLOOR
    if start is None:
        start = BlockState(r=1, c=1, orientation=Orientation.STANDING)
    if bridges is None:
        bridges = {}
    if switches is None:
        switches = []

    tiles[goal] = TileType.GOAL
    return Level(
        width=8,
        height=5,
        tiles=tiles,
        goal=goal,
        start=start,
        bridges=bridges,
        switches=switches,
        split_rules={"control_switch_key": "SPACE", "merge_when_adjacent": True},
        id="test_level",
        name="Test Level",
    )


class TestGoalCondition:
    def test_is_goal_standing_at_goal(self):
        level = create_simple_level(goal=(2, 3))
        state = GameState(
            block=BlockState(r=2, c=3, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        assert is_goal(state, level) is True

    def test_is_goal_lying_at_goal(self):
        level = create_simple_level(goal=(2, 3))
        state_h = GameState(
            block=BlockState(r=2, c=3, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        assert is_goal(state_h, level) is False

        state_v = GameState(
            block=BlockState(r=2, c=3, orientation=Orientation.LYING_V),
            bridge_mask=0,
        )
        assert is_goal(state_v, level) is False

    def test_is_goal_standing_not_at_goal(self):
        level = create_simple_level(goal=(2, 3))
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        assert is_goal(state, level) is False

    def test_is_goal_split_block_at_goal(self):
        level = create_simple_level(goal=(2, 3))
        state = GameState(
            block=BlockState(
                r=2,
                c=3,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((2, 3), (4, 4)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        assert is_goal(state, level) is False


class TestVoidAndBoundaryFall:
    def test_roll_off_board_into_void(self):
        level = create_simple_level()
        # Standing at (0, 1), rolling UP leaves the grid (r becomes -2, -1)
        state = GameState(
            block=BlockState(r=0, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        next_state = apply_move(state, "U", level)
        assert next_state is None

    def test_roll_onto_explicit_void_tile(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        tiles[(1, 2)] = TileType.VOID
        level = create_simple_level(tiles=tiles)

        # Lying horizontally at (1, 0), rolling R moves to standing at (1, 2) which is VOID
        state = GameState(
            block=BlockState(r=1, c=0, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is None

    def test_partially_supported_block_falls(self):
        tiles = {(1, 1): TileType.FLOOR}  # only (1, 1) exists
        level = create_simple_level(tiles=tiles)

        # Rolling from standing at (1, 1) to LYING_H at (1, 2), occupying (1, 2) and (1, 3)
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is None


class TestFragileTiles:
    def test_standing_on_fragile_falls(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        tiles[(1, 3)] = TileType.FRAGILE
        level = create_simple_level(tiles=tiles)

        # Lying H at (1, 1) occupying (1, 1) & (1, 2). Rolling R stands up at (1, 3) (fragile)
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is None

    def test_lying_on_fragile_supported(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        tiles[(1, 2)] = TileType.FRAGILE
        level = create_simple_level(tiles=tiles)

        # Standing at (1, 1). Rolling R lies horizontally at (1, 2) occupying (1, 2) [fragile] & (1, 3) [floor]
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert next_state.block.orientation == Orientation.LYING_H
        assert next_state.block.r == 1
        assert next_state.block.c == 2

    def test_lying_across_both_fragile_tiles_supported(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        tiles[(1, 2)] = TileType.FRAGILE
        tiles[(1, 3)] = TileType.FRAGILE
        level = create_simple_level(tiles=tiles)

        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert next_state.block.orientation == Orientation.LYING_H

    def test_split_cube_on_fragile_falls(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        tiles[(1, 2)] = TileType.FRAGILE
        level = create_simple_level(tiles=tiles)

        # Active cube 0 at (1, 1) moves R onto (1, 2) [fragile]
        state = GameState(
            block=BlockState(
                r=1,
                c=1,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 1), (3, 3)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is None


class TestBridgeBitmaskTransitions:
    def test_closed_bridge_acts_as_void(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        # Remove (1, 3) from tiles and make it bridge "b1"
        del tiles[(1, 3)]
        tiles[(1, 3)] = TileType.BRIDGE
        bridges = {"b1": [(1, 3)]}
        level = create_simple_level(tiles=tiles, bridges=bridges)

        # Lying at (1, 1). Rolling R stands up on (1, 3).
        # Bridge 0 is closed (bridge_mask = 0).
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is None

    def test_open_bridge_is_supported(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        del tiles[(1, 3)]
        tiles[(1, 3)] = TileType.BRIDGE
        bridges = {"b1": [(1, 3)]}
        level = create_simple_level(tiles=tiles, bridges=bridges)

        # Bridge 0 is open (bridge_mask = 1).
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=1,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert next_state.block.r == 1
        assert next_state.block.c == 3
        assert next_state.block.orientation == Orientation.STANDING

    def test_multiple_bridges_bitmask(self):
        tiles = {(r, c): TileType.FLOOR for r in range(4) for c in range(6)}
        del tiles[(1, 3)]
        del tiles[(2, 3)]
        tiles[(1, 3)] = TileType.BRIDGE
        tiles[(2, 3)] = TileType.BRIDGE
        # b1 at index 0 (bit 0), b2 at index 1 (bit 1)
        bridges = {"b1": [(1, 3)], "b2": [(2, 3)]}
        level = create_simple_level(tiles=tiles, bridges=bridges)

        # Mask = 1 (b1 open, b2 closed):
        # Stepping onto (1, 3) works:
        state1 = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0b01,
        )
        res1 = apply_move(state1, "R", level)
        assert res1 is not None

        # Stepping onto (2, 3) fails:
        state2 = GameState(
            block=BlockState(r=2, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0b01,
        )
        res2 = apply_move(state2, "R", level)
        assert res2 is None


class TestSwitchTriggers:
    def test_soft_switch_triggered_by_standing_and_lying(self):
        sw = Switch(
            id="sw1",
            type="soft",
            position=(1, 3),
            bridge_ids=["b1"],
            mode="toggle",
        )
        bridges = {"b1": [(0, 4)]}
        level = create_simple_level(bridges=bridges, switches=[sw])

        # 1. Standing roll onto switch toggles bridge bit 0:
        state_lying = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        res1 = apply_move(state_lying, "R", level)
        assert res1 is not None
        assert res1.bridge_mask == 1

        # 2. Lying roll onto switch toggles bridge bit 0:
        state_standing = GameState(
            block=BlockState(r=1, c=2, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        # Rolling R makes it LYING_H occupying (1, 3) and (1, 4)
        res2 = apply_move(state_standing, "R", level)
        assert res2 is not None
        assert res2.bridge_mask == 1

        # 3. Split cube stepping onto soft switch toggles bridge bit:
        state_split = GameState(
            block=BlockState(
                r=1,
                c=2,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (3, 3)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        res3 = apply_move(state_split, "R", level)
        assert res3 is not None
        assert res3.bridge_mask == 1

    def test_heavy_switch_requires_standing(self):
        sw = Switch(
            id="sw_heavy",
            type="heavy",
            position=(1, 3),
            bridge_ids=["b1"],
            mode="toggle",
        )
        bridges = {"b1": [(0, 4)]}
        level = create_simple_level(bridges=bridges, switches=[sw])

        # 1. Lying roll onto heavy switch does NOT trigger:
        state_standing = GameState(
            block=BlockState(r=1, c=2, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        res_lying = apply_move(state_standing, "R", level)
        assert res_lying is not None
        assert res_lying.bridge_mask == 0  # Not triggered!

        # 2. Standing roll onto heavy switch DOES trigger:
        state_lying = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        res_standing = apply_move(state_lying, "R", level)
        assert res_standing is not None
        assert res_standing.bridge_mask == 1  # Triggered!

        # 3. Split cube stepping onto heavy switch does NOT trigger:
        state_split = GameState(
            block=BlockState(
                r=1,
                c=2,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (3, 3)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        res_split = apply_move(state_split, "R", level)
        assert res_split is not None
        assert res_split.bridge_mask == 0  # Not triggered!

    def test_switch_modes_permanent_and_close(self):
        sw_perm = Switch(
            id="sw_open",
            type="soft",
            position=(1, 2),
            bridge_ids=["b1"],
            mode="permanent",
        )
        sw_close = Switch(
            id="sw_close",
            type="soft",
            position=(2, 2),
            bridge_ids=["b1"],
            mode="close",
        )
        bridges = {"b1": [(0, 4)]}
        level = create_simple_level(bridges=bridges, switches=[sw_perm, sw_close])

        # Step on sw_open (permanent): mask becomes 1
        s0 = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        s1 = apply_move(s0, "R", level)  # lands on (1, 2) and (1, 3)
        assert s1.bridge_mask == 1

        # Roll again on sw_open: mask remains 1
        s2 = apply_move(s1, "L", level)  # lands standing on (1, 1)
        s3 = apply_move(s2, "R", level)  # lands lying on (1, 2) & (1, 3)
        assert s3.bridge_mask == 1

        # Step on sw_close (mode="close"): mask becomes 0
        s4 = GameState(
            block=BlockState(r=2, c=1, orientation=Orientation.STANDING),
            bridge_mask=1,
        )
        s5 = apply_move(s4, "R", level)  # lands on (2, 2) & (2, 3)
        assert s5.bridge_mask == 0


class TestSplitMechanicsAndCubeMerge:
    def test_split_switch_activation(self):
        sw = Switch(
            id="sw_split",
            type="split",
            position=(1, 3),
            bridge_ids=[],
            mode="toggle",
        )
        sw.destinations = ((1, 5), (3, 5))
        level = create_simple_level(switches=[sw])

        # Standing roll onto split switch triggers teleport and split:
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.LYING_H),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert next_state.block.is_split is True
        assert next_state.block.cube_positions == ((1, 5), (3, 5))
        assert next_state.block.active_cube == 0
        assert next_state.block.r == 1
        assert next_state.block.c == 5

    def test_split_switch_does_not_trigger_when_lying(self):
        sw = Switch(
            id="sw_split",
            type="split",
            position=(1, 3),
            bridge_ids=[],
            mode="toggle",
        )
        sw.destinations = ((1, 5), (3, 5))
        level = create_simple_level(switches=[sw])

        # Lying roll onto split switch (standing at 1, 2 rolling R -> lying on 1, 3 & 1, 4)
        state = GameState(
            block=BlockState(r=1, c=2, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert next_state.block.is_split is False  # Not triggered!

    def test_split_block_space_toggles_active_cube(self):
        level = create_simple_level()
        state = GameState(
            block=BlockState(
                r=1,
                c=2,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (3, 5)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        next_state = apply_move(state, "SPACE", level)
        assert next_state is not None
        assert next_state.block.is_split is True
        assert next_state.block.active_cube == 1
        assert next_state.block.cube_positions == ((1, 2), (3, 5))

    def test_space_on_unsplit_block_returns_none(self):
        level = create_simple_level()
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        assert apply_move(state, "SPACE", level) is None

    def test_split_cube_single_step_movement(self):
        level = create_simple_level()
        state = GameState(
            block=BlockState(
                r=1,
                c=2,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (3, 5)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        # Move active cube 0 to the right: (1, 2) -> (1, 3)
        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert next_state.block.is_split is True
        assert next_state.block.cube_positions == ((1, 3), (3, 5))

    def test_adjacent_cubes_merge_horizontal(self):
        level = create_simple_level()
        # Cube 0 at (1, 2), Cube 1 at (1, 4). Move Cube 1 left -> (1, 3), adjacent to Cube 0!
        state = GameState(
            block=BlockState(
                r=1,
                c=4,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (1, 4)),
                active_cube=1,
            ),
            bridge_mask=0,
        )
        next_state = apply_move(state, "L", level)
        assert next_state is not None
        assert next_state.block.is_split is False
        assert next_state.block.orientation == Orientation.LYING_H
        assert next_state.block.r == 1
        assert next_state.block.c == 2
        assert next_state.block.occupied_cells() == [(1, 2), (1, 3)]

    def test_adjacent_cubes_merge_vertical(self):
        level = create_simple_level()
        # Cube 0 at (1, 2), Cube 1 at (3, 2). Move Cube 1 up -> (2, 2), adjacent to Cube 0!
        state = GameState(
            block=BlockState(
                r=3,
                c=2,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (3, 2)),
                active_cube=1,
            ),
            bridge_mask=0,
        )
        next_state = apply_move(state, "U", level)
        assert next_state is not None
        assert next_state.block.is_split is False
        assert next_state.block.orientation == Orientation.LYING_V
        assert next_state.block.r == 1
        assert next_state.block.c == 2
        assert next_state.block.occupied_cells() == [(1, 2), (2, 2)]

    def test_diagonal_cubes_do_not_merge(self):
        level = create_simple_level()
        # Cube 0 at (1, 2), Cube 1 at (3, 3). Move Cube 1 up -> (2, 3) (diagonally adjacent to (1, 2))
        state = GameState(
            block=BlockState(
                r=3,
                c=3,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (3, 3)),
                active_cube=1,
            ),
            bridge_mask=0,
        )
        next_state = apply_move(state, "U", level)
        assert next_state is not None
        assert next_state.block.is_split is True
        assert next_state.block.cube_positions == ((1, 2), (2, 3))

    def test_split_cube_cannot_overlap_other_cube(self):
        level = create_simple_level()
        # Active cube 0 at (1, 2) rolling R into cube 1 at (1, 3) -> pos0 == pos1 -> returns None
        state_0_into_1 = GameState(
            block=BlockState(
                r=1,
                c=2,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 2), (1, 3)),
                active_cube=0,
            ),
            bridge_mask=0,
        )
        assert apply_move(state_0_into_1, "R", level) is None

        # Active cube 1 at (1, 4) rolling L into cube 0 at (1, 3) -> pos0 == pos1 -> returns None
        state_1_into_0 = GameState(
            block=BlockState(
                r=1,
                c=4,
                orientation=Orientation.STANDING,
                is_split=True,
                cube_positions=((1, 3), (1, 4)),
                active_cube=1,
            ),
            bridge_mask=0,
        )
        assert apply_move(state_1_into_0, "L", level) is None


class TestEdgeCasesAndImmutability:
    def test_invalid_action_returns_none(self):
        level = create_simple_level()
        state = GameState(
            block=BlockState(r=1, c=1, orientation=Orientation.STANDING),
            bridge_mask=0,
        )
        assert apply_move(state, "INVALID", level) is None
        assert apply_move(state, "", level) is None

    def test_original_state_not_mutated(self):
        level = create_simple_level()
        block = BlockState(r=1, c=1, orientation=Orientation.STANDING)
        state = GameState(block=block, bridge_mask=0)

        next_state = apply_move(state, "R", level)
        assert next_state is not None
        assert state.block.r == 1
        assert state.block.c == 1
        assert state.block.orientation == Orientation.STANDING
        assert state.bridge_mask == 0

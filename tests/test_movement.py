import pytest
from core.interfaces import BlockState, Orientation
from core.movement import roll_block


class TestSolidBlockStandingTransitions:
    """Tests all 4 rolling transitions when block is STANDING."""

    @pytest.fixture
    def standing_block(self) -> BlockState:
        return BlockState(r=5, c=5, orientation=Orientation.STANDING)

    def test_roll_up_from_standing(self, standing_block: BlockState):
        # STANDING + U -> LYING_V at (r - 2, c)
        next_block = roll_block(standing_block, "U")
        assert next_block.r == 3
        assert next_block.c == 5
        assert next_block.orientation == Orientation.LYING_V
        assert next_block.occupied_cells() == [(3, 5), (4, 5)]
        assert not next_block.is_split

    def test_roll_down_from_standing(self, standing_block: BlockState):
        # STANDING + D -> LYING_V at (r + 1, c)
        next_block = roll_block(standing_block, "D")
        assert next_block.r == 6
        assert next_block.c == 5
        assert next_block.orientation == Orientation.LYING_V
        assert next_block.occupied_cells() == [(6, 5), (7, 5)]
        assert not next_block.is_split

    def test_roll_left_from_standing(self, standing_block: BlockState):
        # STANDING + L -> LYING_H at (r, c - 2)
        next_block = roll_block(standing_block, "L")
        assert next_block.r == 5
        assert next_block.c == 3
        assert next_block.orientation == Orientation.LYING_H
        assert next_block.occupied_cells() == [(5, 3), (5, 4)]
        assert not next_block.is_split

    def test_roll_right_from_standing(self, standing_block: BlockState):
        # STANDING + R -> LYING_H at (r, c + 1)
        next_block = roll_block(standing_block, "R")
        assert next_block.r == 5
        assert next_block.c == 6
        assert next_block.orientation == Orientation.LYING_H
        assert next_block.occupied_cells() == [(5, 6), (5, 7)]
        assert not next_block.is_split


class TestSolidBlockLyingHTransitions:
    """Tests all 4 rolling transitions when block is LYING_H."""

    @pytest.fixture
    def lying_h_block(self) -> BlockState:
        # Occupies (5, 5) and (5, 6)
        return BlockState(r=5, c=5, orientation=Orientation.LYING_H)

    def test_roll_up_from_lying_h(self, lying_h_block: BlockState):
        # LYING_H + U -> LYING_H at (r - 1, c)
        next_block = roll_block(lying_h_block, "U")
        assert next_block.r == 4
        assert next_block.c == 5
        assert next_block.orientation == Orientation.LYING_H
        assert next_block.occupied_cells() == [(4, 5), (4, 6)]
        assert not next_block.is_split

    def test_roll_down_from_lying_h(self, lying_h_block: BlockState):
        # LYING_H + D -> LYING_H at (r + 1, c)
        next_block = roll_block(lying_h_block, "D")
        assert next_block.r == 6
        assert next_block.c == 5
        assert next_block.orientation == Orientation.LYING_H
        assert next_block.occupied_cells() == [(6, 5), (6, 6)]
        assert not next_block.is_split

    def test_roll_left_from_lying_h(self, lying_h_block: BlockState):
        # LYING_H + L -> STANDING at (r, c - 1)
        next_block = roll_block(lying_h_block, "L")
        assert next_block.r == 5
        assert next_block.c == 4
        assert next_block.orientation == Orientation.STANDING
        assert next_block.occupied_cells() == [(5, 4)]
        assert not next_block.is_split

    def test_roll_right_from_lying_h(self, lying_h_block: BlockState):
        # LYING_H + R -> STANDING at (r, c + 2)
        next_block = roll_block(lying_h_block, "R")
        assert next_block.r == 5
        assert next_block.c == 7
        assert next_block.orientation == Orientation.STANDING
        assert next_block.occupied_cells() == [(5, 7)]
        assert not next_block.is_split


class TestSolidBlockLyingVTransitions:
    """Tests all 4 rolling transitions when block is LYING_V."""

    @pytest.fixture
    def lying_v_block(self) -> BlockState:
        # Occupies (5, 5) and (6, 5)
        return BlockState(r=5, c=5, orientation=Orientation.LYING_V)

    def test_roll_up_from_lying_v(self, lying_v_block: BlockState):
        # LYING_V + U -> STANDING at (r - 1, c)
        next_block = roll_block(lying_v_block, "U")
        assert next_block.r == 4
        assert next_block.c == 5
        assert next_block.orientation == Orientation.STANDING
        assert next_block.occupied_cells() == [(4, 5)]
        assert not next_block.is_split

    def test_roll_down_from_lying_v(self, lying_v_block: BlockState):
        # LYING_V + D -> STANDING at (r + 2, c)
        next_block = roll_block(lying_v_block, "D")
        assert next_block.r == 7
        assert next_block.c == 5
        assert next_block.orientation == Orientation.STANDING
        assert next_block.occupied_cells() == [(7, 5)]
        assert not next_block.is_split

    def test_roll_left_from_lying_v(self, lying_v_block: BlockState):
        # LYING_V + L -> LYING_V at (r, c - 1)
        next_block = roll_block(lying_v_block, "L")
        assert next_block.r == 5
        assert next_block.c == 4
        assert next_block.orientation == Orientation.LYING_V
        assert next_block.occupied_cells() == [(5, 4), (6, 4)]
        assert not next_block.is_split

    def test_roll_right_from_lying_v(self, lying_v_block: BlockState):
        # LYING_V + R -> LYING_V at (r, c + 1)
        next_block = roll_block(lying_v_block, "R")
        assert next_block.r == 5
        assert next_block.c == 6
        assert next_block.orientation == Orientation.LYING_V
        assert next_block.occupied_cells() == [(5, 6), (6, 6)]
        assert not next_block.is_split


class TestSplitBlockControls:
    """Tests active cube toggling and individual 1x1 cube movement."""

    @pytest.fixture
    def split_block_cube0_active(self) -> BlockState:
        return BlockState(
            r=2,
            c=1,
            orientation=Orientation.STANDING,
            is_split=True,
            cube_positions=((2, 1), (6, 8)),
            active_cube=0,
        )

    @pytest.fixture
    def split_block_cube1_active(self) -> BlockState:
        return BlockState(
            r=6,
            c=8,
            orientation=Orientation.STANDING,
            is_split=True,
            cube_positions=((2, 1), (6, 8)),
            active_cube=1,
        )

    def test_space_toggles_active_cube(self, split_block_cube0_active: BlockState):
        # 0 -> 1
        toggled = roll_block(split_block_cube0_active, "SPACE")
        assert toggled.is_split is True
        assert toggled.active_cube == 1
        assert toggled.cube_positions == ((2, 1), (6, 8))
        assert toggled.r == 6
        assert toggled.c == 8

        # 1 -> 0
        toggled_back = roll_block(toggled, "SPACE")
        assert toggled_back.is_split is True
        assert toggled_back.active_cube == 0
        assert toggled_back.cube_positions == ((2, 1), (6, 8))
        assert toggled_back.r == 2
        assert toggled_back.c == 1

    def test_move_active_cube_0(self, split_block_cube0_active: BlockState):
        # Move cube 0 UP: (2, 1) -> (1, 1), cube 1 stays (6, 8)
        up = roll_block(split_block_cube0_active, "U")
        assert up.is_split is True
        assert up.active_cube == 0
        assert up.cube_positions == ((1, 1), (6, 8))
        assert up.r == 1 and up.c == 1

        # Move cube 0 DOWN: (2, 1) -> (3, 1), cube 1 stays (6, 8)
        down = roll_block(split_block_cube0_active, "D")
        assert down.cube_positions == ((3, 1), (6, 8))
        assert down.r == 3 and down.c == 1

        # Move cube 0 LEFT: (2, 1) -> (2, 0), cube 1 stays (6, 8)
        left = roll_block(split_block_cube0_active, "L")
        assert left.cube_positions == ((2, 0), (6, 8))
        assert left.r == 2 and left.c == 0

        # Move cube 0 RIGHT: (2, 1) -> (2, 2), cube 1 stays (6, 8)
        right = roll_block(split_block_cube0_active, "R")
        assert right.cube_positions == ((2, 2), (6, 8))
        assert right.r == 2 and right.c == 2

    def test_move_active_cube_1(self, split_block_cube1_active: BlockState):
        # Move cube 1 UP: (6, 8) -> (5, 8), cube 0 stays (2, 1)
        up = roll_block(split_block_cube1_active, "U")
        assert up.is_split is True
        assert up.active_cube == 1
        assert up.cube_positions == ((2, 1), (5, 8))
        assert up.r == 5 and up.c == 8

        # Move cube 1 DOWN: (6, 8) -> (7, 8), cube 0 stays (2, 1)
        down = roll_block(split_block_cube1_active, "D")
        assert down.cube_positions == ((2, 1), (7, 8))
        assert down.r == 7 and down.c == 8

        # Move cube 1 LEFT: (6, 8) -> (6, 7), cube 0 stays (2, 1)
        left = roll_block(split_block_cube1_active, "L")
        assert left.cube_positions == ((2, 1), (6, 7))
        assert left.r == 6 and left.c == 7

        # Move cube 1 RIGHT: (6, 8) -> (6, 9), cube 0 stays (2, 1)
        right = roll_block(split_block_cube1_active, "R")
        assert right.cube_positions == ((2, 1), (6, 9))
        assert right.r == 6 and right.c == 9


class TestEdgeCasesAndImmutability:
    """Tests invalid actions, SPACE on unsplit block, and immutability."""

    def test_unsplit_block_ignores_space(self):
        standing = BlockState(r=1, c=1, orientation=Orientation.STANDING)
        result = roll_block(standing, "SPACE")
        assert result == standing

    def test_unknown_action_returns_unchanged(self):
        standing = BlockState(r=1, c=1, orientation=Orientation.STANDING)
        result = roll_block(standing, "INVALID")
        assert result == standing

    def test_original_state_not_mutated(self):
        block = BlockState(r=3, c=3, orientation=Orientation.STANDING)
        _ = roll_block(block, "U")
        assert block.r == 3
        assert block.c == 3
        assert block.orientation == Orientation.STANDING

import pytest
from core.interfaces import BlockState, GameState, Orientation
from core.game_rules import apply_move, is_goal
from levels.level_loader import load_level
from solvers.BFS import BFSSolver
from solvers.DFS import DFSSolver
from solvers.UCS import UCSSolver
from solvers.astar import AStarSolver

SOLVER_CLASSES = [BFSSolver, DFSSolver, UCSSolver, AStarSolver]

@pytest.fixture
def level():
    return load_level("level_01")

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_with_default_start(level, solver_cls):
    """Test solver works when start is None (defaults to level.start)."""
    solver = solver_cls()
    res = solver.solve(level)
    assert res.success
    assert res.solution_length > 0
    assert res.path is not None

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_with_coordinate_tuple(level, solver_cls):
    """Test solver works when passing a simple (r, c) standing coordinate."""
    solver = solver_cls()
    # level 1 start is (5, 1). Let's pass (5, 1) as a tuple
    res = solver.solve(level, start=(5, 1))
    assert res.success
    assert res.path is not None

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_with_position_keyword(level, solver_cls):
    """Test solver works with position keyword argument."""
    solver = solver_cls()
    res = solver.solve(level, position=(5, 1))
    assert res.success
    assert res.path is not None

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_after_brick_moved(level, solver_cls):
    """Test solver works from a state where the brick was moved manually."""
    init_state = GameState(level.start, level.initial_bridge_mask)
    # Roll Right twice
    s1 = apply_move(init_state, "R", level)
    assert s1 is not None
    s2 = apply_move(s1, "R", level)
    assert s2 is not None

    solver = solver_cls()
    # Solve from s2 (moved brick)
    res = solver.solve(level, start=s2)
    assert res.success
    assert res.path is not None

    # Verify that executing res.path from s2 reaches the goal!
    curr = s2
    for action in res.path:
        curr = apply_move(curr, action, level)
        assert curr is not None
    assert is_goal(curr, level)

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_from_blockstate(level, solver_cls):
    """Test solver works when passing a BlockState directly."""
    block = BlockState(5, 1, Orientation.STANDING)
    solver = solver_cls()
    res = solver.solve(level, start=block)
    assert res.success

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_when_already_at_goal(level, solver_cls):
    """Test solver returns empty path when brick is already at goal."""
    goal_block = BlockState(level.goal[0], level.goal[1], Orientation.STANDING)
    solver = solver_cls()
    res = solver.solve(level, start=goal_block)
    assert res.success
    assert res.solution_length == 0
    assert res.path == []

@pytest.mark.parametrize("solver_cls", SOLVER_CLASSES)
def test_solve_invalid_void_position(level, solver_cls):
    """Test solver handles illegal starting position over void."""
    solver = solver_cls()
    res = solver.solve(level, start=(0, 0))  # (0, 0) is void in level 1
    assert not res.success
    assert res.path is None


from __future__ import annotations

import pytest

from core.interfaces import BlockState, GameState, Level, Orientation
from solvers import BFS, DFS
from solvers.BFS import BFSSolver
from solvers.DFS import DFSSolver


def _state(index: int) -> GameState:
    return GameState(
        block=BlockState(r=index, c=0, orientation=Orientation.STANDING),
        bridge_mask=0,
    )


def _level(start: GameState) -> Level:
    return Level(
        width=1,
        height=1,
        tiles={},
        goal=(0, 0),
        start=start.block,
        bridges={},
        switches=[],
        split_rules={},
    )


def _patch_graph(
    monkeypatch: pytest.MonkeyPatch,
    states: dict[str, GameState],
    graph: dict[GameState, list[tuple[str, GameState]]],
    goal: GameState,
) -> Level:
    level = _level(states["S"])

    def successors(state, _level):
        return graph.get(state, [])

    def is_goal(state, _level):
        return state == goal

    monkeypatch.setattr(BFS, "get_successors", successors)
    monkeypatch.setattr(BFS, "is_goal", is_goal)
    monkeypatch.setattr(DFS, "get_successors", successors)
    monkeypatch.setattr(DFS, "is_goal", is_goal)
    return level


def test_bfs_finds_shortest_path_and_dfs_returns_valid_depth_first_path(monkeypatch):
    states = {name: _state(index) for index, name in enumerate("SBDCG")}
    start = states["S"]
    goal = states["G"]
    graph = {
        start: [("B", states["B"]), ("C", states["C"])],
        states["B"]: [("D", states["D"])],
        states["D"]: [("G", goal), ("back", start)],
        states["C"]: [("C-G", goal)],
    }
    level = _patch_graph(monkeypatch, states, graph, goal)

    bfs_result = BFSSolver().solve(level, start)
    dfs_result = DFSSolver().solve(level, start)

    assert bfs_result.success
    assert bfs_result.path == ["C", "C-G"]
    assert bfs_result.solution_length == 2
    assert dfs_result.success
    assert dfs_result.path == ["B", "D", "G"]
    assert dfs_result.solution_length == 3


@pytest.mark.parametrize("solver_type", [BFSSolver, DFSSolver])
def test_solvers_handle_start_goal_and_unreachable_goal(monkeypatch, solver_type):
    states = {"S": _state(0), "U": _state(1)}
    start = states["S"]
    unreachable_goal = states["U"]
    level = _patch_graph(monkeypatch, states, {}, start)

    start_result = solver_type().solve(level, start)
    assert start_result.success
    assert start_result.path == []
    assert start_result.solution_length == 0

    level = _patch_graph(monkeypatch, states, {start: []}, unreachable_goal)
    unreachable_result = solver_type().solve(level, start)
    assert not unreachable_result.success
    assert unreachable_result.path is None
    assert unreachable_result.solution_length == -1


def test_dependency_adapter_selects_real_bfs_and_dfs():
    from ui.dependencies import IS_MOCK_SOLVERS, get_solver

    assert isinstance(get_solver("BFS"), BFSSolver)
    assert isinstance(get_solver("DFS"), DFSSolver)
    assert IS_MOCK_SOLVERS is False

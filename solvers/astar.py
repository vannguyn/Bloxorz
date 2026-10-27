"""A* độc lập với GUI, dùng hợp đồng hiện tại của core.

UCS/A* dùng chung StepCost trong common.py. Dùng run_solver() trong common.py
để bổ sung số đo thời gian/bộ nhớ; solve() chỉ thực hiện tìm kiếm.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from functools import lru_cache
from itertools import count
from math import isfinite

from core.game_rules import get_successors, is_goal
from core.interfaces import GameState, Level, SolverResult
from .common import Solver, StepCost


Heuristic = Callable[[GameState, Level], float]
CostFunction = Callable[[GameState, str, GameState, Level], float]
Cell = tuple[int, int]


def _distance(first: Cell, second: Cell) -> int:
    """Số bước tối thiểu nếu một điểm được đi tối đa 2 ô Manhattan/bước."""
    manhattan = abs(first[0] - second[0]) + abs(first[1] - second[1])
    return (manhattan + 1) // 2


@lru_cache(maxsize=32)
def _relaxed_landmarks(
    goal: Cell, teleports: tuple[tuple[Cell, Cell], ...],
) -> tuple[tuple[Cell, int], ...]:
    """Shortest distance về goal trên đồ thị điểm được nới lỏng.

    Đi giữa mọi cặp landmark có cost ceil(Manhattan/2). Teleport có hướng
    từ split switch đến destination, cost 0. Dijkstra chạy trên cạnh đảo.
    Không cần dựng cả grid: chỉ giữ goal, switch và destination. Cache key
    chứa cấu hình bất biến, không dùng id(level) hay giữ mutable Level.
    """
    points = sorted({goal} | {cell for edge in teleports for cell in edge})
    reverse_teleports: dict[Cell, list[Cell]] = {}
    for source, destination in teleports:
        reverse_teleports.setdefault(destination, []).append(source)

    distances = {point: _distance(point, goal) for point in points}
    heap = [(distance, point) for point, distance in distances.items()]
    heapq.heapify(heap)
    while heap:
        distance, point = heapq.heappop(heap)
        if distance != distances[point]:
            continue
        predecessors = [(source, 0) for source in reverse_teleports.get(point, ())]
        predecessors.extend((source, _distance(source, point)) for source in points)
        for source, cost in predecessors:
            candidate = distance + cost
            if candidate < distances[source]:
                distances[source] = candidate
                heapq.heappush(heap, (candidate, source))
    return tuple(distances.items())


def heuristic(state: GameState, level: Level | None = None) -> float:
    """Lower bound chi phí StepCost từ relaxation một điểm, hỗ trợ teleport.

    Bỏ orientation, void/fragile và bridge blocking. Một điểm được đi tối
    đa 2 ô Manhattan/bước và teleport miễn phí từ split switch tới mỗi
    destination. Lấy min khoảng cách về goal trên mọi ô state đang chiếm.

    Mỗi ô ở successor thường cách một ô predecessor tối đa 2 Manhattan;
    split được mô phỏng bằng bước đến switch rồi teleport cost 0. SPACE
    giữ nguyên tập ô; merge cũng giữ nguyên tập ô sau chuyển động. Do đó
    h_actions(s) <= 1+h_actions(s') và h_actions(goal)=0. Nhân với lower
    bound edge cost 0.3 của StepCost giữ admissibility/consistency theo
    cost thật, bao gồm cube move 0.8 và SPACE 0.3. Không cộng penalty vào h.
    Xem docs/astar-heuristic.md để biết chứng minh và giới hạn chi tiết.

    Thiếu level thì trả zero vì không thể biết các lối tắt teleport.
    """
    if level is None:
        return 0.0
    teleports = tuple(sorted({
        (switch.position, destination)
        for switch in level.switches
        if switch.type.lower() == "split" and switch.destinations
        for destination in switch.destinations
    }))
    landmarks = _relaxed_landmarks(level.goal, teleports)
    return StepCost.MIN_EDGE_COST * min(
        _distance(cell, landmark) + remaining
        for cell in state.occupied_cells()
        for landmark, remaining in landmarks
    )


def _reconstruct_path(
    goal: GameState,
    parents: dict[GameState, tuple[GameState, str] | None],
) -> list[str]:
    """Lần ngược bảng cha về start rồi đảo thứ tự action."""
    path: list[str] = []
    state = goal
    while (parent := parents[state]) is not None:
        state, action = parent
        path.append(action)
    path.reverse()
    return path


_default_heuristic = heuristic


class AStarSolver(Solver):
    """Tìm lời giải ít cost nhất theo f(s) = g(s) + h(s).

    Heuristic tùy chỉnh phải admissible, hữu hạn, không âm và bằng zero
    tại goal. Kiểm tra giá trị runtime không chứng minh admissibility.
    Không yêu cầu consistency: state được reopen khi tìm được g tốt hơn.

    Dùng toàn bộ GameState frozen/hashable làm key, giữ cả orientation,
    bridge_mask, vị trí hai cube và active_cube. Không tự cài luật game.
    """

    def __init__(
        self, heuristic: Heuristic | None = None, *, cost: CostFunction | None = None,
    ) -> None:
        self._cost = cost
        # Custom cost chưa có lower bound chung: mặc định h=0 cho an toàn.
        # Custom heuristic do bên gọi chịu trách nhiệm chứng minh theo cost đó.
        self._heuristic = heuristic if heuristic is not None else (
            _default_heuristic if cost is None else lambda state, level: 0.0
        )

    def heuristic(self, state: GameState, level: Level) -> float:
        """Đánh giá heuristic được truyền vào và kiểm tra giá trị."""
        value = float(self._heuristic(state, level))
        if not isfinite(value) or value < 0:
            raise ValueError("A* heuristic must be finite and non-negative")
        if is_goal(state, level) and value != 0.0:
            raise ValueError("A* heuristic must be zero at a goal")
        return value

    def solve(self, level: Level, start: GameState) -> SolverResult:
        """Giải từ state của level; mỗi lần gọi có dữ liệu tìm kiếm riêng.

        expanded_nodes đếm pop còn hiệu lực, bao gồm goal. Start đã thắng
        trả path=[]; hết frontier trả path=None. Các lỗi được ném ra thay
        vì bị chuyển thành kết luận không có lời giải.

        Dùng policy StepCost của UCS; hiện chưa có limits hoặc cancellation.
        Thời gian/bộ nhớ bằng zero khi gọi trực tiếp; dùng run_solver()
        để đo các trường đó theo quy ước chung.
        """
        # Tính penalty một lần cho level này, tránh cache nhầm giữa các solve.
        cost = self._cost if self._cost is not None else StepCost(level)
        sequence = count()
        # Entry: (f, counter, g, state). Counter xử lý hòa f bằng FIFO
        # và ngăn heap so sánh các GameState không có thứ tự.
        frontier = [(self.heuristic(start, level), next(sequence), 0.0, start)]
        best_g: dict[GameState, float] = {start: 0.0}
        parents: dict[GameState, tuple[GameState, str] | None] = {start: None}
        expanded = 0

        while frontier:
            _, _, g, state = heapq.heappop(frontier)
            # heapq không có decrease-key: push entry mới khi cải thiện g,
            # rồi bỏ entry cũ khi nó được pop sau này.
            if g != best_g[state]:
                continue

            expanded += 1
            # Chỉ chấp nhận goal khi pop entry còn hiệu lực.
            if is_goal(state, level):
                path = _reconstruct_path(state, parents)
                return SolverResult(
                    path=path,
                    expanded_nodes=expanded,
                    search_time_ms=0.0,
                    peak_memory_kb=0,
                    solution_length=len(path),
                    cost=g,
                    success=True,
                )

            for action, next_state in get_successors(state, level):
                edge_cost = float(cost(state, action, next_state, level))
                if not isfinite(edge_cost) or edge_cost <= 0:
                    raise ValueError("StepCost must return a finite positive cost")
                next_g = g + edge_cost
                if not isfinite(next_g):
                    raise ValueError("Accumulated path cost overflow")
                if next_g >= best_g.get(next_state, float("inf")):
                    continue

                priority = next_g + self.heuristic(next_state, level)
                if not isfinite(priority):
                    raise ValueError("A* priority overflow")
                best_g[next_state] = next_g
                parents[next_state] = (state, action)
                # Không khóa state bằng closed set: cho phép reopen.
                heapq.heappush(
                    frontier, (priority, next(sequence), next_g, next_state)
                )

        return SolverResult(
            path=None,
            expanded_nodes=expanded,
            search_time_ms=0.0,
            peak_memory_kb=0,
            solution_length=-1,
            cost=float("inf"),
            success=False,
        )


__all__ = ["AStarSolver", "Heuristic", "heuristic"]





"""A* độc lập với GUI, dùng hợp đồng hiện tại của core.

Mỗi action (kể cả SPACE) có chi phí 1. Dùng run_solver() trong common.py
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
from .common import Solver


Heuristic = Callable[[GameState, Level], float]
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
    """Lower bound unit-cost từ relaxation một điểm, có hỗ trợ teleport.

    Bỏ orientation, void/fragile và bridge blocking. Một điểm được đi tối
    đa 2 ô Manhattan/bước và teleport miễn phí từ split switch tới mỗi
    destination. Lấy min khoảng cách về goal trên mọi ô state đang chiếm.

    Mỗi ô ở successor thường cách một ô predecessor tối đa 2 Manhattan;
    split được mô phỏng bằng bước đến switch rồi teleport cost 0. SPACE
    giữ nguyên tập ô; merge cũng giữ nguyên tập ô sau chuyển động. Do đó
    h(s) <= 1+h(s') cho mọi cạnh thật và h(goal)=0: consistent/admissible.
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
    return float(min(
        _distance(cell, landmark) + remaining
        for cell in state.occupied_cells()
        for landmark, remaining in landmarks
    ))


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


class AStarSolver(Solver):
    """Tìm lời giải ít action nhất theo f(s) = g(s) + h(s).

    Heuristic tùy chỉnh phải admissible, hữu hạn, không âm và bằng zero
    tại goal. Kiểm tra giá trị runtime không chứng minh admissibility.
    Không yêu cầu consistency: state được reopen khi tìm được g tốt hơn.

    Dùng toàn bộ GameState frozen/hashable làm key, giữ cả orientation,
    bridge_mask, vị trí hai cube và active_cube. Không tự cài luật game.
    """

    def __init__(self, heuristic: Heuristic = heuristic) -> None:
        self._heuristic = heuristic

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

        Hợp đồng hiện tại chưa có StepCost, limits hoặc cancellation.
        Thời gian/bộ nhớ bằng zero khi gọi trực tiếp; dùng run_solver()
        để đo các trường đó theo quy ước chung.
        """
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
                next_g = g + 1.0
                if next_g >= best_g.get(next_state, float("inf")):
                    continue

                priority = next_g + self.heuristic(next_state, level)
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


# ============================================================================
# BẢN THAM CHIẾU HỢP ĐỒNG TƯƠNG LAI — TOÀN BỘ ĐỀU LÀ COMMENT, KHÔNG THỰC THI.
# Không bỏ comment từng đoạn rồi trộn với implementation unit-cost phía trên.
# Khi các owner chốt API, dùng bản này để THAY implementation AStarSolver.
#
# Điều kiện tích hợp:
# - M1: GameState frozen/hashable chứa activated_switch_mask; Level.start là
#   GameState. get_successors trả Transition(action, next_state, events), chỉ
#   gồm state chơi được. Action là enum dùng chung. Các tên import dưới đây
#   là vị trí đề xuất; phải khớp module được nhóm thống nhất, không định nghĩa
#   bản sao của các kiểu hợp đồng trong file A*.
# - M4: StepCost(transition) trả float hữu hạn, dương; cùng policy với UCS.
#   Không suy đoán event từ tọa độ hoặc bridge_mask trong A*.
# - M3/M4/M5: chốt SearchStatus, SearchLimits, CancelToken, SolverResult và
#   cập nhật Solver.solve chung. SolverResult tương lai frozen, không còn
#   success/cost; dùng status/total_cost và tuple[Action, ...].
# - M5: truyền heuristic đã chứng minh theo đúng cost policy. Có thể truyền
#   lambda state, level: 0.0 làm baseline. Heuristic hiện tại dùng schema
#   occupied_cells/switch.destinations hiện tại; cần adapter nếu M1 đổi schema.
#   Chỉ tái sử dụng lower bound hiện tại nếu chứng minh vẫn đúng và cost >= 1;
#   nếu cost có thể < 1, scale theo min edge cost đã chứng minh hoặc dùng 0.
# - Harness: run_solver hiện gán trực tiếp metric vào result. Khi result frozen,
#   đổi harness sang dataclasses.replace(result, search_time_ms=..., ...).
#   Chỉ một nơi sở hữu tracemalloc, dùng try/finally, benchmark tuần tự/cô lập.
#   Thống nhất cold/warm cache; không reset cache hoặc tracing trong A*.
#
# Quy ước cần cả nhóm duyệt:
# - expanded_nodes = số pop không stale, gồm goal (giữ quy ước hiện tại).
# - generated_nodes = mọi Transition được xét, kể cả state trùng; không gồm start.
# - peak_frontier_size = số heap entry lớn nhất, kể cả stale entry; start là 1.
# - Ưu tiên CANCELLED > timeout > node budget; kiểm tra trước mỗi pop và trong
#   vòng successor. Budget đếm cả goal, nên budget=0 trả LIMIT_REACHED ngay.
# - Cancel/timeout là cooperative, không ngắt ngang một lời gọi core/heuristic.
# - Không trả partial path khi hết budget/cancel; path/cost/length là None.
#   Chỉ frontier cạn mà chưa bị giới hạn/hủy mới trả UNSOLVABLE.
#
# from time import perf_counter
# from core.interfaces import (
#     Action, CancelToken, GameState, Level, SearchLimits, SearchStatus,
#     SolverResult, StepCost,
# )
#
# class AStarSolver(Solver):
#     def __init__(self, cost: StepCost, heuristic: Heuristic) -> None:
#         self._cost = cost
#         self._heuristic = heuristic
#
#     def heuristic(self, state: GameState, level: Level) -> float:
#         value = float(self._heuristic(state, level))
#         if not isfinite(value) or value < 0:
#             raise ValueError("A* heuristic must be finite and non-negative")
#         if is_goal(state, level) and value != 0.0:
#             raise ValueError("A* heuristic must be zero at a goal")
#         return value
#
#     def solve(
#         self, level: Level, start: GameState, *,
#         limits: SearchLimits | None = None,
#         cancel: CancelToken | None = None,
#     ) -> SolverResult:
#         started = perf_counter()
#         limits = limits if limits is not None else SearchLimits()
#         budget = limits.max_expanded_nodes
#         timeout = limits.timeout_ms
#         if budget is not None and (type(budget) is not int or budget < 0):
#             raise ValueError("max_expanded_nodes must be a non-negative int")
#         if timeout is not None and (not isfinite(timeout) or timeout < 0):
#             raise ValueError("timeout_ms must be finite and non-negative")
#         deadline = None if timeout is None else started + timeout / 1000.0
#         expanded = 0
#         generated = 0
#
#         def interruption(*, before_pop: bool) -> SearchStatus | None:
#             if cancel is not None and cancel.cancelled:
#                 return SearchStatus.CANCELLED
#             if deadline is not None and perf_counter() >= deadline:
#                 return SearchStatus.LIMIT_REACHED
#             # Khi đã bắt đầu một expansion, cho phép xét xong successors;
#             # budget được kiểm tra trước khi bắt đầu pop kế tiếp.
#             if before_pop and budget is not None and expanded >= budget:
#                 return SearchStatus.LIMIT_REACHED
#             return None
#
#         sequence = count()
#         best_g: dict[GameState, float] = {start: 0.0}
#         parents: dict[GameState, tuple[GameState, Action] | None] = {start: None}
#         frontier = []
#         peak_frontier = 0
#         path: tuple[Action, ...] | None = None
#         total_cost: float | None = None
#         status = interruption(before_pop=True)
#         if status is None:
#             heapq.heappush(
#                 frontier, (self.heuristic(start, level), next(sequence), 0.0, start)
#             )
#             peak_frontier = 1
#
#         while frontier and status is None:
#             status = interruption(before_pop=True)
#             if status is not None:
#                 break
#             _, _, g, state = heapq.heappop(frontier)
#             if g != best_g[state]:
#                 continue
#             expanded += 1
#             if is_goal(state, level):
#                 # Không dùng _reconstruct_path kiểu list[str] của bản hiện tại.
#                 actions: list[Action] = []
#                 cursor = state
#                 while (parent := parents[cursor]) is not None:
#                     cursor, action = parent
#                     actions.append(action)
#                 path = tuple(reversed(actions))
#                 total_cost = g
#                 status = SearchStatus.FOUND
#                 break
#
#             for transition in get_successors(state, level):
#                 status = interruption(before_pop=False)
#                 if status is not None:
#                     break
#                 generated += 1
#                 edge_cost = float(self._cost(transition))
#                 if not isfinite(edge_cost) or edge_cost <= 0:
#                     raise ValueError("StepCost must return a finite positive cost")
#                 child = transition.next_state
#                 new_g = g + edge_cost
#                 if not isfinite(new_g):
#                     raise ValueError("Accumulated path cost overflow")
#                 if new_g >= best_g.get(child, float("inf")):
#                     continue
#                 priority = new_g + self.heuristic(child, level)
#                 if not isfinite(priority):
#                     raise ValueError("A* priority overflow")
#                 best_g[child] = new_g
#                 parents[child] = (state, transition.action)
#                 # Giữ reopen, stale check và counter như bản đang chạy.
#                 heapq.heappush(frontier, (priority, next(sequence), new_g, child))
#                 peak_frontier = max(peak_frontier, len(frontier))
#
#         if status is None:
#             # Kiểm tra hủy/timeout cả khi lần mở rộng cuối làm frontier cạn.
#             status = interruption(before_pop=False)
#             if status is None:
#                 status = SearchStatus.UNSOLVABLE
#         return SolverResult(
#             status=status,
#             path=path,
#             solution_length=len(path) if path is not None else None,
#             total_cost=total_cost,
#             expanded_nodes=expanded,
#             generated_nodes=generated,
#             peak_frontier_size=peak_frontier,
#             search_time_ms=(perf_counter() - started) * 1000.0,
#             peak_memory_kb=0,  # Harness sở hữu tracemalloc và điền bằng replace.
#         )
#
# Cách gọi SAU KHI chuyển đủ các dependency:
# solver = AStarSolver(cost=shared_step_cost, heuristic=proven_cost_heuristic)
# result = solver.solve(
#     level, level.start,
#     limits=SearchLimits(max_expanded_nodes=100_000, timeout_ms=5_000),
#     cancel=cancel_token,
# )
# if result.status is SearchStatus.FOUND:
#     replay_actions = result.path
#
# Checklist trước khi kích hoạt:
# - Graph có cost không đều: A* chọn đường ít cost dù có nhiều action hơn BFS.
# - A*(h=0) cùng optimal cost với UCS dùng chính shared_step_cost.
# - Exact remaining cost bằng UCS, admissibility/consistency theo cost thật.
# - State khác activated_switch_mask phải khác key; replay qua core thật.
# - Kiểm tra found/unsolvable/timeout/budget/cancel, start-goal và budget=0.
# - Kiểm tra metric, stale entries, reopen, cost lỗi và immutable result harness.
# - Benchmark thật thay mock, fixed manifest đủ cơ chế, repetitions, CSV và
#   cache policy; không dùng các code comment này làm bằng chứng đã tích hợp.
# ============================================================================

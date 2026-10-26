# Hướng dẫn nhanh về Tích hợp Giao diện người dùng (UI) & Thuật toán Giải (Solvers)

Tài liệu này hướng dẫn cách kết nối hệ thống Lõi trò chơi (Core), Màn chơi (Levels), Giao diện (UI) và các Thuật toán tìm kiếm (M3–M5 Solvers).

## 1. Trạng thái Hiện tại của Hệ thống
- **M1 (Core & Levels): ĐÃ HOÀN THÀNH & ĐÃ XÁC MINH VỚI 10 MÀN CHƠI THẬT.**
  - `core/game_rules.py`: Triển khai đầy đủ quy tắc chuyển trạng thái (`apply_move`, `is_goal`), kiểm tra rơi vào khoảng trống/ngoài biên, sàn yếu (`FRAGILE`), điều khiển cầu qua bitmask (`bridge_mask`), các loại công tắc (`soft`, `heavy`, `split`) và cơ chế phân tách/hợp nhất khối (`SPLIT`).
  - `levels/`: Toàn bộ 10 màn chơi JSON (`level_01.json` đến `level_10.json`) được tải qua `levels/level_loader.py:load_all_levels()`.
  - Trong `ui/dependencies.py`: Biến `IS_MOCK_CORE = False` đã được kích hoạt. Giao diện trò chơi (`main.py`) và bộ thử nghiệm hiệu năng (`scripts/benchmark.py`) đều chạy trên các màn chơi thật và lõi chuyển trạng thái thật.

- **M2 (UI & Rendering): ĐÃ HOÀN THÀNH.**
  - Vòng lặp Pygame, renderer 2D phẳng, renderer 3D Isometric đẳng cự, solver bridge đa tiến trình (`multiprocessing.Process`), replay lời giải với tùy chọn tốc độ (`0.5x`, `1.0x`, `2.0x`, `4.0x`) đã hoàn chỉnh.

- **M3–M5 (Solvers: BFS, DFS, UCS, A*): SẴN SÀNG ĐỂ TÍCH HỢP.**
  - Hiện tại `IS_MOCK_SOLVERS = True` sử dụng stub solver để kiểm thử luồng UI và benchmark mẫu. Khi cài đặt xong các solver thật, chỉ cần cắm vào điểm kết nối theo hướng dẫn dưới đây.

---

## 2. Điểm kết nối tích hợp (`ui/dependencies.py`)

Tất cả các thành phần phụ thuộc giữa UI, Core và Solvers được cô lập thông qua **`ui/dependencies.py`**. Không cần chỉnh sửa các tệp tin trong thư mục `rendering/` hoặc `ui/`!

### Hướng dẫn tích hợp M3–M5 Solvers:

1. **Kế thừa lớp cơ sở `Solver` từ `solvers/common.py`:**
   Mỗi thuật toán giải phải kế thừa `Solver` và hiện thực phương thức `solve(self, level: Level, start: GameState) -> SolverResult`:
   ```python
   from core.interfaces import Level, GameState, SolverResult
   from core.game_rules import apply_move, is_goal
   from solvers.common import Solver

   class BFSSolver(Solver):
       def solve(self, level: Level, start: GameState) -> SolverResult:
           # Duyệt trạng thái sử dụng apply_move(state, action, level)
           # và kiểm tra đích bằng is_goal(state, level).
           # Trả về đối tượng SolverResult.
           ...
   ```
   > **Lưu ý:**
   > - `run_solver()` trong `solvers/common.py` sẽ tự động đo lường thời gian thực thi bằng `time.perf_counter()` và bộ nhớ đỉnh bằng `tracemalloc`, gán vào `search_time_ms` và `peak_memory_kb` của `SolverResult`.
   > - Thuật toán A* có thể cài đặt thêm phương thức `heuristic(self, state: GameState, level: Level) -> float`.

2. **Cắm các solver thật vào `ui/dependencies.py`:**
   - Import các solver thật:
     ```python
     from solvers.bfs import BFSSolver
     from solvers.dfs import DFSSolver
     from solvers.ucs import UCSSolver
     from solvers.astar import AStarSolver
     ```
   - Đặt biến:
     ```python
     IS_MOCK_SOLVERS: bool = False
     ```
   - Cập nhật hàm `get_solver(algo: str) -> Solver`:
     ```python
     def get_solver(algo: str) -> Solver:
         name = algo.strip().upper()
         if name == "BFS":
             return BFSSolver()
         elif name == "DFS":
             return DFSSolver()
         elif name == "UCS":
             return UCSSolver()
         elif name in ("ASTAR", "A*"):
             return AStarSolver()
         raise ValueError(f"Unknown solver algorithm: {algo}")
     ```

3. **Cập nhật `scripts/benchmark.py`:**
   - Trong `get_benchmark_solvers()`, thay thế các `Mock*Solver` bằng các solver thực tế để thu thập dữ liệu benchmark cho báo cáo nghiệm thu (§3.6).

---

## 3. Xác minh Hệ thống

Sau khi tích hợp, thực hiện kiểm tra theo các bước sau:

```bash
# 1. Chạy toàn bộ bộ kiểm thử tự động (smoke tests, rule tests, loader tests)
./.venv/bin/pytest tests/ -v

# 2. Chạy thử nghiệm hiệu năng không giao diện (Headless Benchmark Suite)
./.venv/bin/python scripts/benchmark.py
# -> Kết quả sẽ được xuất ra bảng console và tệp `experiments/results.csv`

# 3. Khởi chạy giao diện người dùng
./.venv/bin/python main.py
# -> HUD trên cùng sẽ hiển thị nhãn `[REAL]` khi cả Core và Solvers đều là thật.
# -> Bạn có thể chọn màn chơi, chuyển thuật toán, bấm "Solve" và xem lời giải tự động phát lại.
```

---

## 4. Kiến trúc Hiển thị Kép (Dual Rendering Architecture: 2D & 3D Isometric)

Hệ thống giao diện Bloxorz hỗ trợ cơ chế hiển thị kép linh hoạt giữa chế độ 2D phẳng truyền thống (Top-Down) và chế độ 3D Đẳng cự (Isometric View).

### 4.1. So sánh Chế độ 2D Top-Down và 3D Isometric
- **2D Top-Down (Mặc định - Default)**:
  - Góc nhìn trực diện từ trên xuống, giúp người chơi và nhà phát triển dễ dàng quan sát bố cục lưới, tọa độ ma trận hàng-cột `(r, c)` và các ô tính năng (`FRAGILE`, `BRIDGE`, công tắc).
  - Sử dụng `BoardRenderer` và `BlockRenderer`.
- **3D Isometric View**:
  - Tái hiện phong cách không gian 3 chiều nguyên bản của tựa game Bloxorz kinh điển thông qua phép chiếu đẳng cự 2:1 tiêu chuẩn:
    $$\begin{aligned}
    x_{\text{iso}} &= (c - r) \cdot \frac{W}{2} + \text{offset}_x \\
    y_{\text{iso}} &= (c + r) \cdot \frac{H}{2} + \text{offset}_y
    \end{aligned}$$
    với tỉ lệ kích thước hình thoi ô sàn là $W : H = 2 : 1$ ($H = W / 2$).
  - Khối chữ nhật 3D (Extruded Cuboid) được hiển thị với 3 mặt trực quan: Mặt trên (Top), Mặt hông trái (Left flank), Mặt hông phải (Right flank) kết hợp bảng màu đổ bóng (lighting & shading) tinh tế.
  - Sắp xếp thứ tự vẽ theo chiều sâu tự động (Depth Sorting / Painter's Algorithm) dựa trên tổng chỉ số ma trận $(r + c)$ từ xa đến gần, đảm bảo không có hiện tượng xuyên thấu hình học giữa các ô gạch và khối hộp.
  - Hiệu ứng nâng nhẹ khi lăn (Lightweight Lift LERP): Khi chuyển động hoặc replay, khối hộp có độ nâng nhẹ theo cung parabol $z_{\text{lift}} = 0.35 \cdot \sin(\pi \cdot t)$ tạo cảm giác nhấc bổng mượt mà thay vì trượt bẹt trên mặt sàn.
  - Khối phân tách (Split Block) trong 3D hiển thị rõ nét 2 khối lập phương $1 \times 1 \times 1$ độc lập, với viền chỉ thị màu vàng kim rực rỡ quanh khối đang được kích hoạt điều khiển.

### 4.2. Cơ chế Điều phối Renderer trong `GameScreen`
`GameScreen` (`ui/game_screen.py`) đóng vai trò điều phối trung tâm và ủy quyền toàn bộ tác vụ dựng hình tới các renderer chuyên biệt mà **không làm thay đổi logic Core** (`core/` và `levels/`):
- Khi khởi tạo:
  ```python
  self.board_renderer = BoardRenderer(self.board_rect.width, self.board_rect.height)
  self.block_renderer = BlockRenderer(self.board_renderer)
  self.iso_board_renderer = IsometricBoardRenderer(self.board_rect.width, self.board_rect.height)
  self.iso_block_renderer = IsometricBlockRenderer(self.iso_board_renderer)
  self.view_mode = "2D"  # 2D là mặc định khi khởi động
  ```
- Khi thực thi vòng lặp dựng hình `GameScreen.draw()`:
  ```python
  if self.view_mode == "3D":
      self.iso_board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect)
      self.iso_block_renderer.draw(self.surface, self.current_state)
  else:
      self.board_renderer.draw(self.surface, self.level, self.current_state, self.board_rect)
      self.block_renderer.draw(self.surface, self.current_state)
  ```

### 4.3. Nút Điều khiển UI, Phím tắt và Cơ chế Lưu trạng thái (Persistence)
- **Nút bấm Sidebar (`btn_view_mode`)**: Nằm tại thanh điều khiển bên phải, hiển thị trực tiếp nhãn `View: 2D` hoặc `View: 3D`. Nhấp chuột trái vào nút để chuyển đổi luân phiên giữa 2 chế độ.
- **Phím tắt nhanh (`V`)**: Người chơi có thể nhấn phím `V` bất cứ lúc nào trong khi chơi thủ công hoặc trong khi đang xem Replay để chuyển đổi góc nhìn tức thì.
- **Duy trì trạng thái (State Persistence)**: Chế độ hiển thị `self.view_mode` được duy trì bền vững xuyên suốt vòng đời phiên chơi. Khi người dùng:
  - Tải màn chơi kế tiếp (`next_level()`) hoặc màn chơi trước (`prev_level()`)
  - Tải màn chơi bất kỳ (`load_level(idx)`)
  - Chơi lại màn chơi hiện tại (`restart_level()`)
  chế độ góc nhìn đã chọn (ví dụ `"3D"`) vẫn được giữ nguyên vẹn mà không bị reset về `"2D"`.

---

## Phụ lục: Tóm tắt Kiến trúc & Hợp đồng Dữ liệu

### 1. Cấu trúc dữ liệu chính (`core/interfaces.py`)
- **`GameState`**: `dataclass(frozen=True)` chứa `block: BlockState` và `bridge_mask: int`.
  - Hashing và so sánh trạng thái đạt $O(1)$, tối ưu cho cấu trúc tập đã duyệt (`visited: set[GameState]`).
  - Bitmask `bridge_mask`: bit thứ $i = 1$ nghĩa là cầu thứ $i$ đang mở; $0$ nghĩa là đóng (đóng vai trò như ô trống `VOID`).
- **`BlockState`**: `r`, `c`, `orientation` (`STANDING`, `LYING_H`, `LYING_V`), cờ `is_split`, `cube_positions` và `active_cube`.
- **`Level`**: Kích thước, từ điển tọa độ `tiles`, vị trí đích `goal`, khối ban đầu `start`, siêu dữ liệu `bridges`, danh sách `switches`, `split_rules`, và `initial_bridge_mask`.
- **`SolverResult`**:
  - `path: list[str] | None` (danh sách các hành động `"U"`, `"D"`, `"L"`, `"R"`, `"SPACE"` hoặc `None` nếu vô nghiệm).
  - `expanded_nodes: int` (số trạng thái đã lấy ra khỏi hàng đợi).
  - `search_time_ms: float` (thời gian tính bằng mili-giây).
  - `peak_memory_kb: int` (bộ nhớ đỉnh tính bằng kilobyte).
  - `solution_length: int` (độ dài đường đi, `-1` nếu vô nghiệm).
  - `cost: float` (tổng chi phí các bước đi).
  - `success: bool` (`True` nếu tìm thấy lời giải).

### 2. Các hành động hợp lệ (`actions`)
- `"U"`: Lăn lên trên (Up)
- `"D"`: Lăn xuống dưới (Down)
- `"L"`: Lăn sang trái (Left)
- `"R"`: Lăn sang phải (Right)
- `"SPACE"`: Đổi khối điều khiển khi khối đang ở trạng thái phân tách (`is_split == True`)

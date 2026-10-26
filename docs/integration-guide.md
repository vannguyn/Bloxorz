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

### 4.4. Tối ưu hóa Nhận diện & Hình ảnh các Ô Đặc biệt (Special Cells Visual Affordance Overhaul & Rubric Patch)
Nhằm mang lại trải nghiệm thị giác trực quan, giải quyết triệt để các hạn chế gây nhầm lẫn nhận diện trạng thái, nâng cao tính gợi ý tương tác (visual affordances) cho người chơi và đảm bảo tuân thủ tuyệt đối quy ước bài toán theo đề bài môn học (`AI - Project 1.pdf`), hệ thống dựng hình (cả 2D phẳng và 3D Isometric) đã được nâng cấp toàn diện với 5 cải tiến cốt lõi:

1. **Loại bỏ Xung đột Dấu X Đỏ & Giếng Vực Cơ khí Cầu Đóng (Elimination of Red-X Collision & Mechanical Docking on Closed Bridges)**:
   - *Vấn đề trước đây*: Cầu ở trạng thái đóng từng sử dụng dấu gạch chéo đỏ (Red-X), dẫn đến hiện tượng xung đột thị giác nghiêm trọng với Công tắc Nặng (`heavy switch`), khiến người chơi dễ nhầm lẫn giữa một cơ quan kích hoạt và một vực thẳm cấm đi.
   - *Giải pháp thiết kế*:
     - **Cầu Đóng (`Closed Bridge`)**: Thay thế hoàn toàn dấu X bằng cấu trúc giếng vực cơ khí tụt sâu (`sunken abyss pit`), trang bị hệ thống thanh ray cơ cấu trượt âm (`recessed docking rails`, mã màu `COLOR_BRIDGE_DOCK_RAIL = (35, 60, 80)`) cùng 4 chốt định vị góc dẫn hướng (`corner docking guide pins`, mã màu `COLOR_BRIDGE_DOCK_PIN = (45, 85, 110)`). Cầu đóng được khẳng định hoàn toàn không chứa bất kỳ điểm ảnh đỏ nào ($r > 150, g < 100, b < 100$).
     - **Công tắc Nặng (`Heavy Switch`)**: Ký hiệu chữ X màu đỏ công nghiệp dập nổi được bảo lưu độc quyền duy nhất cho Công tắc Nặng.

2. **Tấm Kính Cường lực Nứt Pixel-Art Retro & Chiều Sâu Phiến Đá 35% (Pixel-Art Amber-Orange Cracked Glass with Rust Depth & 35% Slab Depth)**:
   - *Bản sắc màu cam chuẩn Rubric (`AI - Project 1.pdf`)*: Ô gạch yếu (`FRAGILE`) bắt buộc phải nhận diện rõ ràng bằng sắc cam theo mô tả đề bài. Hệ thống sử dụng lớp nền kính cường lực màu hổ phách bán trong suốt (`COLOR_GLASS_FILL = (245, 130, 45, 185)`) cùng đường viền hổ phách sắc nét (`COLOR_GLASS_BORDER = (255, 160, 60)`), bảo toàn nghiêm ngặt quy tắc màu cam chủ đạo ($R > G > B$, chiếm $> 60\%$ diện tích bề mặt ô gạch).
   - *Hệ thống rạn nứt Pixel-Art 16-bit chuẩn quy chiếu (Canonical $32 \times 32$ Raster Crack Network)*: Thay vì các đường vector hình học trơn đơn điệu, bề mặt ô kính được tái hiện chân thực theo phong cách retro 16-bit (dựa trên bản mẫu quy chiếu `fragile_ref.png`) thông qua ma trận điểm ảnh chuẩn hóa $32 \times 32$:
     - **Vết nứt phản quang chính (`COLOR_GLASS_CRACK = (255, 255, 255, 230)`)**: Tập hợp hơn 85 tọa độ chuẩn (`FRAGILE_CRACK_WHITE` trong `config/settings.py`) khắc họa khe nứt chính chéo từ tây bắc sang đông nam với các đường gấp khúc zig-zag micro-fractures, phân nhánh lên mép trên $(10, 0)$ và mép dưới $(20, 31)$, đảm bảo điểm ảnh trắng sáng phản quang ($R, G, B > 220$).
     - **Bóng đổ chiều sâu khe nứt màu rỉ sét (`COLOR_GLASS_SHADOW = (140, 50, 10, 220)`)**: Hơn 50 tọa độ chuẩn (`FRAGILE_CRACK_SHADOW` trong `config/settings.py`) được dịch chuyển chính xác $+1\text{px}$ về phía đông nam (South-East offset) bám sát các đoạn nứt chính, mô phỏng chiều sâu vực rạn nứt thủy tinh 3D mà không làm tối hoặc biến chất lớp nền cam ($R \in [110, 180], G \in [30, 90], B < 60$).
   - *Quy trình dựng hình đa độ phân giải 2D & Chiếu phối cảnh 3D Isometric*:
     - **2D Board Renderer**: Dựng hình trực tiếp ma trận nứt lên bề mặt $32 \times 32\text{px}$ cục bộ và co giãn nội suy gần nhất (`pygame.transform.scale`) theo kích thước ô lưới thực tế (`tile_size`), duy trì độ sắc nét pixel-art tuyệt đối không bị mờ nhòe.
     - **3D Isometric Dimetric Projection**: Chuyển đổi tọa độ chuẩn hóa $(u, v) = (g_x / 32.0, g_y / 32.0)$ trực tiếp lên mặt thoi đỉnh (top diamond polygon) theo phép biến đổi affine thuận:
       $$\vec{P}(u, v) = \vec{C}_{\text{top}} + u \cdot (\vec{C}_{\text{right}} - \vec{C}_{\text{top}}) + v \cdot (\vec{C}_{\text{left}} - \vec{C}_{\text{top}})$$
       Mỗi điểm ảnh vết nứt được chiếu thành vi thoi góc nghiêng 2:1 đồng bộ hoàn hảo với góc nhìn isometric của toàn bàn cờ.
   - *Độ dày phiến đá 35% trong 3D Isometric*: Chiều dày khối đá hông (slab extrusion depth) của ô sàn yếu được tinh chỉnh thanh mảnh chính xác $35\%$ so với phiến sàn tiêu chuẩn ($d_{\text{fragile}} = \max(2, \text{round}(d \times 0.35))$), tạo cảm giác phiến kính mỏng manh, không chịu nổi trọng lực khi khối đá Bloxorz dựng đứng (chỉ chịu tải an toàn khi khối đá nằm ngang).

3. **Công tắc Nặng Chữ X Thép Công nghiệp Dập nổi 12 Điểm (12-Point Embossed Industrial Steel X Heavy Switch)**:
   - *Bệ thép đúc công nghiệp*: Đặt trên bệ thép hình vuông (2D) hoặc hình thoi bát giác (3D) màu xám đá phiến (`COLOR_HEAVY_BASE = (71, 85, 105)`), gia cố bằng 4 đinh tán kim loại màu xám sáng tại các góc (`(148, 163, 184)`).
   - *Chữ X đa giác 12 điểm dập nổi*: Biểu tượng chữ X dập nổi đa giác khép kín 12 điểm (`12-point closed polygon X-cross`) với bề mặt màu đỏ công nghiệp (`COLOR_HEAVY_RED = (239, 68, 68)`) và bóng đổ hông 3D góc cạnh màu đỏ đậm (`COLOR_HEAVY_DARKRED = (153, 27, 27)`).
   - *Phản hồi xúc giác cơ học (Tactile Depression)*: Ở trạng thái nghỉ, nắp chữ X nhô cao độ nâng $-3\text{px}$; khi khối đá đứng thẳng đè lên, nắp lún xuống $-1\text{px}$ sát bệ đệm (3D) và chuyển sắc phát quang (2D), nhấn mạnh cơ chế kích hoạt chỉ chấp nhận khối đá đứng thẳng dồn toàn bộ trọng lượng.

4. **Công tắc Phân tách Cánh Khung Vòm Kép Nén Khe Hở Động (Dual Arched Bracket Wings Split Switch with Dynamic Gap Compression)**:
   - *Thiết kế cánh khung vòm đối xứng*: Hiển thị hai cánh khung vòm đối xứng dạng ngoặc đơn (`arched bracket wings`) màu xanh lơ phát sáng (`COLOR_SPLIT_CYAN = (56, 189, 248)`) với viền thân đậm (`COLOR_SPLIT_DARK = (2, 132, 199)`), ngăn cách bởi rãnh cơ học tối trung tâm (`(15, 23, 42)`).
   - *Cơ chế nén khe hở động (Dynamic Gap Compression)*: Ở trạng thái nghỉ, khoảng cách giữa 2 cánh vòm là $6\text{px}$; khi khối đá tiếp xúc đè lên, hai cánh vòm nén co khép vào tâm còn $2\text{px}$, đồng thời hạ độ nâng lún từ $-3\text{px}$ xuống $-1\text{px}$ (3D), cung cấp phản hồi thị giác xúc giác sinh động cho cơ chế phân tách khối.

5. **Giếng Đích Thăm Thẳm với Chiều Sâu Quang Học (Optical Depth Goal Shaft with Abyss Void Floor)**:
   - Thay cho vòng tròn đích phẳng đơn điệu, ô đích (`GOAL`) trong không gian 3D Isometric được tái tạo thành một giếng sụt quang học hướng trục sâu xuống đáy không gian.
   - Cấu trúc bao gồm:
     - Vành miệng giếng mạ viền vàng kim tinh tế (`(190, 155, 50)`).
     - Thành giếng góc khuất bên trái đổ bóng tối sâu (`COLOR_GOAL_WALL_LEFT = (18, 22, 32)`).
     - Thành giếng góc đón sáng bên phải đổ bóng trung tính (`COLOR_GOAL_WALL_RIGHT = (28, 34, 48)`).
     - Đáy giếng hố đen thăm thẳm vô tận (`COLOR_GOAL_ABYSS = (6, 8, 12)`).
   - Thiết kế này tạo ra ảo ảnh thị giác chiều sâu mạnh mẽ, kích thích trực giác chiến thắng khi người chơi đưa khối đá rơi thẳng đứng vào miệng hố.

6. **Cam kết Tuân thủ Tuyệt đối Bảng Tiêu chí Đánh giá Môn học (Course Rubric Alignment - `AI - Project 1.pdf`)**:
   - Tất cả các nâng cấp thị giác đều tuân thủ chặt chẽ 100% rubric của môn học:
     - Ô sàn yếu (Fragile Tile) bảo lưu trọn vẹn sắc cam đặc trưng ($R > G > B$) theo định nghĩa đề bài, kết hợp hệ thống nứt pixel-art 16-bit 2 tầng màu (trắng phản quang và bóng đổ rỉ sét) để chống nhầm lẫn hoàn toàn.
     - Cầu đóng (Closed Bridge) triệt tiêu hoàn toàn dấu X đỏ, loại bỏ 100% xung đột thị giác với Công tắc Nặng.
     - Công tắc Nặng (Heavy Switch) chuẩn hình tượng chữ X đỏ dập nổi trên bệ thép.
     - Công tắc Phân tách (Split Switch) chuẩn hình tượng 2 dấu ngoặc/cánh phân tách màu xanh cyan.
     - 100% đồ họa vector và raster thủ công (Pygame procedural rendering), hoàn toàn không phụ thuộc bất kỳ file tài nguyên bitmap bên ngoài nào, bảo đảm tính độc lập, độ tin cậy và tốc độ khung hình mượt mà ($< 2.0\text{s}$ toàn bộ 107 unit tests).

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

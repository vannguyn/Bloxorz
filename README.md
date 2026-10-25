# Bloxorz

Tài liệu này mô tả cấu trúc dự án và vai trò của các thành phần đã tạo cho game
Bloxorz bằng Python và Pygame. Đây là bộ khung có thể cài đặt, chạy màn mẫu và
mở rộng thêm màn chơi, cơ chế, hình ảnh, âm thanh và hoạt ảnh.

## Cấu trúc dự án

```text
Bloxorz/
├── main.py
├── requirements.txt
├── README.md
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── block.py
│   ├── board.py
│   ├── movement.py
│   ├── game_rules.py
│   └── game_state.py
├── entities/
│   ├── __init__.py
│   ├── block_entity.py
│   ├── tile.py
│   ├── switch.py
│   └── bridge.py
├── levels/
│   ├── __init__.py
│   ├── level_loader.py
│   ├── level_manager.py
│   └── level_01.json
├── solvers/
│   ├── common.py
│   ├── BFS.py
│   ├── DFS.py
│   ├── UCS.py
│   └── astar.py
├── rendering/
│   ├── __init__.py
│   ├── board_renderer.py
│   ├── block_renderer.py
│   └── animation.py
├── ui/
│   ├── __init__.py
│   ├── menu_screen.py
│   ├── game_screen.py
│   ├── pause_screen.py
│   ├── result_screen.py
│   └── button.py
├── assets/
│   ├── images/
│   ├── sounds/
│   └── fonts/
├── tests/
│   ├── __init__.py
│   ├── test_movement.py
│   ├── test_game_rules.py
│   └── test_levels.py
├── build/
└── dist/
```

## Vai trò và công việc của từng phần

### Tệp ở thư mục gốc

- **`main.py`**: Mở game GUI khi chạy bình thường; nhận `--test core`, `--test
  levels`, `--test gui` hoặc `--test all` để chạy riêng các nhóm kiểm thử.
- **`requirements.txt`**: Liệt kê các thư viện cần cài, tối thiểu là phiên bản
  Pygame phù hợp. Người chơi cài thư viện bằng `pip install -r requirements.txt`.
- **`README.md`**: Tài liệu hướng dẫn cấu trúc dự án, cách cài đặt, chạy và kiểm
  thử game. Cập nhật file này khi cách chạy hoặc cấu trúc thay đổi.

### `config/` — cấu hình

- **`settings.py`**: Khai báo kích thước cửa sổ, FPS, kích thước ô, màu sắc, tiêu
  đề game và phím điều khiển. Tập trung các giá trị có thể điều chỉnh ở đây để
  tránh rải số cố định trong mã nguồn.

### `core/` — trạng thái và luật chơi

Phần này xử lý logic độc lập với cách vẽ để có thể kiểm thử mà không cần mở cửa
sổ game.

- **`block.py`**: Mô hình vị trí, hướng và tư thế của khối domino trên bàn. Cần
  biểu diễn được khối đang đứng dọc trên một ô hoặc nằm ngang trên hai ô.
- **`board.py`**: Biểu diễn lưới màn chơi, các ô hợp lệ, ô đích và các cơ chế
  trên bàn; cung cấp thao tác tra cứu ô theo tọa độ.
- **`movement.py`**: Tính vị trí và tư thế mới khi người chơi di chuyển lên,
  xuống, trái hoặc phải. Không tự quyết định hoạt ảnh hay vẽ khối.
- **`game_rules.py`**: Kiểm tra nước đi có hợp lệ không, khối có rơi khỏi bàn
  không, công tắc/cầu có được kích hoạt không và điều kiện chiến thắng.
- **`game_state.py`**: Lưu trạng thái logic hiện tại như màn chơi, vị trí khối,
  trạng thái cầu, số bước đi và trạng thái đang chơi/thắng. Tạm dừng là trạng
  thái giao diện, không làm thay đổi state dùng bởi solver.

### `entities/` — các vật thể trong game

- **`block_entity.py`**: Bao bọc `Block`/`Cube` của `core/` cho tầng hiển thị,
  không tự giữ bản sao vị trí hay luật di chuyển.
- **`tile.py`**: Mô tả loại ô; `core/board.py` tạo mô tả ô từ dữ liệu màn để
  renderer vẽ mà không tự suy diễn loại ô.
- **`switch.py`** và **`bridge.py`**: Khai báo dữ liệu bất biến của các cơ chế.
  `core/` dùng các entity này để áp dụng luật và trạng thái.

### `levels/` — dữ liệu màn chơi

- **`level_loader.py`**: Đọc tệp JSON, kiểm tra dữ liệu bắt buộc, kiểu dữ liệu,
  tọa độ, ô đặc biệt và tính nhất quán của màn; báo lỗi rõ ràng nếu dữ liệu sai.
- **`level_manager.py`**: Quản lý danh sách màn, màn đang chơi và việc chuyển
  sang màn trước/sau. `ui/game_screen.py` dùng manager này để chọn màn; tải lại
  trạng thái hiện tại được xử lý bằng chức năng restart.
- **`level_01.json`, ...**: Dữ liệu bàn chơi, không chứa luật xử lý hay mã vẽ.
  Mỗi màn cần khai báo kích thước/lưới, vị trí bắt đầu, ô đích và các ô, công
  tắc, cầu đặc biệt nếu có. Nên thống nhất một định dạng JSON và kiểm tra nó
  bằng `level_loader.py`.

#### Thông số cơ chế trong file màn chơi

Các trường dưới đây mô tả dữ liệu cơ chế; phần code đọc JSON và áp dụng luật cần
được triển khai trong `core/` và `levels/`.

- **`fragile_tiles`**: Danh sách tọa độ `[x, y]` của ô dễ vỡ. Mỗi tọa độ cũng
  phải có trong `tiles`. Khối đứng trên ô này thì rơi; khối nằm bắc qua ô thì
  vẫn an toàn.
- **`bridges`**: Mỗi cầu có `id` duy nhất, `tiles` là các tọa độ thuộc cầu và
  `initial_state` là `"open"` hoặc `"closed"`. Cầu đóng được xem như khoảng
  trống; cầu mở được xem như sàn. Tọa độ cầu không được lặp lại trong `tiles`.
- **`switches`**: Mỗi công tắc có `id`, `type` và tọa độ `position`.
  - `type: "soft"`: kích hoạt khi bất kỳ phần nào của khối đè lên công tắc.
  - `type: "heavy"`: chỉ kích hoạt khi khối đứng thẳng trên công tắc.
  - `type: "split"`: chỉ kích hoạt khi khối đứng thẳng; `effect.destinations`
    chứa tọa độ hai khối lập phương sau khi tách.
- **`effect.type: "bridge"`**: Hiệu ứng cầu; `bridge_ids` liệt kê một hoặc nhiều
  cầu cần điều khiển. `mode: "toggle"` đảo trạng thái mỗi lần kích hoạt.
  `mode: "permanent"` đặt cầu theo `state` (`"open"`/`"closed"`) và
  `lock_after_activation: true` giữ trạng thái đó sau khi kích hoạt.
- **`effect.trigger: "enter"`**: Chỉ kích hoạt lúc khối bước lên công tắc, không
  lặp liên tục khi khối vẫn nằm trên đó.
- **`split_rules`**: `control_switch_key` là phím đổi khối đang điều khiển;
  `merge_when_adjacent` cho phép nhập lại khi hai khối kề nhau;
  `single_cube_can_win` quyết định khối đơn có thể hoàn thành màn không.
  `single_cube_activates` và `single_cube_cannot_activate` liệt kê các loại công
  tắc khối đơn được phép hoặc không được phép kích hoạt.

Các màn JSON trong `levels/` dùng chung định dạng; mỗi màn chỉ khai báo những
cơ chế thực sự xuất hiện trên màn đó.

### `solvers/` — các thuật toán tìm lời giải

Các solver nhận trạng thái hiện tại của Bloxorz, sinh các nước đi hợp lệ thông qua
`core/`, kiểm tra trạng thái đã thăm và trả về chuỗi hướng di chuyển dẫn tới ô đích.
Trạng thái tìm kiếm cần bao gồm vị trí, tư thế của block và trạng thái các cơ chế trên
bàn (ví dụ trạng thái đóng/mở của bridge), không chỉ riêng tọa độ block.

- **`common.py`**: Chứa giao diện solver, sinh successor qua `core.GameState` và
  harness đo thời gian/bộ nhớ, tạo kết quả. Khóa trạng thái và kiểm tra goal thuộc
  `core/`, được các solver dùng chung để thống nhất quá trình tìm kiếm.
- **`BFS.py`**: Cài đặt Breadth-First Search. Thuật toán duyệt theo từng lớp độ sâu,
  dùng hàng đợi FIFO và tập `visited`. Khi mỗi nước đi có cùng chi phí, BFS tìm được
  lời giải có ít bước nhất; đổi lại có thể dùng nhiều bộ nhớ.
- **`DFS.py`**: Cài đặt Depth-First Search. Thuật toán đi sâu theo một nhánh trước,
  dùng stack hoặc đệ quy và tập trạng thái đã thăm để tránh chu kỳ. DFS thường ít
  tốn bộ nhớ hơn BFS nhưng không bảo đảm lời giải ngắn nhất; nên có giới hạn độ sâu
  hoặc cơ chế chống lặp phù hợp.
- **`UCS.py`**: Cài đặt Uniform-Cost Search. Thuật toán dùng hàng đợi ưu tiên và luôn
  mở rộng trạng thái có tổng chi phí từ đầu nhỏ nhất. Hàm chi phí phải được định nghĩa
  rõ trong report; nếu mọi nước đi đều có cost bằng 1 thì UCS tương đương BFS.
- **`astar.py`**: Cài đặt A*. Thuật toán ưu tiên trạng thái theo `f(n) = g(n) + h(n)`,
  trong đó `g(n)` là chi phí đã đi và `h(n)` ước lượng chi phí còn lại. Heuristic có
  thể dùng khoảng cách Manhattan kết hợp phạt tư thế chưa đứng; nếu heuristic không
  vượt quá chi phí thật thì A* vẫn bảo đảm lời giải tối ưu theo hàm cost đã chọn.

Tất cả solver cần dùng cùng một stage/test set và ghi lại thời gian tìm kiếm, bộ nhớ,
số node mở rộng và độ dài lời giải để phục vụ phần thực nghiệm của project.

### `rendering/` — vẽ và hoạt ảnh

- **`board_renderer.py`**: Vẽ lưới, ô, ô đích, công tắc và cầu theo trạng thái
  bàn chơi.
- **`block_renderer.py`**: Vẽ khối ở đúng vị trí, tư thế và tỷ lệ trên màn hình.
- **`animation.py`**: Nội suy chuyển động giữa vị trí cũ và mới để khối lăn mượt.
  Hoạt ảnh chỉ trình bày nước đi đã được logic chấp nhận, không thay thế việc
  kiểm tra luật.

### `ui/` — màn hình và thao tác người chơi

- **`menu_screen.py`**: Màn hình bắt đầu với lựa chọn bắt đầu game hoặc thoát.
- **`game_screen.py`**: Kết hợp hiển thị bàn/khối với HUD (ví dụ số bước và tên
  màn), nhận lệnh điều khiển và chuyển lệnh tới phần logic.
- **`pause_screen.py`**: Giao diện tạm dừng; `Esc` tiếp tục, hoặc chọn tiếp tục /
  quay lại menu.
- **`result_screen.py`**: Thông báo thắng/thua và cung cấp lựa chọn chơi lại hoặc
  sang màn tiếp theo.
- **`button.py`**: Thành phần nút dùng chung, xử lý vẽ, trạng thái hover và nhấn.

### `assets/` — tài nguyên tĩnh

- **`images/`**: Hình nền, hình ô, khối, nút và biểu tượng.
- **`sounds/`**: Nhạc nền và hiệu ứng âm thanh.
- **`fonts/`**: Phông chữ sử dụng trong game.

Chỉ lưu tài nguyên ở đây; không đặt luật chơi hoặc mã Python trong `assets/`.
Khi nạp tài nguyên, xử lý đường dẫn tương đối từ vị trí dự án và báo lỗi rõ ràng
nếu tài nguyên bắt buộc bị thiếu.

### `tests/` — kiểm thử

- **`test_movement.py`**: Kiểm tra tư thế và tọa độ sau từng hướng di chuyển,
  gồm cả trường hợp khối nằm trên một hoặc hai ô.
- **`test_game_rules.py`**: Kiểm tra rơi khỏi bàn, ô không hợp lệ, kích hoạt
  công tắc/cầu và điều kiện thắng.
- **`test_levels.py`**: Kiểm tra nạp màn hợp lệ và từ chối dữ liệu JSON thiếu,
  sai kiểu hoặc có tọa độ không hợp lệ.

Ưu tiên kiểm thử logic `core/` và nạp màn mà không cần khởi tạo giao diện Pygame.
Mỗi lỗi luật quan trọng nên có một trường hợp kiểm thử tái hiện.

### `build/` và `dist/` — bản đóng gói

- **`build/`**: Tệp trung gian do công cụ đóng gói tạo ra.
- **`dist/`**: Bản game có thể phân phối sau khi đóng gói.

Đây thường là thư mục sinh tự động, không phải nơi viết mã nguồn. Chỉ tạo nội
dung khi thiết lập quy trình đóng gói; không chỉnh sửa thủ công các tệp sinh ra.

## Trình tự hoàn thiện game

1. **Chốt luật và định dạng màn chơi**: Quy định cách biểu diễn tư thế khối,
   thao tác di chuyển, loại ô, công tắc, cầu và điều kiện thắng; thống nhất cấu
   trúc JSON cho các màn.
2. **Làm logic trước giao diện**: Cài đặt `block.py`, `board.py`, `movement.py`,
   `game_rules.py` và `game_state.py`. Viết kiểm thử cho di chuyển, va chạm, cơ
   chế và chiến thắng.
3. **Nạp và quản lý màn**: Cài đặt loader có kiểm tra dữ liệu, manager chuyển
   màn và tạo ít nhất một màn JSON có thể chơi từ đầu đến đích.
4. **Kết nối Pygame**: Tạo điểm khởi chạy GUI riêng, nhận phím, cập nhật trạng
   thái theo logic và vẽ bàn/khối.
5. **Hoàn thiện trải nghiệm**: Thêm menu, HUD, tạm dừng, màn kết quả, hoạt ảnh,
   âm thanh và tài nguyên đồ họa. Kiểm tra có thể bắt đầu lại và chuyển màn.
6. **Kiểm thử và đóng gói**: Chạy toàn bộ kiểm thử, thử chơi bằng bàn phím ở
   nhiều màn hình/kích thước cửa sổ, xử lý lỗi tài nguyên/dữ liệu, sau đó tạo
   bản phân phối trong `dist/`.

## Chạy và kiểm thử

Sau khi đã tạo `requirements.txt` và triển khai các file tương ứng:

```powershell
python -m pip install -r requirements.txt
python main.py
python main.py --test core
python main.py --test levels
python main.py --test gui
python main.py --test all
```

`python main.py` mở GUI. Tham số `--test` chọn nhóm kiểm thử; `all` chạy toàn
bộ suite. Có thể gọi trực tiếp `python -m pytest` để chạy cùng toàn bộ kiểm thử.

Nếu dự án chọn công cụ kiểm thử khác pytest, cập nhật lệnh và khai báo thư viện
trong `requirements.txt` cho nhất quán.

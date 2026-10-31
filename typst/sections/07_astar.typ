#import "../components.typ": styled_table, algorithm_box, callout_note, callout_warning

#pagebreak()

= Thuật toán A\* và hàm ước lượng

== Phạm vi thực hiện


Cài đặt A\*, xây dựng hàm ước
lượng (heuristic) và đánh giá lời giải trên đồ thị chuyển trạng thái do
phần lõi trò chơi cung cấp.

 A\* tối thiểu hóa tổng chi phí, không nhất thiết tối
thiểu số hành động. Chi phí được tính bằng `StepCost` trong
`solvers/common.py`. Hành động `SPACE` cũng được tính vào chuỗi lời giải
và có chi phí.

=== Đầu vào và đầu ra

Đầu vào gồm màn chơi `Level` và trạng thái bắt đầu `GameState`, có thể là
trạng thái ban đầu hoặc trạng thái hiện tại của người chơi. `GameState`
bất biến và có thể dùng làm khóa của bảng băm. Nó chứa thông tin về khối
và mặt nạ bit biểu diễn trạng thái các cầu. Thông tin khối gồm tư thế,
trạng thái tách, vị trí hai khối lập phương và khối đang được điều khiển.
Thuật toán dùng toàn bộ trạng thái làm khóa tìm kiếm.

Đầu ra là `SolverResult`, gồm chuỗi lời giải, trạng thái thành công, tổng
chi phí, số hành động, số lần mở rộng và các số đo thời gian, bộ nhớ.
Chuỗi lời giải dùng các ký hiệu `U`, `D`, `L`, `R`, `SPACE`. Nếu trạng thái
ban đầu đã thắng, chuỗi rỗng là lời giải hợp lệ có chi phí bằng 0.
Nếu hàng đợi tìm kiếm cạn, trường `path` là `None`, `solution_length` bằng
−1 và `cost` bằng vô cực.

=== Ranh giới giữa các thành phần

#styled_table(
  (1fr, 2.4fr),
  ([Thành phần], [Trách nhiệm]),
  (
    [`core/interfaces.py`], [Các kiểu trạng thái, màn chơi và kết quả dùng chung.],
    [`core/game_rules.py`], [Sinh trạng thái kế tiếp hợp lệ và kiểm tra đích.],
    [`solvers/common.py`], [Quy tắc tính chi phí và hàm đo thời gian, bộ nhớ.],
    [`solvers/astar.py`], [Quản lý tìm kiếm, hàm ước lượng và dựng lời giải.],
    [`ui/solver_bridge.py`], [Chạy thuật toán trong tiến trình riêng và trả kết quả về giao diện.],
  ),
  align: (left, left),
  caption: [Phân chia trách nhiệm trong chương trình hiện tại.],
)

#callout_note(title: [Phạm vi bảo đảm tính đúng])[
A\* không tự cài lại luật công tắc, cầu hay tách và ghép khối. Tính tối ưu
được xét trên đồ thị do phần lõi hiện tại cung cấp, với màn chơi giữ cố định
trong mỗi lần giải. Việc phát lại một lời giải hợp lệ qua phần lõi không
thay thế kiểm thử độc lập các luật trò chơi.
]


== Mô hình chi phí và cấu trúc dữ liệu

=== Quy tắc tính chi phí dùng chung

Gọi $s$ là trạng thái trước, $a$ là hành động và $t$ là trạng thái sau.
Chi phí chuyển trạng thái gồm chi phí chuyển động cơ sở, chi phí bổ sung
trên các ô đích và chi phí thay đổi trạng thái cầu:

$ c(s,a,t) = e(s,a,t) + sum_(x in C(t)) p(x) + b(s,t). $

Trong đó $C(t)$ là tập ô mà trạng thái đích chiếm, $e$ là chi phí chuyển
động cơ sở, $p$ là chi phí bổ sung trên mỗi ô và $b$ là chi phí thay đổi
trạng thái cầu. Đây là mô hình định lượng của chương trình, không phải
phép đo năng lượng vật lý. Các hằng số được giữ theo quy tắc tính chi phí
được chuyển từ UCS sang `common.py`.

#styled_table(
  (2.6fr, 1fr),
  ([Loại chuyển động], [Chi phí cơ sở]),
  (
    [Đứng → nằm hoặc kích hoạt tách khối từ tư thế đứng], [1.0],
    [Nằm → đứng, khi kết quả chưa tách], [1.5],
    [Nằm → nằm], [1.2],
    [Di chuyển từ trạng thái đã tách], [0.8],
    [`SPACE`: đổi khối lập phương đang điều khiển], [0.3],
  ),
  align: (left, center),
  caption: [Chi phí cơ sở của mỗi hành động.],
)

Chi phí bổ sung gồm 0.5 cho mỗi ô dễ vỡ bị chiếm, 0.3 cho mỗi ô cầu bị
chiếm, 0.1 cho mỗi ô đích kề khoảng trống theo phép kiểm tra bản đồ, và
0.5 nếu mặt nạ trạng thái cầu thay đổi. Phép kiểm tra kề khoảng trống xét
bốn hướng; các ô cầu vẫn được xem là một phần của cấu trúc bản đồ.
Chi phí trên các ô đích vẫn được tính cho `SPACE`, đúng theo cài đặt hiện
tại. Thuật toán chỉ tính chi phí cho các trạng thái kế tiếp đã được phần
lõi chấp nhận, không biến một nước đi thua thành nước đi hợp lệ.

Mọi chi phí bổ sung đều không âm, nên với quy tắc mặc định:

$ c(s,a,t) >= c_min = 0.3 > 0. $

`StepCost(level)` tính trước chi phí bổ sung của các ô một lần cho mỗi lần
giải. A\* có thể nhận hàm tính chi phí tùy chỉnh; nếu không truyền kèm hàm
ước lượng riêng, thuật toán mặc định dùng $h=0$. Cận dưới 0.3 chỉ áp dụng
cho quy tắc mặc định, không tự động áp dụng cho quy tắc khác.

=== Cấu trúc tìm kiếm

- *Hàng đợi ưu tiên:* dùng cấu trúc đống cực tiểu (min-heap), lưu các bộ
  `(f, counter, g, state)`.
- *Bảng chi phí tốt nhất:* `best_g[state]` lưu chi phí thấp nhất đã biết để
  tới một trạng thái.
- *Bảng cha:* `parents[state] = (previous_state, action)` dùng để dựng lời giải.
- *Bộ đếm thứ tự:* phân giải trường hợp hòa điểm theo thứ tự đưa vào hàng
  đợi, tránh phải so sánh trực tiếp các đối tượng trạng thái.

Không dùng riêng tọa độ làm khóa: hai trạng thái cùng vị trí nhưng khác
trạng thái cầu hoặc khối đang điều khiển có thể có các bước đi tiếp theo
khác nhau. Thuật toán không khóa vĩnh viễn trạng thái đã mở rộng, mà cho
phép xét lại khi tìm được đường đến có chi phí thấp hơn.

== Thuật toán A\* và cách tích hợp

=== Hàm ưu tiên

$ f(s) = g(s) + h(s). $

$g(s)$ là chi phí thực tế của đường từ trạng thái bắt đầu tới $s$; $h(s)$
là cận dưới của chi phí còn lại. Hàng đợi ưu tiên lấy phần tử có $f$ nhỏ
nhất. Nếu hòa $f$, phần tử được đưa vào trước được xét trước, theo bộ đếm
thứ tự và thứ tự sinh trạng thái kế tiếp của phần lõi.

=== Mã giả

#algorithm_box(
  [A\* trên đồ thị trạng thái với chi phí không đều],
  input: [Màn chơi cố định, trạng thái bắt đầu, hàm chi phí và hàm ước lượng không vượt chi phí còn lại.],
  output: [Lời giải có chi phí tối ưu, hoặc thông báo không có lời giải khi hàng đợi cạn.],
  steps: (
    [Chuẩn bị hàm chi phí; đặt `best_g[start] = 0`, cha của trạng thái bắt đầu là rỗng.],
    [Đưa `(h(start), counter, 0, start)` vào hàng đợi.],
    [Khi hàng đợi còn phần tử: lấy phần tử có ưu tiên nhỏ nhất.],
    [Bỏ qua phần tử nếu `g` không còn bằng `best_g[state]`.],
    [Tăng bộ đếm; nếu `is_goal(state, level)`, dựng lời giải và trả chi phí `g`.],
    [Xét từng cặp `(action, child)` từ `get_successors(state, level)`.],
    [Tính `new_g = g + cost(state, action, child, level)`.],
    [Nếu `new_g` nhỏ hơn chi phí tốt nhất của `child`, cập nhật chi phí và cha.],
    [Đưa `(new_g + h(child), counter, new_g, child)` vào hàng đợi, kể cả khi trạng thái đó đã mở rộng.],
    [Nếu hàng đợi cạn, trả kết quả không có lời giải.],
  ),
)

=== Loại phần tử cũ, mở lại trạng thái và điều kiện tối ưu

`heapq` không hỗ trợ giảm trực tiếp khóa ưu tiên của một phần tử đang có.
Vì vậy khi cải thiện $g$, thuật toán đưa thêm phần tử mới vào hàng đợi và
giữ phần tử cũ. Khi phần tử cũ được lấy ra, phép kiểm tra chi phí loại bỏ
nó mà không tăng `expanded_nodes`.

Thuật toán chấp nhận đích khi lấy một phần tử còn hiệu lực khỏi hàng đợi,
không phải ngay khi vừa sinh ra trạng thái đích. Việc mở lại trạng thái
cho phép sử dụng hàm ước lượng chấp nhận được nhưng chưa nhất quán.
Với chi phí dương hiện tại, hàm ước lượng không vượt chi phí còn lại và
đồ thị trạng thái hữu hạn, thuật toán tìm được lời giải có chi phí tối ưu
nếu lời giải tồn tại.

A\* kiểm tra chi phí và giá trị ước lượng hữu hạn, chi phí dương, giá trị
ước lượng không âm và bằng 0 tại đích. Các phép kiểm tra khi chạy không
chứng minh được tính chấp nhận được của hàm ước lượng tùy chỉnh; người
thiết kế hàm phải chứng minh điều kiện này.

=== Cách gọi từ chương trình

```python
from core.interfaces import GameState
from levels.level_loader import load_level
from solvers.astar import AStarSolver
from solvers.common import run_solver

level = load_level("level_01")
start = GameState(level.start, level.initial_bridge_mask)
result = run_solver(AStarSolver(), level, start)
```

`solve()` tạo `SolverResult`; `run_solver()` bổ sung số đo thời gian và
bộ nhớ. Trong giao diện, bộ kết nối chọn thuật toán và chạy hàm đo đạc
trong tiến trình riêng. Luồng giao diện nhận kết quả để phát lại lời giải.
Thao tác hủy hiện được thực hiện bằng cách dừng tiến trình tìm kiếm;
thuật toán chưa có giới hạn thời gian, số nút hoặc cơ chế nhận yêu cầu hủy
nội bộ. Các giao diện dự kiến trong tài liệu thiết kế không được xem là
tính năng đã triển khai.

== Thiết kế và chứng minh hàm ước lượng

=== Vì sao không dùng Manhattan cộng chi phí tư thế

Một lần lăn có thể làm tọa độ neo của khối dịch hơn một ô. Khi tách,
khối còn có thể dịch chuyển tức thời tới vị trí xa. Vì vậy khoảng cách
Manhattan từ tọa độ neo cộng một điểm cho tư thế nằm không mặc nhiên là
cận dưới. Bản này dùng mô hình nới lỏng xét cả các đường dịch chuyển tức
thời ngay khi trạng thái hiện tại chưa tách, như trình bày trong
`docs/astar-heuristic.md`.

=== Mô hình điểm và các điểm mốc

Thay khối bằng một điểm trên lưới không giới hạn. Mỗi bước trong mô hình
nới lỏng có chi phí 1 và đi tối đa 2 ô Manhattan, kể cả bước chéo (1,1).
Mô hình bỏ qua tư thế, khoảng trống, ô dễ vỡ, trạng thái cầu và điều kiện
kích hoạt công tắc. Mỗi công tắc tách khối có cạnh dịch chuyển tức thời
có hướng tới từng vị trí đích của nó, với chi phí bằng 0.

Khoảng cách di chuyển thông thường giữa hai điểm trong mô hình là:

$ w(p,q) = ceil((abs(p_1-q_1) + abs(p_2-q_2))/2). $

Chỉ giữ các điểm mốc gồm ô đích, vị trí công tắc tách khối và các vị trí
nhận khối sau khi tách. Nối mọi cặp bằng $w$, thêm cạnh dịch chuyển tức
thời với chi phí 0, rồi chạy Dijkstra trên đồ thị đảo từ ô đích.
Gọi $d(p)$ là khoảng cách từ điểm $p$ tới ô đích trong mô hình nới lỏng.
Với điểm bất kỳ, khoảng cách bằng giá trị nhỏ nhất của chi phí đi tới một
điểm mốc cộng khoảng cách còn lại của điểm mốc đó. Cách rút gọn này vẫn
xét mọi chuỗi dịch chuyển tức thời: một đường đi hoặc tới thẳng ô đích,
hoặc phải tới đầu của cạnh dịch chuyển tức thời đầu tiên.

Với $C(s)$ là tập một hoặc hai ô mà trạng thái thật đang chiếm, đặt:

$ H(s) = min_(p in C(s)) d(p), quad h(s) = 0.3 H(s). $

Khi đã tách, phép lấy giá trị nhỏ nhất xét cả hai khối lập phương, không
chỉ khối đang điều khiển. Một trạng thái chưa thắng vẫn có thể có $h=0$,
chẳng hạn khối nằm đè lên ô đích; đây vẫn là cận dưới hợp lệ.

=== Chứng minh tính nhất quán và tính chấp nhận được

Tính nhất quán yêu cầu $h(s) <= c(s,a,t)+h(t)$ trên mỗi cạnh hợp lệ.
Tính chấp nhận được yêu cầu hàm ước lượng không vượt quá chi phí tối ưu
còn lại. Xét cạnh thật $s -> t$ có chi phí $c(s,a,t)$. Chọn ô $q$ thuộc
$C(t)$ sao cho $d(q)=H(t)$. Có một ô $p$ thuộc $C(s)$ với đường đi tới $q$
trong mô hình nới lỏng có chi phí tối đa 1:

- *Lăn khối:* theo bảng chuyển tư thế, mỗi ô mới cách ít nhất một ô cũ
  không quá 2 đơn vị Manhattan.
- *Di chuyển khối lập phương:* khối đang điều khiển dịch 1 ô, khối còn
  lại đứng yên.
- *Đổi điều khiển bằng SPACE:* tập ô không đổi nên có thể mô phỏng bằng
  đường đi có chi phí 0.
- *Ghép khối:* tập ô sau ghép trùng với tập ô của hai khối lập phương
  sau chuyển động.
- *Tách và dịch chuyển tức thời:* từ ô cũ tới công tắc trong tối đa một
  bước nới lỏng, rồi tới vị trí nhận khối với chi phí 0.
- *Cầu và công tắc:* thay đổi mặt nạ trạng thái không ảnh hưởng đến
  lập luận vì mô hình bỏ các ràng buộc cản đường.

Suy ra $H(s) <= d(p) <= 1+d(q) = 1+H(t)$. Vì chi phí thật ít nhất 0.3:

$ h(s) <= 0.3 + h(t) <= c(s,a,t) + h(t). $

Vậy hàm ước lượng nhất quán theo quy tắc chi phí hiện tại. Mọi chi phí
trong mô hình nới lỏng không âm nên $h(s)>=0$; tại trạng thái đích, tập ô
chỉ chứa ô đích nên giá trị ước lượng bằng 0. Cộng bất đẳng thức nhất quán
dọc một đường tới đích cho thấy giá trị ước lượng không lớn hơn chi phí
của đường đó. Do đó hàm cũng chấp nhận được.

=== Chi phí tính toán và giới hạn

Với $K$ điểm mốc, đồ thị đầy đủ có $O(K^2)$ cạnh. Cài đặt Dijkstra với
hàng đợi ưu tiên dùng khoảng $O(K^2 log K)$ thời gian tiền xử lý. Bộ nhớ
đệm lưu $O(K)$ khoảng cách cho mỗi cấu hình; hàng đợi tạm có thể chứa
$O(K^2)$ phần tử. Mỗi lần đánh giá xét tối đa hai ô đang chiếm và $K$ điểm
mốc, cộng chi phí tạo khóa từ các công tắc tách khối. Bộ nhớ đệm LRU giữ
tối đa 32 cấu hình ô đích và các cạnh dịch chuyển tức thời.

#callout_warning(title: [Giới hạn của hàm ước lượng])[
Hàm ước lượng bỏ nhiều ràng buộc nên có thể yếu khi lời giải cần phối hợp
hai khối lập phương hoặc mở cầu. Không bảo đảm luôn giảm số nút hay thời
gian so với $h=0$. Khi quy tắc chi phí thay đổi, phải cập nhật cận dưới
và chứng minh lại; không tự động dùng hệ số 0.3 cho mọi quy tắc tùy chỉnh.
]

== Thực nghiệm và đánh giá

#let all_records = csv("../data/all_algorithms.csv", row-type: dictionary)
#let records = all_records.filter(row => row.algorithm == "A*")
#assert(records.len() == 11)
#assert(records.filter(row => row.cost == "").len() == 0)
#let environment = json("../data/all_algorithms_environment.json")

=== Mục tiêu và cách bố trí thực nghiệm

Script `typst/collect_all_results.py` chạy A\* trên cùng 11 level và từ
cùng trạng thái đầu như BFS, DFS và UCS. Mỗi solver được khởi động một
lần không ghi nhận, sau đó đo thời gian
#environment.repeats_per_level_algorithm lần; thứ tự thuật toán được
xoay vòng giữa các lượt. Bảng dùng trung vị và độ lệch chuẩn mẫu của thời
gian; bộ nhớ đỉnh được đo riêng một lần cho mỗi level.

Mọi đường đi được phát lại bằng `apply_move`; collector kiểm tra tính hợp
lệ, độ dài, đích đến và tổng `StepCost`. Chi phí A\* được đối chiếu với
UCS trên từng level. Môi trường thu thập: Python #environment.python trên
#raw(environment.platform); tổng số lượt đo là #environment.total_solver_runs.
CSV tổng hợp, dữ liệu thô và mã băm nguồn nằm trong `data/`.

=== Cách đo thời gian và bộ nhớ

Thời gian được đo bằng `perf_counter()` quanh `solve()` khi
`tracemalloc` tắt; cùng một cách đo được dùng cho cả bốn solver. Trước
mỗi lần A\* chạy, bộ nhớ đệm heuristic được xóa để các lượt đo có điều
kiện tương đương. Thu gom rác và phát lại lời giải nằm ngoài khoảng đo.
Lượt đo bộ nhớ chạy riêng với `tracemalloc`.

Bộ nhớ là đỉnh cấp phát do `tracemalloc` ghi nhận, không phải toàn
bộ RAM tiến trình. Trường `peak_memory_kb_median` là trung vị số KB qua
các lần đo. Độ lệch chuẩn thời gian được báo để thể hiện mức dao động.

=== Kiểm chứng lời giải và số nút mở rộng

Ngoài khoảng đo, chương trình xác minh kết quả của cả bốn thuật toán.
Mỗi nước đi phải hợp lệ, trạng thái cuối phải thỏa `is_goal`, độ dài phải
khớp với số hành động và tổng chi phí UCS/A\* phải khớp `StepCost`. Kết
quả lời giải và số nút phải ổn định qua các lần đo; sai lệch làm collector
dừng và không ghi bộ dữ liệu tổng hợp mới.

#styled_table(
  (1fr, 1fr, 0.65fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr, 0.8fr),
  ([Màn], [Nhóm], [Giải được], [Bước], [Chi phí], [Thời gian trung vị (ms)], [ĐLC thời gian (ms)], [Bộ nhớ đỉnh (KB)], [Nút mở rộng]),
  records.map(row => (
    [#row.level], [#row.group],
    if row.success == "True" [Có] else [Không],
    [#row.solution_length],
    [#calc.round(float(row.cost), digits: 2)],
    [#calc.round(float(row.time_ms_median), digits: 3)],
    [#calc.round(float(row.time_ms_stdev), digits: 3)],
    [#calc.round(float(row.peak_memory_kb_median), digits: 1)],
    [#row.expanded_nodes],
  )).flatten(),
  inset: 2pt,
  align: (left, left, center, right, right, right, right, right, right),
  caption: [Kết quả A\* trên cùng bộ level; thời gian là trung vị qua #environment.repeats_per_level_algorithm lượt đo, bộ nhớ đo riêng một lượt.],
)

=== Biểu đồ và nhận xét

#figure(
  image("../figures/astar_overview.png", width: 100%),
  caption: [Thời gian, bộ nhớ đỉnh, số nút mở rộng và độ dài lời giải của A\* theo level.],
)

A\* tối ưu tổng `StepCost`, không nhất thiết tối ưu số bước; do đó độ
dài lời giải cần được diễn giải cùng chi phí và đối chiếu với BFS/UCS,
không dùng riêng để xếp hạng chất lượng. Việc mở rộng ít nút hơn cũng
không bảo đảm thời gian thấp hơn vì A\* còn tính heuristic và quản lý bộ
nhớ đệm.

#callout_note(title: [Phạm vi kết quả])[
Số liệu mô tả các level trong thư mục `levels/`, trạng thái bắt đầu mặc
định, mã nguồn và môi trường ghi trong metadata. Không suy rộng kết quả
thành khẳng định A\* luôn nhanh hơn hoặc dùng ít bộ nhớ hơn trên mọi màn.
]

Benchmark không giới hạn thời gian hay số nút; collector dừng nếu solver
lỗi, kết quả không ổn định, replay sai hoặc chi phí A\* khác UCS. BFS tối
ưu số hành động, còn UCS và A\* tối ưu tổng `StepCost`; vì vậy không so
sánh chất lượng lời giải chỉ bằng số bước.

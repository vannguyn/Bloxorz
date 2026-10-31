#import "../../components.typ": styled_table, callout_note

= Thực nghiệm BFS

== Thiết lập

BFS chạy trên cùng bộ màn chơi do `load_all_levels()` nạp, với trạng thái đầu `GameState(level.start, level.initial_bridge_mask)`. Các số liệu được đo như sau:

- *Thời gian tìm kiếm*: `time.perf_counter()`, lấy trung bình và độ lệch chuẩn qua nhiều lần chạy, *không* bật `tracemalloc` (vì `tracemalloc` làm chương trình chậm đi đáng kể).
- *Bộ nhớ đỉnh*: `tracemalloc.get_traced_memory()`, đo ở một lần chạy riêng (hàm `run_solver` trong `solvers/common.py`).
- *Số nút mở rộng*: số trạng thái được lấy ra khỏi hàng đợi và sinh trạng thái con. Nút đích được phát hiện lúc sinh nên không được tính là đã mở rộng.
- *Số bước di chuyển*: độ dài đường đi trả về; hành động `SPACE` tính là một bước.

#text(fill: red)[*(CẦN BỔ SUNG)* Mô tả các nhóm màn chơi (cơ bản, có ô dễ vỡ, có công tắc/cầu, có công tắc tách) và màn nào thuộc nhóm nào; cấu hình máy (CPU, RAM, hệ điều hành, phiên bản Python); số lần lặp đã dùng khi đo thời gian.]

== Kết quả

#let rows = csv("../../data/bfs_results.csv").slice(1)
#let data = rows.map(r => (
  r.at(0),
  if r.at(1) == "True" [Có] else [Không],
  r.at(2), r.at(3), r.at(4), r.at(5), r.at(6),
)).flatten()

#styled_table(
  (auto,) * 7,
  ("Màn", "Tìm được", "Thời gian TB (ms)", "Độ lệch chuẩn (ms)", "Bộ nhớ đỉnh (KB)", "Nút mở rộng", "Độ dài lời giải"),
  data,
  caption: [Kết quả của BFS trên bộ màn chơi thử nghiệm.],
)

#figure(
  image("../../figures/bfs_overview.png", width: 100%),
  caption: [Thời gian, bộ nhớ đỉnh, số nút mở rộng và độ dài lời giải của BFS theo từng màn (dùng thang log khi giá trị trải rộng).],
)

== Nhận xét

BFS giải được cả 11 màn và luôn cho lời giải ngắn nhất (từ 7 đến 55 bước), đúng với lý thuyết khi mọi hành động có chi phí 1.

Ở các màn nhỏ (`level_01` đến `level_07`), BFS mở rộng từ 20 đến 52 nút, mất khoảng 0,3 đến 0,6 ms và 7 đến 17 KB bộ nhớ. Ở mức này, bộ nhớ chủ yếu phản ánh chi phí cố định của Python nên chênh lệch giữa các màn không có nhiều ý nghĩa.

Tài nguyên tăng nhanh theo độ khó. `level_08`, `level_09` và `level_10` lần lượt mở rộng 292, 887 và 2864 nút (5,1; 17,2 và 60,7 ms; 125, 333 và 1060 KB). `level_11` là màn lớn nhất: BFS mở rộng 25815 nút, mất khoảng 585 ms và 10552 KB, với lời giải 55 bước.

Dù độ sâu lời giải của `level_11` là 55, số nút mở rộng vẫn nhỏ hơn rất nhiều so với $b^d$, cho thấy tập trạng thái đã thăm loại bỏ được phần lớn trạng thái trùng. Nhược điểm của BFS là phải giữ toàn bộ biên tìm kiếm trong bộ nhớ nên chi phí tăng theo kích thước không gian trạng thái. So sánh với DFS được trình bày trong phần DFS.

#text(fill: red)[*(CẦN BỔ SUNG)* Nhận xét thêm theo nhóm màn (ví dụ màn có công tắc tách có làm số nút tăng đột biến không) sau khi đã xác định màn nào thuộc nhóm nào.]

== Kết luận

BFS phù hợp khi cần lời giải ít bước nhất và không gian trạng thái ở mức vừa phải. Điểm mạnh là tính tối ưu và hiệu năng ổn định; điểm yếu là bộ nhớ tăng nhanh ở các màn lớn (10552 KB ở `level_11`).

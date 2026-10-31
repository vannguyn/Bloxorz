#import "../../components.typ": styled_table, callout_warning

= Thực nghiệm DFS

== Thiết lập

DFS chạy trên cùng bộ màn chơi do `load_all_levels()` nạp, với trạng thái đầu `GameState(level.start, level.initial_bridge_mask)`. Các số liệu được đo như sau:

- *Thời gian tìm kiếm*: `time.perf_counter()`, lấy trung bình và độ lệch chuẩn qua nhiều lần chạy, *không* bật `tracemalloc`.
- *Bộ nhớ đỉnh*: `tracemalloc.get_traced_memory()`, đo ở một lần chạy riêng (hàm `run_solver` trong `solvers/common.py`).
- *Số nút mở rộng*: số trạng thái được lấy ra khỏi ngăn xếp và thực sự được mở rộng; các bản sao bị bỏ qua và nút đích không được tính.
- *Số bước di chuyển*: độ dài đường đi trả về; hành động `SPACE` tính là một bước.

#text(fill: red)[*(CẦN BỔ SUNG)* Mô tả các nhóm màn chơi (cơ bản, có ô dễ vỡ, có công tắc/cầu, có công tắc tách) và màn nào thuộc nhóm nào; cấu hình máy (CPU, RAM, hệ điều hành, phiên bản Python); số lần lặp đã dùng khi đo thời gian.]

== Kết quả

#let rows = csv("../../data/dfs_results.csv").slice(1)
#let data = rows.map(r => (
  r.at(0),
  if r.at(1) == "True" [Có] else [Không],
  r.at(2), r.at(3), r.at(4), r.at(5), r.at(6),
)).flatten()

#styled_table(
  (auto,) * 7,
  ("Màn", "Tìm được", "Thời gian TB (ms)", "Độ lệch chuẩn (ms)", "Bộ nhớ đỉnh (KB)", "Nút mở rộng", "Độ dài lời giải"),
  data,
  caption: [Kết quả của DFS trên bộ màn chơi thử nghiệm.],
)

#figure(
  image("../../figures/dfs_overview.png", width: 100%),
  caption: [Thời gian, bộ nhớ đỉnh, số nút mở rộng và độ dài lời giải của DFS theo từng màn (dùng thang log khi giá trị trải rộng).],
)

== Nhận xét

*Khả năng giải.* DFS giải được cả 11 màn nhờ tập trạng thái đã thăm giúp tránh chu trình.

*Độ dài lời giải.* Lời giải của DFS rất không đều và có thể dài bất thường: từ 9 đến 35 bước ở các màn nhỏ (`level_01` đến `level_07`), lên 19, 101 và 710 bước ở `level_08`, `level_09`, `level_10`, và đạt 95212 bước ở `level_11`. Điều này đúng với bản chất của DFS: nó trả về lời giải hợp lệ đầu tiên gặp được trên nhánh đang đi sâu, không bảo đảm ngắn nhất.

*Các màn nhỏ (`level_01` đến `level_07`).* DFS mở rộng từ 43 đến 62 nút, mất khoảng 0,5 đến 0,9 ms và 11 đến 19 KB bộ nhớ đỉnh. Ở mức này, bộ nhớ chủ yếu phản ánh chi phí cố định của Python nên chênh lệch giữa các màn không có nhiều ý nghĩa.

*Các màn trung bình (`level_08` đến `level_10`).* Số nút mở rộng là 43, 168 và 769, thời gian lần lượt khoảng 0,7; 3,1 và 16,2 ms, bộ nhớ đỉnh 16, 67 và 485 KB. Tài nguyên còn nhỏ, nhưng lời giải dài ra rõ rệt (19, 101 và 710 bước).

*Màn lớn nhất (`level_11`).* DFS mất khoảng 3099 ms, mở rộng 107660 nút và dùng 97663 KB, với lời giải dài 95212 bước. Số bước này chiếm khoảng 88% số nút đã mở rộng, nghĩa là DFS đi theo một nhánh rất dài gần như không quay lui. Vì bản cài đặt lưu `came_from` cho mọi trạng thái đã thăm nên bộ nhớ vẫn tăng theo số nút đã khám phá, không tiết kiệm như DFS dạng cây trên lý thuyết.

*Tính ổn định.* Kết quả của DFS phụ thuộc vào thứ tự hành động mà `get_successors` trả về (`U, D, L, R`) và vào hình dạng của màn. Hai màn có cùng kích thước không gian trạng thái nhưng bố cục khác nhau có thể cho độ dài lời giải rất khác nhau.

#callout_warning[
  DFS chỉ cho một lời giải hợp lệ, không bảo đảm ngắn nhất, và hiệu năng không ổn định giữa các màn. Vì vậy không nên dùng DFS khi cần đường đi ngắn.
]

#text(fill: red)[*(CẦN BỔ SUNG)* Nếu có thời gian, chạy lại DFS với thứ tự hành động khác (ví dụ `R, L, D, U`) và ghi lại kết quả để kiểm chứng nhận định về tính ổn định ở trên; nhận xét thêm theo nhóm màn sau khi xác định màn nào thuộc nhóm nào.]

== Kết luận

DFS giải được cả 11 màn nhưng lời giải thường dài và không đều (từ 9 bước đến 95212 bước ở `level_11`). Ở màn lớn nhất, DFS tốn khoảng 3099 ms và 97663 KB. DFS phù hợp khi chỉ cần một lời giải hợp lệ và không quan tâm đến độ dài; không phù hợp khi cần đường đi ngắn.

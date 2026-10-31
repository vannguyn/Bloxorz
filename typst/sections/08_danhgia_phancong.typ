#import "../components.typ": styled_table

#pagebreak()

= Đánh giá và phân công

== Tổng hợp kết quả

#let summary = csv("../data/algorithm_summary.csv", row-type: dictionary)
#let environment = json("../data/all_algorithms_environment.json")

#figure(
  caption: [Mục tiêu tối ưu và phạm vi số liệu của từng thuật toán],
  table(
    columns: (1fr, 1.5fr, 1fr, 2fr),
    align: (left, left, center, left),
    table.header([*Thuật toán*], [*Mục tiêu tối ưu*], [*Số màn trong bảng riêng*], [*Nội dung thực nghiệm*]),
    [BFS], [Số hành động], [#environment.level_count], [Thời gian, bộ nhớ đỉnh, nút mở rộng, độ dài lời giải.],
    [DFS], [Không bảo đảm tối ưu], [#environment.level_count], [Thời gian, bộ nhớ đỉnh, nút mở rộng, độ dài lời giải.],
    [UCS], [Tổng chi phí `StepCost`], [#environment.level_count], [Thời gian, bộ nhớ đỉnh, nút mở rộng, độ dài lời giải và chi phí.],
    [A\*], [Tổng chi phí `StepCost`], [#environment.level_count], [Thời gian, bộ nhớ đỉnh, nút mở rộng, độ dài lời giải và chi phí.],
  ),
) <tab:algorithm_scope>

== So sánh định lượng trên cùng bộ level

Collector đã chạy #environment.algorithms.len() thuật toán trên
#environment.level_count level, với #environment.repeats_per_level_algorithm
lần đo thời gian cho mỗi cặp level/solver (tổng cộng #environment.timed_runs
lần đo thời gian), và một lần đo bộ nhớ riêng cho mỗi cặp
(#environment.memory_runs lần). Mỗi lời giải được kiểm tra bằng replay;
chi phí UCS và A\* được đối chiếu trên từng màn.

#styled_table(
  (1fr, 0.9fr, 0.9fr, 1fr, 1fr, 1fr, 1fr),
  ([Thuật toán], [Giải được], [Tổng level], [Thời gian trung vị (ms)], [Bộ nhớ đỉnh trung vị (KB)], [Nút mở rộng trung vị], [Độ dài lời giải trung vị]),
  summary.map(row => (
    [#row.algorithm], [#row.solved_levels], [#row.total_levels],
    [#calc.round(float(row.median_time_ms), digits: 3)],
    [#calc.round(float(row.median_peak_memory_kb), digits: 1)],
    [#calc.round(float(row.median_expanded_nodes), digits: 1)],
    [#calc.round(float(row.median_solution_length), digits: 1)],
  )).flatten(),
  inset: 3pt,
  caption: [Trung vị theo level của bốn chỉ số thực nghiệm; chi tiết từng level nằm trong mục của mỗi thuật toán.],
)

#figure(
  image("../figures/algorithm_comparison.png", width: 100%),
  caption: [So sánh BFS, DFS, UCS và A\* theo thời gian, bộ nhớ đỉnh, nút mở rộng và độ dài lời giải trên cùng các level.],
)

Các nhóm test được xác định từ dữ liệu level: cơ bản (không có ô dễ vỡ
hay công tắc), ô dễ vỡ, công tắc/cầu, và kết hợp. Biểu đồ dùng thang
logarit khi dải số liệu đủ rộng; vì vậy khi đọc cần xem nhãn trục. Trung
vị ở bảng tổng hợp là trung vị của các trung vị theo từng level, không
phải trung bình có trọng số theo độ khó.

== Kiểm chứng và giới hạn

Các lời giải được kiểm tra bằng cách phát lại hành động qua luật trò chơi,
kiểm tra trạng thái đích, và đối chiếu tổng chi phí với `StepCost` đối với
UCS/A\*. Kiểm thử tự động của dự án bao phủ luật lõi, giao diện và hợp đồng
solver; kết quả không thay thế việc kiểm tra độc lập từng cơ chế trong
màn chơi.

BFS trả lời bài toán ít bước nhất, còn UCS/A\* trả lời bài toán chi phí
thấp nhất. Vì vậy không dùng riêng độ dài lời giải để kết luận UCS/A\*
tốt hơn hoặc kém hơn BFS. DFS là thuật toán đầy đủ trên không gian hữu
hạn có tập trạng thái đã thăm, nhưng không bảo đảm tối ưu và hiệu năng
phụ thuộc thứ tự successor. Kết luận so sánh chỉ áp dụng cho các level,
trạng thái đầu, mã nguồn, số lần lặp và môi trường ghi trong tệp metadata.

== Phân công và tự đánh giá

Danh sách thành viên:

#figure(
  caption: [Bảng xác nhận phân công và tỷ lệ đóng góp của nhóm],
  table(
    columns: (auto, auto, 2.2fr, 0.5fr),
    align: (center, left, left),
    table.header([*STT*], [*Thành viên*], [*Nhiệm vụ được nhóm xác nhận*], [*Tỷ lệ*]),
    [1], [Nguyễn Ngọc Quang — 24120127], [Xây dựng giao diện người dùng (GUI), xử lý đầu vào], [100%],
    [2], [Lương Nhật Tân — 24120134], [Cài đặt thuật toán BFS/DFS, đánh giá thuật toán và viết báo cáo về thuật toán BFS/DFS], [100%],
    [3], [Nguyễn Gia Hưng — 24120185], [Cài đặt thuật toán UCS, đánh giá thuật toán và viết báo cáo về thuật toán UCS], [100%],
    [4], [Võ Nhật Minh — 24120202], [Cài đặt thuật toán A\*, heuristic, đánh giá thuật toán và viết báo cáo về thuật toán A\*], [100%],
    [5], [Trần Văn Nguyên — 24120205], [Xây dựng logic cho game,  interface để kết nối GUI với các thuật toán], [100%],
  ),
) <tab:contributions>

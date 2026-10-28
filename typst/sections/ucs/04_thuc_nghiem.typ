#import "../../components.typ": styled_table, callout_note

= Thực nghiệm

#let records = csv("../../data/ucs_results.csv", row-type: dictionary)

== Cách bố trí

Chương trình `typst/collect_ucs_results.py` chạy hai cấu hình trên các màn
`level_01` đến `level_10` trong thư mục `levels/`:

- *UCS:* `UCSSolver` với chi phí `StepCost` (bản được nộp).
- *UCS chi phí 1:* lớp con ghi đè `step_cost` trả về 1 cho mọi nước đi. Cấu
  hình này có thứ tự mở rộng như BFS, dùng làm đối chứng để thấy ảnh hưởng
  của hàm chi phí.

Mỗi cấu hình chạy thử một lần không ghi nhận, sau đó đo 5 lần qua
`run_solver()` (cùng hàm đo với giao diện); bảng lấy trung vị thời gian và
bộ nhớ. Thời gian đo bằng `perf_counter()` quanh `solve()`, bộ nhớ là mức
cấp phát Python cao nhất theo `tracemalloc`. Vì `tracemalloc` theo dõi từng
lần cấp phát, thời gian đo được cao hơn thời gian chạy thuần nhiều lần;
ảnh hưởng này như nhau cho cả hai cấu hình. Môi trường: Python 3.11.7 trên
Linux x86-64.

Mỗi lời giải được phát lại bằng `apply_move`: mọi hành động phải hợp lệ,
trạng thái cuối phải thỏa `is_goal`, và tổng chi phí tính lại phải bằng
chi phí thuật toán báo cáo. Kết quả của 5 lần đo phải trùng nhau. Tất cả
các màn đều qua các phép kiểm tra này.

== Kết quả

#styled_table(
  (1.1fr, 0.6fr, 0.75fr, 0.8fr, 0.9fr, 0.85fr),
  ([Màn], [Bước], [Chi phí], [Số nút], [Thời gian (ms)], [Bộ nhớ (KB)]),
  records.map(row => (
    [#row.level], [#row.steps],
    [#calc.round(float(row.cost), digits: 2)],
    [#row.nodes], [#row.time_ms], [#row.memory_kb],
  )).flatten(),
  inset: 4pt,
  align: (left, right, right, right, right, right),
  caption: [Kết quả UCS với chi phí `StepCost` (trung vị 5 lần đo).],
)

#styled_table(
  (1.1fr, 0.8fr, 0.8fr, 1fr, 1fr, 0.8fr, 0.8fr),
  ([Màn], [Bước UCS], [Bước chi phí 1], [Chi phí UCS], [Chi phí đường chi phí 1], [Nút UCS], [Nút chi phí 1]),
  records.map(row => (
    [#row.level], [#row.steps], [#row.unit_steps],
    [#calc.round(float(row.cost), digits: 2)],
    [#calc.round(float(row.unit_cost_stepcost), digits: 2)],
    [#row.nodes], [#row.unit_nodes],
  )).flatten(),
  inset: 4pt,
  align: (left, right, right, right, right, right, right),
  caption: [So sánh với cấu hình chi phí 1. Cột "chi phí đường chi phí 1" là
    chi phí `StepCost` của lời giải mà cấu hình chi phí 1 tìm được.],
)

Số nút là số trạng thái được lấy khỏi hàng đợi và mở rộng, kể cả trạng
thái đích; không tính phần tử cũ bị bỏ qua.

== Nhận xét

- *UCS giải được cả 10 màn.* Lời giải được kiểm chứng bằng luật chơi và có
  chi phí nhỏ nhất theo `StepCost`.
- *Hàm chi phí thay đổi lời giải.* Ở `level_10`, UCS chọn đường 18 bước
  với chi phí 24.5, trong khi đường ngắn nhất 17 bước có chi phí 25.2.
  Ở `level_02`, hai cấu hình cùng 9 bước nhưng UCS chọn đường có chi phí
  13.1 thay vì 13.2. Ở các màn còn lại, đường ngắn nhất cũng là đường rẻ
  nhất.
- *Các màn có công tắc tách tốn kém nhất.* `level_08`–`level_10` mở rộng
  hàng nghìn nút, gấp hàng chục lần các màn khác: sau khi tách, vị trí hai
  khối lập phương cùng khối đang điều khiển làm số trạng thái tăng mạnh.
- *Chi phí không đều làm UCS mở rộng nhiều nút hơn.* Trên ba màn có công
  tắc tách, UCS mở rộng khoảng 1.25–2.8 lần số nút của cấu hình chi phí 1.
  Nước đi của khối lập phương (0.8) và `SPACE` (0.3) rẻ hơn nước đi của khối
  nguyên, nên UCS khám phá rất nhiều tổ hợp khối lập phương trước khi xét
  đường dài hơn của khối nguyên. Đây là cái giá của việc tối ưu theo chi
  phí thay vì số bước. Trên các màn không có công tắc tách, số nút của hai
  cấu hình gần như nhau.

#callout_note(title: [Hạn chế])[
  UCS không biết đích nằm ở đâu nên lan đều theo mọi hướng. Để giảm số nút
  cần một hàm ước lượng chấp nhận được, tức là chuyển sang A\*. Thuật toán
  cũng chưa có giới hạn thời gian hay số nút; trong giao diện, việc hủy
  được thực hiện bằng cách dừng tiến trình tìm kiếm.
]

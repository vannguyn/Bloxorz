#import "../components.typ": styled_table, callout_note, callout_warning

= Thực nghiệm và đánh giá

#let records = csv("../data/validation.csv", row-type: dictionary)
#let environment = json("../data/environment.json")

== Mục tiêu và cách bố trí thực nghiệm

Chương trình `typst/collect_results.py` so sánh A\* mặc định với cùng bản
cài đặt dùng $h=0$. Phương án $h=0$ ưu tiên trạng thái có chi phí tích lũy
nhỏ nhất; đây là phương án đối chứng có thứ tự tìm kiếm như UCS, không
phải bản cài đặt UCS độc lập. Cả hai dùng cùng `StepCost`, cùng màn chơi
và trạng thái bắt đầu. Mục tiêu là kiểm tra tính hợp lệ của lời giải,
đối chiếu chi phí và đo ảnh hưởng của hàm ước lượng tới tài nguyên tìm kiếm.

Các màn `level_01` đến `level_10` được đọc trực tiếp từ thư mục `levels/`.
Mỗi cấu hình được chạy thử một lần không ghi nhận số đo, rồi đo
#environment.repeats lần. Hai cấu hình chạy tuần tự và đổi thứ tự qua các
lần lặp để giảm ảnh hưởng của thứ tự chạy. Mỗi lần dùng một đối tượng
thuật toán mới. Bảng báo cáo lấy trung vị riêng của từng chỉ số theo màn
và cấu hình, không lấy số đo của một lần chạy duy nhất.

Môi trường thu thập: Python #environment.python trên
#raw(environment.platform). Tổng số lần đo là #environment.measured_runs.
Tệp `data/environment.json` lưu cách đo, phiên bản môi trường và mã băm
SHA-256 của chương trình thu thập, mã nguồn thuật toán, phần lõi và các màn.
Tệp `data/raw_runs.csv` giữ số liệu từng lần; `data/validation.csv` giữ số
liệu tổng hợp dùng trong các bảng dưới. Cần thu thập lại sau khi thay mã nguồn.

== Cách đo thời gian và bộ nhớ

Cả hai cấu hình đều gọi `run_solver()` trong `solvers/common.py`, cùng
hàm đo mà giao diện sử dụng. Thời gian được đo bằng `perf_counter()` quanh
`solve()`, theo đơn vị mili giây. Khoảng đo bao gồm tiền xử lý chi phí,
xây dựng dữ liệu hàm ước lượng phát sinh trong lần giải và dựng lời giải;
không gồm đọc màn, thu gom rác trước khi chạy, vẽ giao diện hay phát lại.

Trước mỗi lần đo, chương trình xóa bộ nhớ đệm của hàm ước lượng. Do đó
số liệu A\* bao gồm chi phí khởi tạo bộ nhớ đệm trong lần giải đó. Bộ nhớ
đệm chỉ số cầu của phần lõi được chuẩn bị trước cho cả hai cấu hình.
Chương trình gọi thu gom rác trước mỗi lần đo; cơ chế thu gom tự động
của Python vẫn hoạt động khi thuật toán chạy.

Bộ nhớ được ghi nhận bằng `tracemalloc.get_traced_memory()[1]`, là mức
cấp phát Python cao nhất trong lần giải. `run_solver()` chia số byte cho
1024 và lấy phần nguyên; bảng giữ nhãn KB theo trường dữ liệu hiện tại.
Đây không phải toàn bộ bộ nhớ của tiến trình hay mức dùng RAM của trò chơi.
Mỗi lần có một phiên đo riêng, không chạy chồng các phép đo trong cùng
tiến trình. Việc theo dõi cấp phát có thể làm tăng thời gian chạy, và
ảnh hưởng đó áp dụng cho cả hai cấu hình.

== Kiểm chứng lời giải và số nút mở rộng

Ngoài khoảng đo, chương trình phát lại từng lời giải bằng `apply_move`,
kiểm tra từng hành động hợp lệ, trạng thái cuối thỏa `is_goal` và tổng
chi phí tính lại khớp kết quả. Tính ổn định của kết quả qua các lần lặp
cũng được kiểm tra. Nếu có sai lệch hoặc lỗi thực thi, chương trình dừng
và không công bố bộ CSV mới chưa hoàn tất.

#styled_table(
  (1.1fr, 0.55fr, 0.85fr, 0.85fr, 0.85fr, 0.85fr),
  ([Màn], [Bước A\*], [Chi phí A\*], [Chi phí h=0], [Nút A\*], [Nút h=0]),
  records.map(row => (
    [#row.level], [#row.actions],
    [#calc.round(float(row.cost_astar), digits: 2)],
    [#calc.round(float(row.cost_h0), digits: 2)],
    [#row.expanded_astar], [#row.expanded_h0],
  )).flatten(),
  inset: 4pt,
  align: (left, right, right, right, right, right),
  caption: [Đối chiếu chi phí và số nút mở rộng.],
)

Số nút là số lần lấy phần tử còn hiệu lực khỏi hàng đợi, gồm đích và các
lần mở lại trạng thái; không đếm phần tử cũ bị bỏ qua. Hai cấu hình cho
cùng chi phí trên các màn đã xét, và lời giải đều được phát lại hợp lệ.
Cột số bước chỉ ghi lời giải A\*: số bước của phương án đối chứng có thể
khác khi tồn tại nhiều đường có cùng chi phí.

== Kết quả thời gian và bộ nhớ

#styled_table(
  (1.05fr, 1fr, 1fr, 1fr, 1fr),
  ([Màn], [A\* (ms)], [h=0 (ms)], [A\* (KB)], [h=0 (KB)]),
  records.map(row => (
    [#row.level],
    [#calc.round(float(row.time_ms_astar), digits: 3)],
    [#calc.round(float(row.time_ms_h0), digits: 3)],
    [#calc.round(float(row.memory_kb_astar), digits: 1)],
    [#calc.round(float(row.memory_kb_h0), digits: 1)],
  )).flatten(),
  inset: 5pt,
  align: (left, right, right, right, right),
  caption: [Trung vị thời gian và bộ nhớ đỉnh qua #environment.repeats lần đo mỗi cấu hình.],
)

#let fewer_nodes = records.filter(row => int(row.expanded_astar) < int(row.expanded_h0)).len()
#let faster = records.filter(row => float(row.time_ms_astar) < float(row.time_ms_h0)).len()
#let less_memory = records.filter(row => float(row.memory_kb_astar) < float(row.memory_kb_h0)).len()

Trong đợt đo này, A\* mở rộng ít nút hơn trên #fewer_nodes/#records.len()
màn, có trung vị thời gian thấp hơn trên #faster/#records.len() màn và có
trung vị bộ nhớ thấp hơn trên #less_memory/#records.len() màn. Các nhận xét
này được tính trực tiếp từ bảng kết quả của lần thu thập hiện tại.

Giảm số nút không bảo đảm giảm thời gian tương ứng: A\* còn phải tính hàm
ước lượng, tạo khóa cấu hình và tra bộ nhớ đệm. Trên màn nhỏ, chi phí này
có thể lớn hơn phần tìm kiếm tiết kiệm được. Hàm ước lượng bỏ nhiều ràng
buộc và dùng hệ số bảo thủ 0.3, nên ở một số màn mức giảm tìm kiếm còn nhỏ.
Số nút giảm cũng không quyết định duy nhất mức dùng bộ nhớ vì còn có dữ
liệu điểm mốc, bảng chi phí, bảng cha và các phần tử cũ trong hàng đợi.

#callout_note(title: [Vì sao số đo có thể khác khi chơi trên giao diện?])[
Giao diện thường hiển thị kết quả của một lần chạy từ trạng thái người
chơi đang đứng. Báo cáo lấy trung vị nhiều lần từ trạng thái ban đầu,
xóa bộ nhớ đệm hàm ước lượng trước mỗi lần và chạy ngoài giao diện. Dù
cùng dùng `run_solver()`, điều kiện chạy khác nhau có thể cho số đo khác.
]

== Giới hạn và hướng hoàn thiện

#callout_warning(title: [Phạm vi kết luận])[
Kết quả áp dụng cho các màn, trạng thái bắt đầu, mã nguồn và môi trường
được ghi nhận. Số liệu không chứng minh A\* luôn nhanh hơn hoặc dùng ít
bộ nhớ hơn. Phương án đối chứng dùng chung mã tìm kiếm, nên chưa loại trừ
lỗi chung của bản cài đặt hoặc thay thế đối chiếu với UCS độc lập.
]

Chương trình thu thập hiện chưa đặt giới hạn thời gian hoặc số nút, và
chưa khảo sát nhiều máy, nhiều trạng thái giữa màn hay các màn không có
lời giải được thiết kế riêng. Trước khi kết luận cho toàn bộ đồ án, nhóm
cần bổ sung các thuật toán độc lập, phân nhóm màn theo cơ chế và giữ cùng
quy tắc đo. BFS tối ưu số hành động, còn UCS và A\* tối ưu chi phí chung;
không so sánh chất lượng lời giải chỉ bằng số bước.

Trước khi nộp, cần điền thông tin bìa của báo cáo chung, xác nhận đóng góp
của các thành viên và ghi nhận hỗ trợ AI theo quy định môn học. Bản thảo
được soạn với trợ lý AI từ mã nguồn, tài liệu hàm ước lượng và dữ liệu đo;
người thực hiện cần rà soát và xác nhận nội dung.

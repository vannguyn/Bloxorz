# Báo cáo thành viên số 5 — Võ Nhật Minh — 24120202

**Phần A* để ghép vào project nằm trong `Astar.typ`.** Mở file này và chọn
**Typst Preview: Preview Opened File** để xem riêng; export thành `Astar.pdf`.
Nếu đã ghim `main.typ`, chạy **Unpin the Main File** trước khi preview file riêng.
File này gom các phần bằng `#include`; sửa nội dung ở `sections/`.
Phần thực nghiệm đọc bảng từ `data/validation.csv` do `collect_results.py` tạo.
Trong file báo cáo chính cùng thư mục, dùng:

```typst
#include "Astar.typ"
```

`main.typ` đã được khôi phục về mẫu ban đầu theo yêu cầu. File tổng để làm
việc với phần A* hiện tại là `Astar.typ`, xuất thành `Astar.pdf`.
Nội dung bám code hiện
tại và `docs/astar-heuristic.md`, không mô tả API tương lai như tính năng đã có.
Đây là phần của thành viên số 5 — Võ Nhật Minh — MSSV 24120202 để ghép vào
báo cáo nhóm, chưa thay thế các phần của những thành viên khác.

## 1. Cài extension trên VS Code

Máy được kiểm tra trong phiên làm việc đã có **Tinymist Typst 0.15.10**.
Nếu Extensions hiển thị **Disable/Uninstall** thì extension đã cài; chỉ cần
kiểm tra nó không bị Disable trong workspace.

Nếu cài trên máy khác:

1. Mở VS Code, nhấn `Ctrl+Shift+X`.
2. Tìm **Tinymist Typst**, chọn extension của **Myriad-Dreamin**.
   Extension ID: `myriad-dreamin.tinymist`.
3. Chọn **Install**. Có thể cài bằng terminal:

   ```powershell
   code --install-extension myriad-dreamin.tinymist
   ```

4. Mở thư mục gốc `Bloxorz` bằng **File > Open Folder**.

Tinymist hỗ trợ preview và export PDF; không bắt buộc cài thêm Typst Preview,
LaTeX Workshop hay một distribution LaTeX. Typst CLI là tùy chọn nếu muốn
dùng lệnh `typst compile/watch` độc lập trong terminal. Hướng dẫn chính thức:
[Tinymist cho VS Code](https://myriad-dreamin.github.io/tinymist/frontend/vscode.html).

## 2. Xem trước và sửa tài liệu nhiều file

1. Mở **`typst/main.typ`**, không bắt đầu preview từ file section.
2. Nhấn `Ctrl+Shift+P`, tìm **Pin the Main File to the Currently Open Document**
   của Tinymist để ghim `main.typ` làm tài liệu chính.
3. Nhấn `Ctrl+Shift+P`, chạy **Typst Preview: Preview Opened File**.
4. Mở các file trong `sections/` để sửa; preview sẽ cập nhật theo tài liệu chính.

Tên lệnh được xác nhận từ Tinymist 0.15.10 cài trên máy; ở phiên bản khác có
thể tìm bằng từ khóa **Typst Preview**, **Pin Main**, **Export PDF**.
Không dùng Markdown Preview để mở `.typ`.

## 3. Xuất PDF

Mở/ghim `main.typ`, rồi `Ctrl+Shift+P` > **Export the Opened File as PDF**.
Kiểm tra file `typst/main.pdf`. Các PDF `main_lab.pdf` và `main_project.pdf`
có sẵn là bản mẫu cũ, không phải bản báo cáo mới này.

Hoặc tại thư mục gốc repo, chạy:

```powershell
.\typst\compile.ps1
```

Script dùng `typst` nếu đã có trong PATH, nếu không dùng `tinymist.exe` từ
extension VS Code trên Windows. Không cần thêm thư mục extension vào PATH.
Nếu PowerShell không cho chạy script, dùng lệnh Export trong VS Code.
Trên máy hiện tại PowerShell đang chặn chạy `.ps1`, nên ưu tiên Export PDF.

Nếu đã cài Typst CLI độc lập:

```powershell
typst compile typst/main.typ typst/main.pdf
typst watch typst/main.typ typst/main.pdf
```

Lần biên dịch đầu cần mạng để tải các package đã được ghim phiên bản trong
`template.typ`: `chic-hdr:0.5.0`, `equate:0.3.2`, `codly:1.3.0` cùng dependency.
Nếu bị lỗi download, kiểm tra kết nối/proxy rồi biên dịch lại. Preview và
export dùng cùng môi trường compiler/package:
[Tài liệu export của Tinymist](https://myriad-dreamin.github.io/tinymist/feature/export.html).

## 4. Viết nội dung ở đâu?

| File | Nội dung |
|---|---|
| `main.typ` | Bìa, thông tin người thực hiện, thứ tự các chương |
| `sections/01_gioithieu.typ` | Mục tiêu, input/output, ranh giới module |
| `sections/02_kientruc_thietke.typ` | StepCost và cấu trúc dữ liệu |
| `sections/03_thuat_toan_ma_nguon.typ` | A*, mã giả, reopen và tích hợp |
| `sections/04_danhgia_phancong.typ` | Relaxation, teleport, chứng minh heuristic |
| `sections/05_thucnghiem.typ` | Bảng chi phí, số nút, thời gian/bộ nhớ và đánh giá |
| `references.bib` | Nguồn nội bộ cho nội dung code và chứng minh |
| `template.typ`, `components.typ` | Định dạng, bảng, hộp thuật toán |
| `data/validation.csv` | Kết quả tổng hợp, trung vị thời gian và bộ nhớ |
| `data/raw_runs.csv` | Số liệu từng lần đo, gồm thứ tự chạy |
| `data/environment.json` | Môi trường, quy trình đo và hash phiên bản code/level |

Trước khi nộp, điền mã môn, giảng viên, lớp, MSSV, tên và email trong
`main.typ`; các giá trị trong dấu `[...]` là chỗ điền, không phải dữ liệu thật.
Năm học cũng cần kiểm tra lại. Không tự điền tỷ lệ đóng góp hoặc kết quả
benchmark chưa được nhóm xác nhận.

Ví dụ cú pháp Typst:

````typst
== Tiêu đề mục

Đoạn văn với *chữ đậm*, _chữ nghiêng_ và `tên_hàm`.

$ f(s) = g(s) + h(s) $

- Ý thứ nhất.
- Ý thứ hai.

```python
result = run_solver(AStarSolver(), level, start)
```
````

## 5. Cập nhật kết quả sau khi đổi code

```powershell
python typst/collect_results.py
```

Sau khi chạy xong, mở `Astar.typ` và chọn **Export the Opened File as PDF**.
Nếu PowerShell cho phép chạy script, có thể dùng compiler CLI thay thế.

Script dùng thư viện chuẩn Python và module repo, không cần pygame/pytest.
Mặc định đo 5 lần mỗi màn/cấu hình sau một lần chạy thử không ghi số đo,
qua `run_solver()` như UI. Nó xóa cache heuristic trước mỗi lần, chạy tuần
tự, đổi thứ tự A*/h=0 giữa các lần lặp và lấy trung vị. Thời gian gồm phần
solve, bộ nhớ là peak Python allocations qua tracemalloc (byte // 1024).
Replay và kiểm tra goal/cost được thực hiện ngoài khoảng đo.

Có thể đổi số lần lặp:

```powershell
python typst/collect_results.py --repeats 10
```

Số liệu từng lần được lưu ở `data/raw_runs.csv`; bảng tổng hợp ở
`data/validation.csv` và điều kiện đo ở `data/environment.json`. Bảng và
nhận xét trong Typst cập nhật theo dữ liệu này sau khi export lại.
Đối chứng là cùng solver với `h=0`, không phải implementation UCS độc lập.
Hiện script chưa đặt timeout; lỗi sẽ dừng thu thập, không công bố bộ CSV
mới chưa hoàn tất. Số đo có thể khác UI do UI hiển thị một lần chạy, trạng
thái người chơi và điều kiện cache khác nhau.

## 6. Lỗi thường gặp

- **Undefined variable khi mở section:** ghim `main.typ` và preview lại.
- **Sai đường dẫn ảnh/bibliography:** giữ cấu trúc thư mục, biên dịch `main.typ`.
- **Không tìm thấy `typst`:** dùng extension hoặc `compile.ps1`; extension đã
  cài không đồng nghĩa lệnh `typst` có sẵn trong PATH.
- **Font tiếng Việt:** mẫu dùng Times New Roman và Consolas. Máy khác cần có
  font hỗ trợ tiếng Việt hoặc thay font trong `template.typ`.
- **Lỗi sau khi sửa:** mở Problems bằng `Ctrl+Shift+M`, sửa lỗi đầu tiên trước.

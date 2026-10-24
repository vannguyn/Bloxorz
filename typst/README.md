# BIỂU MẪU BÁO CÁO VÀ BÀI TẬP CÁ NHÂN / ĐỒ ÁN MÔN HỌC
### Khoa Công nghệ Thông tin — Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM (FIT - HCMUS)

---

## 📌 1. Giới thiệu tổng quan

Bộ biểu mẫu được thiết kế chuyên biệt dành cho sinh viên **Khoa Công nghệ Thông tin - Trường ĐH Khoa học Tự nhiên (ĐHQG-HCM)**, đáp ứng đồng thời 2 nhu cầu phổ biến:
1. **Bài tập cá nhân / Thực hành Lab hàng tuần (Assignment / Lab Report):** Gọn gàng (3–10 trang), có khối thông tin sinh viên ngay trên đầu trang 1 (Header block) giúp tiết kiệm giấy in, không rườm rà.
2. **Báo cáo Đồ án môn học / Tiểu luận chuyên đề (Course Project Report):** Đầy đủ trang bìa phong cách hiện đại thanh lịch, mục lục tự động, danh mục hình ảnh & bảng biểu, phân chia chương mục rõ ràng, bảng phân công nhiệm vụ và tài liệu tham khảo.

### 📐 Quy chuẩn định dạng học thuật (ĐHQG-HCM)
* **Khổ giấy:** A4 ($21.0 \times 29.7\text{ cm}$).
* **Lề trang chuẩn đóng tập:**
  * Lề Trái (*Left*): **$3.0\text{ cm}$**
  * Lề Phải (*Right*): **$2.0\text{ cm}$**
  * Lề Trên (*Top*): **$2.0\text{ cm}$**
  * Lề Dưới (*Bottom*): **$2.0\text{ cm}$**
* **Kiểu chữ (Typography):**
  * Văn bản chính: **Times New Roman $13\text{ pt}$**, dãn dòng $1.35$ lines, thụt đầu dòng $1.27\text{ cm}$, khoảng cách đoạn dưới $6\text{ pt}$.
  * Mã nguồn / Kỹ thuật: **Consolas $10.5\text{ pt}$**.
* **Tiêu đề bảng & hình:**
  * Bảng biểu: **Bảng X:** đặt ở **TRÊN** bảng.
  * Hình ảnh: **Hình X:** đặt ở **DƯỚI** hình.

---

## 📂 2. Cấu trúc thư mục

```text
templates/
├── README.md                      # Hướng dẫn chi tiết sử dụng bộ biểu mẫu
├── word/
│   ├── Mau_Bao_Cao_FIT_HCMUS.docx # Tệp Word mẫu hoàn chỉnh tích hợp sẵn hệ thống Styles
│   └── figures/                   # Thư mục chứa biểu trưng chính thức HCMUS
│       └── hcmus_logo.png
├── latex/
│   ├── main.tex                   # Tệp biên dịch chính (XeLaTeX)
│   ├── main.pdf                   # Bản xuất PDF mẫu hoàn chỉnh để xem trước
│   ├── fit_hcmus.sty              # Gói định dạng giao diện, màu sắc, bìa và môi trường
│   ├── references.bib             # Tệp cơ sở dữ liệu trích dẫn BibTeX
│   ├── figures/                   # Biểu trưng HCMUS dùng cho LaTeX
│   │   └── hcmus_logo.png
│   └── sections/                  # Các chương mục nội dung tách rời
│       ├── 01_gioithieu.tex       # Mục 1: Bối cảnh, mục tiêu, yêu cầu
│       ├── 02_kientruc_thietke.tex# Mục 2: Sơ đồ, bảng cấu hình, công thức toán
│       ├── 03_thuat_toan_ma_nguon.tex # Mục 3: Mã giả (Pseudocode), Code block, Callouts
│       └── 04_danhgia_phancong.tex    # Mục 4: Bảng phân công nhiệm vụ, Checklist nộp bài
└── typst/
    ├── main.typ                      # Tệp biên dịch chính của mẫu Typst
    ├── references.bib                # Cơ sở dữ liệu trích dẫn BibTeX
    ├── figures/
    │   └── hcmus_logo.png            # Biểu trưng dùng trên bìa và header
    └── sections/                     # Các chương mục nội dung dạng Typst
        ├── 01_gioithieu.typ
        ├── 02_kientruc_thietke.typ
        ├── 03_thuat_toan_ma_nguon.typ
        └── 04_danhgia_phancong.typ
```

---

## 📝 3. Hướng dẫn sử dụng Biểu mẫu Word (`.docx`)

Tệp `templates/word/Mau_Bao_Cao_FIT_HCMUS.docx` đã được định hình sẵn:
1. **Lựa chọn chế độ sử dụng:**
   * **Nếu làm Đồ án môn học:** Giữ nguyên trang bìa lớn ở trang 1. Xóa khối *Header rút gọn* ở trang 2 và bắt đầu viết từ mục 1.
   * **Nếu làm Bài tập cá nhân / Lab ngắn:** Xóa trang bìa (trang 1) và dấu ngắt trang, sử dụng trực tiếp khối *Header rút gọn* trên đầu trang 1 để điền MSSV, Họ tên, Lớp.
2. **Sử dụng hệ thống Quick Styles tích hợp sẵn:**
   * `Heading 1`: Tiêu đề mục lớn (1., 2., 3.) - Times New Roman $15\text{ pt}$ Bold, màu xanh HCMUS `#003366`.
   * `Heading 2`: Tiêu đề mục cấp 2 (1.1., 1.2.) - Times New Roman $13.5\text{ pt}$ Bold, màu `#1A2B4C`.
   * `Heading 3`: Tiêu đề mục cấp 3 (1.1.1.) - Times New Roman $13\text{ pt}$ Bold Italic.
   * `Normal`: Đoạn văn bản chuẩn $13\text{ pt}$, dãn dòng $1.35$.
3. **Các thành phần kỹ thuật đã dựng sẵn:**
   * **Khối Code Consolas:** Bảng 1 ô nền xám nhạt `#F6F8FA`, viền mỏng bo nhẹ, có đánh số thứ tự dòng code.
   * **Khối Mã giả (Pseudocode):** Trình bày chuẩn bài báo khoa học.
   * **Callout Boxes:** 3 loại hộp chú thích được tạo bởi bảng 1 ô có viền trái dày:
     * ℹ **Ghi chú (Note):** Nền `#F0F5FA`, viền trái xanh dương `#005CA9`.
     * 💡 **Mẹo hay (Tip):** Nền `#F2F9F4`, viền trái xanh lá `#4CAF50`.
     * ⚠ **Cảnh báo (Warning):** Nền `#FFF9F2`, viền trái cam `#FF9800`.
   * **Bảng phân công & Checklist:** Bảng có tiêu đề xanh HCMUS đậm, chữ trắng, các dòng xen kẽ xám nhạt.
4. **Mẹo lưu thành Template dùng lâu dài:**
   * Trong Microsoft Word: Chọn `File` $\rightarrow$ `Save As` $\rightarrow$ Chọn định dạng `Word Template (*.dotx)`.
   * Từ lần sau chỉ cần chọn `New from template` là có ngay văn bản chuẩn.

---

## ⚡ 4. Hướng dẫn sử dụng Biểu mẫu LaTeX (`.tex`)

Dự án được tối ưu hóa cho **XeLaTeX** hoặc **LuaLaTeX** để tải trực tiếp font **Times New Roman** và **Consolas** hệ thống.

### 4.1. Chuyển đổi giữa Đồ án và Bài tập ngắn
Trong tệp [main.tex](file:///d:/Codes/doc-misc/templates/latex/main.tex), bạn chỉ cần điều chỉnh dòng:
```latex
\newif\ifisprojectreport
\isprojectreporttrue   % <--- Giữ nguyên true cho Đồ án (có bìa + mục lục)
                       % <--- Đổi thành \isprojectreportfalse cho Bài tập cá nhân ngắn
```

### 4.2. Biên dịch trên máy tính cá nhân (Local)
Mở terminal tại thư mục `templates/latex/` và chạy:
```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```
*(Hoặc trong VS Code với extension LaTeX Workshop, cấu hình recipe biên dịch chọn `xelatex`).*

## ⚡ 5. Hướng dẫn sử dụng Biểu mẫu Typst (`.typ`)

Thư mục [typst/](typst/) chứa biểu mẫu Typst chuẩn hoá hoàn chỉnh tương đương với bản LaTeX, bao gồm bìa đồ án, chế độ bài tập ngắn, mục lục tự động, header/footer, thuật toán, mã nguồn và trích dẫn BibTeX.

### 5.1. Soạn thảo trên Visual Studio Code (Khuyên dùng)
1. Cài đặt tiện ích mở rộng [**Tinymist Typst**](https://marketplace.visualstudio.com/items?itemName=myriad-dreamit.tinymist) trên VS Code.
2. Mở file [typst/main.typ](typst/main.typ).
3. **Các tính năng nổi bật của Tinymist:**
   * **Xem trước thời gian thực (Live Preview):** Nhấn vào biểu tượng kính lúp / **Show Preview** ở góc trên bên phải thanh công cụ editor (hoặc bấm `Ctrl + K, V`) để mở tab xem trước cạnh mã nguồn; tài liệu sẽ tự động cập nhật ngay lập tức khi bạn gõ.
   * **Xuất PDF nhanh (Export PDF):** Nhấn vào nút **Export** / **Export to PDF** trên thanh công cụ góc phải của file `.typ`, hoặc nhấn `Ctrl + Shift + P` $\rightarrow$ gõ `Tinymist: Export Current Document as PDF`.

### 5.2. Biên dịch bằng dòng lệnh (CLI)
Nếu máy tính đã cài đặt [Typst CLI](https://github.com/typst/typst):
```bash
# Biên dịch ra file PDF
typst compile typst/main.typ typst/main.pdf

# Hoặc bật chế độ tự động theo dõi thay đổi và biên dịch lại khi lưu file:
typst watch typst/main.typ typst/main.pdf
```

### 5.3. Cấu hình nội dung báo cáo
* Sửa thông tin môn học, giảng viên, lớp, danh sách sinh viên tại hàm `fit_report` ở đầu [main.typ](typst/main.typ).
* **Chế độ hiển thị:**
  * Đặt `is_project_report: true`: Chế độ đồ án lớn (có trang bìa riêng và trang mục lục).
  * Đặt `is_project_report: false`: Chế độ bài tập ngắn / Lab (sử dụng header thu gọn ngay đầu trang 1).
* Nội dung các phần được tách độc lập trong thư mục `typst/sections/`. Các thành phần giao diện mẫu (hộp ghi chú `callout`, thuật toán `algorithm_box`, bảng biểu) được định nghĩa sẵn trong [components.typ](typst/components.typ).

### 4.3. Sử dụng trên Overleaf
1. Nén toàn bộ thư mục `templates/latex/` thành tệp `.zip`.
2. Truy cập [Overleaf.com](https://www.overleaf.com) $\rightarrow$ `New Project` $\rightarrow$ `Upload Project`.
3. Bấm vào nút **Menu** ở góc trên bên trái của Overleaf:
   * Tại mục **Compiler**: Chọn **XeLaTeX** (hoặc LuaLaTeX).
   * Tại mục **Main document**: Chọn `main.tex`.
4. Bấm **Recompile**.

### 4.4. Cú pháp các khối đặc thù trong LaTeX
* **Chèn hộp chú thích:**
  ```latex
  \begin{calloutnote}[Tiêu đề ghi chú]
      Nội dung ghi chú kỹ thuật...
  \end{calloutnote}

  \begin{callouttip}[Mẹo tối ưu]
      Nội dung mẹo hay...
  \end{callouttip}

  \begin{calloutwarning}[Lưu ý quan trọng]
      Nội dung cảnh báo...
  \end{calloutwarning}
  ```
* **Chèn mã nguồn (Code listing):**
  ```latex
  \begin{lstlisting}[language=Python, caption={Tiêu đề code}]
  def hello_world():
      print("Hello FIT - HCMUS")
  \end{lstlisting}
  ```
* **Chèn thuật toán (Mã giả):**
  ```latex
  \begin{algorithm}[h!]
      \caption{Tên thuật toán}
      \begin{algorithmic}[1]
          \Require Đầu vào ...
          \Ensure Đầu ra ...
          \State Khởi tạo ...
      \end{algorithmic}
  \end{algorithm}
  ```

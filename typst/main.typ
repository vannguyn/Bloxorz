// ==============================================================================
// BIỂU MẪU BÁO CÁO VÀ BÀI TẬP KHOA CÔNG NGHỆ THÔNG TIN - ĐH KHTN (ĐHQG-HCM)
// Bản Typst chuẩn hoá - cấu trúc tương đồng LaTeX main.tex
// ==============================================================================

#import "template.typ": *

// ==============================================================================
// THIẾT LẬP THÔNG TIN BÁO CÁO / BÀI TẬP
// ==============================================================================
#show: fit_report.with(
  // Thông tin môn học & đề tài
  course_id: "CSC14003",
  course_name: "NHẬP MÔN TRÍ TUỆ NHÂN TẠO",
  report_subtitle: "BÁO CÁO ĐỒ ÁN MÔN HỌC",
  report_title: "BLOXORZ SOLVER",
  instructor: "TS. Bùi Tiến Lên",
  class_id: "24_22",
  academic_year: "Học kỳ I, 2026 - 2027",

  // Danh sách sinh viên thực hiện: (MSSV, Họ và tên, Email sinh viên)
  students: (
    ("24120127", "Nguyễn Ngọc Quang", "24120127@student.hcmus.edu.vn"),
    ("24120134", "Lương Nhật Tân", "24120134@student.hcmus.edu.vn"),
    ("24120185", "Nguyễn Gia Hưng", "24120185@student.hcmus.edu.vn"),
    ("24120202", "Võ Nhật Minh", "24120202@student.hcmus.edu.vn"),
    ("24120205", "Trần Văn Nguyên", "24120205@student.hcmus.edu.vn")
  ),
  is_project_report: true,
)

// ==============================================================================
// CÁC CHƯƠNG MỤC NỘI DUNG (SECTIONS) - TƯƠNG ĐƯƠNG \input TRONG LATEX
// ==============================================================================
#include "sections/01_gioithieu.typ"
#include "sections/02_kientruc_thietke.typ"
#include "sections/03_thuat_toan_ma_nguon.typ"
#include "sections/04_bfs.typ"
#include "sections/05_dfs.typ"
#include "sections/06_ucs.typ"
#include "sections/07_astar.typ"
#include "sections/08_danhgia_phancong.typ"

// ==============================================================================
// PHỤ LỤC: CÔNG KHAI SỬ DỤNG AI
// ==============================================================================
#pagebreak()
= Phụ lục: Công khai việc sử dụng công cụ AI

Trong quá trình thực hiện đồ án, nhóm có sử dụng các công cụ AI tạo sinh
để hỗ trợ trao đổi ý tưởng, tìm hiểu và rà soát mã nguồn, cũng như hoàn
thiện báo cáo. Các công cụ được sử dụng gồm:

#table(
  columns: (1fr, 1fr, 2.5fr),
  table.header([*Công cụ*], [*Nhà cung cấp*], [*Mục đích sử dụng*]),
  [Codex], [OpenAI], [Hỗ trợ viết mã nguồn, xử lý logic, lập trình và kiểm thử thuật toán.],
  [Claude], [Anthropic], [Hỗ trợ giải thích thuật toán, tư duy giải quyết bài toán và cách tổ chức mã nguồn.],
  [Antigravity], [Google], [Hỗ trợ toàn diện việc code, giải quyết bài toán, phân tích heuristic và kiểm thử dự án.],
  [ChatGPT], [OpenAI], [Hỗ trợ thảo luận khái niệm, diễn đạt văn phong và rà soát nội dung báo cáo.],
)

Các đề xuất do công cụ AI đưa ra không được xem là kết quả đúng mặc
nhiên. Nhóm đã xem xét, chỉnh sửa và kiểm chứng mã nguồn, đường đi và
kết quả thực nghiệm bằng chương trình, đồng thời chịu trách nhiệm về
nội dung cuối cùng của đồ án.

Một số prompt tiêu biểu:

- “Kiểm tra xem các thuật toán tìm kiếm đã đáp ứng yêu cầu của đề bài
  chưa; nêu rõ căn cứ và điểm cần lưu ý.”
- “Phân tích vì sao DFS tìm được đường đi dài và đối chiếu kết quả với
  BFS trên các level; không thay đổi mã nguồn.”
- “Điều chỉnh chức năng giải để thuật toán tìm đường từ trạng thái hiện
  tại của khối, thay vì luôn quay về trạng thái ban đầu.”
- “Dùng cùng bộ level để thu thập số liệu của bốn thuật toán, kiểm tra
  lời giải và tạo bảng, biểu đồ cho báo cáo.”

// ==============================================================================
// TÀI LIỆU THAM KHẢO (BIBLIOGRAPHY)
// ==============================================================================
#pagebreak()
#heading(level: 1, numbering: none)[Tài liệu tham khảo] <nooutlined>
#bibliography("references.bib", title: none, style: "ieee", full: true)

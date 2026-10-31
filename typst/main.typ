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
  course_id: "CSC10043",
  course_name: "NHẬP MÔN TRÍ TUỆ NHÂN TẠO",
  report_subtitle: "BÁO CÁO ĐỒ ÁN MÔN HỌC",
  report_title: "TÊN ĐỀ TÀI / TÊN BÀI TẬP",
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

  // CHỌN CHẾ ĐỘ HIỂN THỊ (PROJECT HOẶC ASSIGNMENT/LAB)
  // Đặt true: Báo cáo đồ án (có trang bìa riêng, mục lục La Mã)
  // Đặt false: Bài tập cá nhân / Lab ngắn (header đầu trang 1)
  is_project_report: true,
)

// ==============================================================================
// CÁC CHƯƠNG MỤC NỘI DUNG (SECTIONS) - TƯƠNG ĐƯƠNG \input TRONG LATEX
// ==============================================================================
#include "sections/01_gioithieu.typ"
#include "sections/02_kientruc_thietke.typ"
#include "sections/03_thuat_toan_ma_nguon.typ"
#include "sections/04_danhgia_phancong.typ"

// ==============================================================================
// TÀI LIỆU THAM KHẢO (BIBLIOGRAPHY)
// ==============================================================================
#pagebreak()
#heading(level: 1, numbering: none)[Tài liệu tham khảo] <nooutlined>
#bibliography("references.bib", title: none, style: "ieee")

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
  report_subtitle: "BÁO CÁO ĐỒ ÁN MÔN HỌC / BÀI TẬP CÁ NHÂN",
  report_title: "TÊN ĐỀ TÀI / TÊN BÀI TẬP",
  instructor: "TS. Nguyễn Văn X",
  class_id: "21CNTN",
  academic_year: "Học kỳ I, 2026 - 2027",

  // Danh sách sinh viên thực hiện: (MSSV, Họ và tên, Email sinh viên)
  students: (
    ("21120001", "Nguyễn Văn A", "nva@clc.fit.hcmus.edu.vn"),
    ("21120002", "Trần Thị B", "ttb@clc.fit.hcmus.edu.vn"),
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

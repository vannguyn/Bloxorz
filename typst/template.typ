// ==============================================================================
// BIỂU MẪU BÁO CÁO VÀ BÀI TẬP KHOA CÔNG NGHỆ THÔNG TIN - ĐH KHTN (ĐHQG-HCM)
// File mẫu Typst chuẩn hoá (tương đương fit_hcmus.sty trong LaTeX)
// ==============================================================================

#import "@preview/chic-hdr:0.5.0": *
#import "@preview/equate:0.3.2": *
#import "@preview/codly:1.3.0": *

// Nạp lại các thành phần giao diện
#import "components.typ": *

// ==============================================================================
// 1. ĐỊNH NGHĨA MÀU SẮC CHUẨN NHẬN DIỆN THƯƠNG HIỆU FIT-HCMUS
// ==============================================================================
#let hcmus_blue = rgb("#003366")       // Xanh ĐHKHTN đậm
#let fit_blue = rgb("#005CA9")         // Xanh FIT tươi
#let dark_navy = rgb("#1A2B4C")        // Màu chữ tiêu đề
#let code_bg = rgb("#F6F8FA")          // Nền code
#let code_border = rgb("#D0D7DE")      // Viền code
#let code_green = rgb("#22863A")       // Comment
#let code_blue = rgb("#005CC5")        // Từ khóa
#let code_purple = rgb("#6F42C1")      // Hàm số
#let code_red = rgb("#D73A49")         // Chuỗi

// ==============================================================================
// 2. BỘ CHỌN TIỆN ÍCH (KẾ THỪA TỪ _OLD_TEMPLATE)
// ==============================================================================
#let nonumber = <nonumber>
#let nooutlined = <nooutlined>
#let hidden = <hidden>

// ==============================================================================
// 3. TRANG BÌA ĐỒ ÁN (PROJECT COVER PAGE)
// ==============================================================================
#let make_student_table(students) = table(
  columns: (auto, auto, auto),
  align: (left, left, left),
  inset: (x: 8pt, y: 6.75pt),
  stroke: none,
  table.header(
    [*MSSV*],
    [*Họ và tên*],
    [*Email sinh viên*],
  ),
  ..students.map(student => (
    [#student.at(0)],
    [#student.at(1)],
    [#student.at(2)],
  )).flatten(),
)

#let make_cover_page(
  course_id: "",
  course_name: "",
  report_subtitle: "",
  report_title: "",
  instructor: "",
  class_id: "",
  academic_year: "",
  students: (),
  logo_path: "figures/hcmus_logo.png",
) = {
  set page(
    header: none,
    footer: none,
    numbering: none,
    margin: (left: 30mm, right: 20mm, top: 20mm, bottom: 20mm),
  )
  set par(first-line-indent: 0pt, spacing: 0pt)
  align(center)[
    #v(8pt)
    #stack(
      spacing: 16pt,
      text(size: 13pt, weight: "bold")[ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH],
      text(size: 14pt, weight: "bold", fill: hcmus_blue)[TRƯỜNG ĐẠI HỌC KHOA HỌC TỰ NHIÊN],
      text(size: 13pt, weight: "bold", fill: fit_blue)[KHOA CÔNG NGHỆ THÔNG TIN],
    )
    #v(18pt)
    #line(length: 65%, stroke: 1.5pt + fit_blue)
    #v(20pt)
    #image(logo_path, height: 3.6cm)
    #v(28pt)
    #stack(
      spacing: 16pt,
      text(size: 13pt, weight: "bold")[MÔN HỌC: #course_id - #course_name],
      text(size: 14pt, weight: "bold", fill: dark_navy)[#report_subtitle],
    )
    #v(24pt)
    #block(
      width: 100%,
      inset: (x: 12pt, y: 19.5pt),
      stroke: 1.5pt + hcmus_blue,
      radius: 4pt,
    )[
      #text(size: 18pt, weight: "bold", fill: hcmus_blue)[#report_title]
    ]
    #v(32pt)
    #pad(left: 1cm)[
      #align(left)[
        #grid(
          columns: (auto, 1fr),
          column-gutter: 8pt,
          row-gutter: 17pt,
          [*Giảng viên hướng dẫn:*], [#instructor],
          [*Lớp:*], [#class_id],
          [*Năm học:*], [#academic_year],
          [*Sinh viên thực hiện:*], [],
        )
        #v(6pt)
        #make_student_table(students)
      ]
    ]
  ]
  pagebreak()
}

// ==============================================================================
// 4. HEADER BÀI TẬP CÁ NHÂN / LAB NGẮN (ASSIGNMENT HEADER)
// ==============================================================================
#let make_assignment_header(
  course_id: "",
  course_name: "",
  report_subtitle: "",
  report_title: "",
  instructor: "",
  class_id: "",
  academic_year: "",
  students: (),
  logo_path: "figures/hcmus_logo.png",
) = {
  set par(first-line-indent: 0pt, spacing: 0pt)
  grid(
    columns: (18%, 1fr),
    gutter: 12pt,
    align(center + horizon, image(logo_path, width: 100%)),
    [
      #text(size: 13pt, weight: "bold")[TRƯỜNG ĐẠI HỌC KHOA HỌC TỰ NHIÊN - ĐHQG TP.HCM] \
      #v(10pt)
      #text(size: 13pt, weight: "bold", fill: fit_blue)[KHOA CÔNG NGHỆ THÔNG TIN] \
      #v(10pt)
      #text(size: 11.5pt)[Môn học: *#course_id - #course_name*] \
      #v(10pt)
      #text(size: 11.5pt)[Giảng viên: *#instructor* | Lớp: *#class_id*]
    ],
  )
  v(18pt)
  line(length: 100%, stroke: 1.2pt + hcmus_blue)
  v(18pt)
  align(center)[
    #text(size: 16pt, weight: "bold", fill: hcmus_blue)[#report_title] \
    #v(12pt)
    #text(size: 12pt, style: "italic")[#report_subtitle] \
    #v(12pt)
    #block(
      width: 100%,
      inset: (x: 8pt, y: 6pt),
      fill: code_bg,
      stroke: 0.6pt + code_border,
      radius: 2pt,
    )[
      #text(size: 10pt)[
        *Họ và tên sinh viên:* #students.map(student => student.at(1)).join(", ")
        #h(1em)|#h(1em) *Năm học:* #academic_year
      ]
    ]
  ]
}

// ==============================================================================
// 5. HÀM TEMPLATE CHÍNH: FIT_REPORT
// ==============================================================================
#let fit_report(
  course_id: "CSC10043",
  course_name: "NHẬP MÔN TRÍ TUỆ NHÂN TẠO",
  report_subtitle: "BÁO CÁO ĐỒ ÁN MÔN HỌC / BÀI TẬP CÁ NHÂN",
  report_title: "TÊN ĐỀ TÀI / TÊN BÀI TẬP",
  instructor: "TS. Nguyễn Văn X",
  class_id: "21CNTN",
  academic_year: "Học kỳ I, 2026 - 2027",
  students: (
    ("21120001", "Nguyễn Văn A", "nva@clc.fit.hcmus.edu.vn"),
    ("21120002", "Trần Thị B", "ttb@clc.fit.hcmus.edu.vn"),
  ),
  is_project_report: true,
  logo_path: "figures/hcmus_logo.png",
  toc_title: "Nội dung",
  body,
) = {
  // --- A. CẤU HÌNH TRANG VÀ VĂN BẢN CHUẨN ĐHQG-HCM ---
  // LaTeX: font 13pt, \setstretch{1.35}, \parskip=6pt
  // Typst spacing = leading + parskip: 0.72em + ~0.46em ≈ 1.2em (≈15.6pt)
  // (Typst spacing THAY THẾ leading giữa các đoạn, không cộng dồn như LaTeX)

  set page(
    paper: "a4",
    margin: (left: 30mm, right: 20mm, top: 24mm, bottom: 20mm),
    numbering: "1",
  )

  set text(
    font: "Times New Roman",
    size: 13pt,
    lang: "vi",
  )

  set par(
    justify: true,
    leading: 0.72em,    // Dãn dòng ≈ 1.35 (khớp LaTeX \setstretch{1.35})
    spacing: 1.6em,     // Khoảng cách giữa đoạn — thoải mái giống LaTeX
    first-line-indent: (amount: 1.27cm, all: false),
  )

  // List/Enum: lề trên dưới khối 20pt, khoảng cách giữa các items 18pt chuẩn LaTeX
  show list: set block(above: 20pt, below: 20pt)
  show enum: set block(above: 20pt, below: 20pt)
  set list(indent: 0.8cm, spacing: 18pt)
  set enum(indent: 0.8cm, spacing: 18pt)

  show link: set text(fill: fit_blue)

  // --- B. ĐỊNH DẠNG TIÊU ĐỀ MỤC THEO TITLESEC ---
  // Định dạng số mục có dấu chấm ở cuối (1., 1.1., 1.1.1.) chuẩn LaTeX
  set heading(numbering: (..nums) => nums.pos().map(str).join(".") + ".")

  show heading.where(level: 1): it => {
    set text(size: 15pt, weight: "bold", fill: hcmus_blue)
    v(20pt)
    block(above: 18pt, below: 22pt, width: 100%)[
      #stack(
        spacing: 29pt,
        [
          #if it.numbering != none {
            counter(heading).display(it.numbering)
            h(0.6em)
          }
          #it.body
        ],
        line(length: 100%, stroke: 0.8pt + hcmus_blue),
      )
    ]
  }

  show heading.where(level: 2): it => {
    set text(size: 13.5pt, weight: "bold", fill: dark_navy)
    block(above: 27pt, below: 20pt)[
      #if it.numbering != none {
        counter(heading).display(it.numbering)
        h(0.5em)
      }
      #it.body
    ]
  }

  show heading.where(level: 3): it => {
    set text(size: 13pt, weight: "bold", style: "italic", fill: dark_navy)
    block(above: 26pt, below: 16pt)[
      #if it.numbering != none {
        counter(heading).display(it.numbering)
        h(0.4em)
      }
      #it.body
    ]
  }

  // Tiện ích ẩn số hoặc ẩn khỏi mục lục
  show selector(<nonumber>): set heading(numbering: none)
  show selector(<nooutlined>): set heading(outlined: false)
  show selector(<hidden>): set heading(numbering: none, outlined: false)

  // --- C. ĐỊNH DẠNG MỤC LỤC CHUẨN LATEX ---
  // Cách ly TOC khỏi par.spacing chung bằng spacing: 0pt, dùng v() thủ công
  show outline: set par(first-line-indent: 0pt, spacing: 0pt)
  show outline.entry: set par(first-line-indent: 0pt, spacing: 0pt)

  show outline.entry.where(level: 1): it => {
    v(36pt, weak: true)
    let pfx = if it.prefix() != none {
      context {
        let loc = it.element.location()
        let num = counter(heading).at(loc)
        str(num.at(0)) + h(0.8em)
      }
    } else { none }
    strong(link(it.element.location())[
      #text(fill: dark_navy)[#pfx#it.body()]
      #h(1fr)
      #text(fill: dark_navy)[#it.page()]
    ])
  }

  show outline.entry.where(level: 2): it => {
    v(20pt, weak: true)
    let pfx = if it.prefix() != none {
      context {
        let loc = it.element.location()
        let num = counter(heading).at(loc)
        str(num.at(0)) + "." + str(num.at(1)) + h(0.6em)
      }
    } else { none }
    h(1.2em)
    link(it.element.location())[
      #text(fill: dark_navy)[#pfx#it.body()]
      #box(width: 1fr, align(center, text(fill: gray.darken(20%), repeat[.#h(10pt)] + h(10pt))))
      #text(fill: dark_navy)[#it.page()]
    ]
  }

  show outline.entry.where(level: 3): it => {
    v(10pt, weak: true)
    let pfx = if it.prefix() != none {
      context {
        let loc = it.element.location()
        let num = counter(heading).at(loc)
        str(num.at(0)) + "." + str(num.at(1)) + "." + str(num.at(2)) + h(0.5em)
      }
    } else { none }
    h(2.4em)
    link(it.element.location())[
      #text(fill: dark_navy)[#pfx#it.body()]
      #box(width: 1fr, align(center, text(fill: gray.darken(20%), repeat[.#h(10pt)] + h(10pt))))
      #text(fill: dark_navy)[#it.page()]
    ]
  }

  // --- D. ĐỊNH DẠNG CAPTION HÌNH ẢNH, BẢNG BIỂU, CODE ---
  show figure.where(kind: table): set figure(supplement: [Bảng])
  show figure.where(kind: image): set figure(supplement: [Hình])
  show figure.where(kind: raw): set figure(supplement: [Listing])

  show figure.where(kind: table): set figure.caption(position: top)
  show figure.where(kind: image): set figure.caption(position: bottom)
  show figure.where(kind: raw): set figure.caption(position: bottom)

  show figure.caption: it => [
    #set text(size: 12pt)
    #text(weight: "bold", fill: hcmus_blue)[#it.supplement #it.counter.display(it.numbering):]
    #h(0.4em)
    #it.body
  ]

  show table.cell: set par(justify: false, first-line-indent: 0pt)
  show figure: set block(above: 14pt, below: 14pt)

  // --- E. CẤU HÌNH TOÁN HỌC VỚI EQUATE ---
  show: equate.with(breakable: true, sub-numbering: true)
  set math.equation(numbering: "(1)")
  show math.equation.where(block: true): set block(above: 12pt, below: 12pt)

  // --- F. CẤU HÌNH MÃ NGUỒN VỚI CODLY ---
  show: codly-init.with()
  codly(
    stroke: 0.6pt + code_border,
    fill: code_bg,
    zebra-fill: none,
    radius: 0pt,
    display-icon: false,
    display-name: false,
    number-format: (num) => text(size: 8.5pt, fill: gray.darken(20%))[#num],
    inset: (x: 8pt, y: 0.28em),
  )
  show raw: set text(font: "Consolas", size: 10.5pt)
  show raw.where(block: true): set par(spacing: 0pt, leading: 0.45em)

  // --- G. ĐỊNH NGHĨA HỆ THỐNG HEADER/FOOTER (CHIC-HDR) ---
  let chic_setup = chic.with(
    chic-header(
      side-width: (65%, 0%, 35%),
      left-side: context {
        if not is_project_report and here().page() == 1 {
          none
        } else {
          text(size: 12pt, weight: "bold", fill: dark_navy)[#course_id: #course_name]
        }
      },
      right-side: context {
        if not is_project_report and here().page() == 1 {
          none
        } else {
          pad(right: 21.5pt)[
            #text(size: 12pt, weight: "bold", fill: hcmus_blue)[Khoa CNTT -- ĐHKHTN]
          ]
        }
      },
    ),
    chic-footer(
      side-width: (65%, 0%, 35%),
      left-side: context {
        if not is_project_report and here().page() == 1 {
          none
        } else {
          text(size: 12pt, style: "italic", fill: gray)[#report_subtitle]
        }
      },
      right-side: context {
        if not is_project_report and here().page() == 1 {
          pad(right: 21.5pt)[
            #text(size: 12pt, weight: "bold", fill: dark_navy)[
              Trang #counter(page).display("1")
            ]
          ]
        } else {
          pad(right: 21.5pt)[
            #text(size: 12pt, weight: "bold", fill: dark_navy)[
              Trang #counter(page).display("1")/#counter(page).final().at(0)
            ]
          ]
        }
      },
    ),
    chic-separator(
      context {
        if not is_project_report and here().page() == 1 {
          none
        } else {
          line(length: 100%, stroke: 0.6pt + dark_navy.lighten(40%))
        }
      },
      on: "header",
    ),
    chic-separator(
      context {
        if not is_project_report and here().page() == 1 {
          none
        } else {
          line(length: 100%, stroke: 0.5pt + dark_navy.lighten(40%))
        }
      },
      on: "footer",
    ),
    chic-offset(8pt),
  )

  // --- H. XUẤT NỘI DUNG THEO CHẾ ĐỘ ---
  if is_project_report {
    // 1. Trang bìa
    make_cover_page(
      course_id: course_id,
      course_name: course_name,
      report_subtitle: report_subtitle,
      report_title: report_title,
      instructor: instructor,
      class_id: class_id,
      academic_year: academic_year,
      students: students,
      logo_path: logo_path,
    )

    // 2. Trang Mục lục (Đánh số La Mã ở góc dưới phải, không header)
    set page(
      numbering: "i",
      header: none,
      footer: context align(right, text(size: 9pt, weight: "bold", fill: dark_navy)[
        Trang #counter(page).display("i")
      ]),
    )
    counter(page).update(1)
    set par(first-line-indent: 0pt)
    outline(title: toc_title, depth: 3, indent: 0pt)
    pagebreak()

    // 3. Chuẩn bị nội dung chính
    counter(page).update(1)
    set page(numbering: "1")
    show: chic_setup

    body
  } else {
    // Chế độ bài tập ngắn: kích hoạt chic_setup trước khi render nội dung
    // để không phát sinh pagebreak ngầm do `set page` giữa chừng
    show: chic_setup
    make_assignment_header(
      course_id: course_id,
      course_name: course_name,
      report_subtitle: report_subtitle,
      report_title: report_title,
      instructor: instructor,
      class_id: class_id,
      academic_year: academic_year,
      students: students,
      logo_path: logo_path,
    )
    body
  }
}

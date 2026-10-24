// ==============================================================================
// CÁC THÀNH PHẦN GIAO DIỆN (COMPONENTS) CHUẨN FIT - HCMUS
// ==============================================================================

#let hcmus_blue = rgb("#003366")
#let fit_blue = rgb("#005CA9")
#let dark_navy = rgb("#1A2B4C")

// Màu hộp callout theo chuẩn tcolorbox trong fit_hcmus.sty
#let light_blue_bg = rgb("#F0F5FA")
#let border_blue = rgb("#005CA9")
#let title_blue = rgb("#003366")

#let light_green_bg = rgb("#F2F9F4")
#let border_green = rgb("#4CAF50")
#let title_green = rgb("#1E5D22")

#let light_orange_bg = rgb("#FFF9F2")
#let border_orange = rgb("#FF9800")
#let title_orange = rgb("#B26A00")

// ==============================================================================
// 1. HỘP CHÚ THÍCH (CALLOUT BOXES: NOTE, TIP, WARNING)
// ==============================================================================
#let callout(
  title,
  body,
  fill_color: light_blue_bg,
  border_color: border_blue,
  title_color: title_blue,
  title_bg: none,
) = {
  let t_bg = if title_bg != none { title_bg } else { border_color.lighten(35%) }
  block(
    width: 100%,
    stroke: (left: 4pt + border_color, rest: 1.2pt + border_color),
    radius: 3pt,
    clip: true,
  )[
    #set par(spacing: 0pt, leading: 0.65em, first-line-indent: 0pt)
    #if title != none [
      #block(
        width: 100%,
        fill: t_bg,
        inset: (x: 8pt, y: 5pt),
      )[
        #text(size: 11pt, weight: "bold", fill: title_color)[#title]
      ]
    ]
    #block(
      width: 100%,
      fill: fill_color,
      inset: (x: 8pt, top: 6pt, bottom: 6pt),
    )[
      #set par(first-line-indent: 0pt, justify: true, leading: 0.65em)
      #body
    ]
  ]
}

#let callout_note(body, title: [Ghi chú]) = callout(
  title,
  body,
  fill_color: light_blue_bg,
  border_color: border_blue,
  title_color: title_blue,
  title_bg: border_blue.lighten(40%),
)

#let callout_tip(body, title: [Mẹo hay]) = callout(
  title,
  body,
  fill_color: light_green_bg,
  border_color: border_green,
  title_color: title_green,
  title_bg: border_green.lighten(25%),
)

#let callout_warning(body, title: [Cảnh báo / Lưu ý quan trọng]) = callout(
  title,
  body,
  fill_color: light_orange_bg,
  border_color: border_orange,
  title_color: title_orange,
  title_bg: border_orange.lighten(30%),
)

// ==============================================================================
// 2. KHỐI MÃ GIẢ / THUẬT TOÁN (ALGORITHM BOX)
// ==============================================================================
#let algorithm_counter = counter("algorithm")

#let algorithm_box(title, ..args) = {
  algorithm_counter.step()
  let pos = args.pos()
  let named = args.named()

  let input = if "input" in named {
    named.input
  } else if pos.len() > 0 and type(pos.at(0)) != array {
    pos.at(0)
  } else {
    none
  }

  let output = if "output" in named {
    named.output
  } else if pos.len() > 1 and type(pos.at(1)) != array {
    pos.at(1)
  } else {
    none
  }

  let steps = if "steps" in named {
    named.steps
  } else if pos.len() > 2 and type(pos.at(2)) == array {
    pos.at(2)
  } else if pos.len() > 0 and type(pos.last()) == array {
    pos.last()
  } else {
    ()
  }

  block(width: 100%, breakable: false)[
    #set par(justify: false, first-line-indent: 0pt, leading: 0.55em, spacing: 0pt)
    #line(length: 100%, stroke: 1pt + black)
    #v(6pt)
    #context [
      #text(weight: "bold")[Thuật toán #algorithm_counter.display("1"):]
      #h(0.4em)
      #title
    ]
    #v(5pt)
    #line(length: 100%, stroke: 0.6pt + black)
    #v(8pt)
    #if input != none [
      #text(weight: "bold")[Đầu vào:] #h(0.4em) #input \
      #v(6pt)
    ]
    #if output != none [
      #text(weight: "bold")[Đầu ra:] #h(0.4em) #output \
      #v(6pt)
    ]
    #grid(
      columns: (1.2em, 1fr),
      column-gutter: 8pt,
      row-gutter: 7pt,
      align: (right, left),
      ..steps.enumerate().map(((index, step)) => (
        text(size: 13pt, fill: gray.darken(25%))[#(index + 1):],
        step,
      )).flatten(),
    )
    #v(6pt)
    #line(length: 100%, stroke: 0.6pt + black)
  ]
}

// ==============================================================================
// 3. TIỆN ÍCH BẢNG BIỂU CÓ ĐỊNH DẠNG (STYLED TABLE HELPER)
// ==============================================================================
#let styled_table(
  columns,
  header,
  data,
  caption: none,
  inset: 6pt,
  stroke_color: rgb("#E0E5ED"),
) = {
  let content = table(
    columns: columns,
    align: (center + horizon,) * (columns.len()),
    stroke: 0.5pt + stroke_color,
    fill: (col, row) => if row == 0 {
      hcmus_blue
    } else if calc.even(row) {
      white
    } else {
      light_blue_bg
    },
    inset: inset,
    table.header(..header.map(h => text(fill: white, weight: "bold", h))),
    ..data,
  )

  if caption != none {
    figure(content, caption: caption)
  } else {
    content
  }
}

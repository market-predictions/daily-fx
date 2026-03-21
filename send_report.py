import os
import re
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ---------- COLOR SCHEME ----------
COLOR_TEXT = RGBColor(40, 40, 40)
COLOR_HEADING = RGBColor(47, 85, 151)       # dark blue
COLOR_ADD = RGBColor(0, 128, 0)             # green
COLOR_HOLD = RGBColor(0, 128, 0)            # green
COLOR_REDUCE = RGBColor(192, 128, 0)        # orange
COLOR_CLOSE = RGBColor(192, 0, 0)           # red
COLOR_LABEL = RGBColor(31, 78, 121)         # blue accent
COLOR_MUTED = RGBColor(90, 90, 90)

TABLE_HEADER_FILL = "D9EAF7"                # light blue
TABLE_ALT_FILL = "F7FBFF"                   # very light blue
TABLE_BORDER_COLOR = "A6A6A6"


# ---------- BASIC HELPERS ----------
def clean_md_inline(text: str) -> str:
    text = text.replace("**", "")
    text = text.replace("`", "")
    text = text.replace("<u>", "").replace("</u>", "")
    return text.strip()


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None, font_size: float = 10.0):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.bold = bold
    run.font.name = "Calibri"
    run.font.size = Pt(font_size)
    run.font.color.rgb = color or COLOR_TEXT


def set_document_layout(doc: Document) -> None:
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)

    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10.5)


def is_markdown_table_line(line: str) -> bool:
    line = line.strip()
    return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]


def is_markdown_separator_line(line: str) -> bool:
    line = line.strip()
    if not is_markdown_table_line(line):
        return False
    cells = [c.strip() for c in line.strip("|").split("|")]
    if not cells:
        return False
    for cell in cells:
        if not re.fullmatch(r":?-{3,}:?", cell):
            return False
    return True


def parse_markdown_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for i, line in enumerate(lines):
        if i == 1 and is_markdown_separator_line(line):
            continue
        cells = [clean_md_inline(c) for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


# ---------- WORD STYLING HELPERS ----------
def add_colored_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_heading("", level=level)
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Calibri"
    run.font.color.rgb = COLOR_HEADING

    if level == 0:
        run.font.size = Pt(20)
    elif level == 1:
        run.font.size = Pt(16)
    elif level == 2:
        run.font.size = Pt(13)
    else:
        run.font.size = Pt(11.5)


def add_normal_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(clean_md_inline(text))
    run.font.name = "Calibri"
    run.font.size = Pt(10.5)
    run.font.color.rgb = COLOR_TEXT


def add_bold_label_paragraph(doc: Document, label: str, rest: str = "", label_color: RGBColor = COLOR_LABEL) -> None:
    p = doc.add_paragraph()
    r1 = p.add_run(label)
    r1.bold = True
    r1.font.name = "Calibri"
    r1.font.size = Pt(10.5)
    r1.font.color.rgb = label_color

    if rest:
        r2 = p.add_run(rest)
        r2.font.name = "Calibri"
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = COLOR_TEXT


def add_action_header(doc: Document, text: str) -> None:
    """
    Styles lines like:
    ❌ Close
    ➖ Reduce
    ✅ Hold
    ➕ Add
    🔁 Replace
    """
    clean = clean_md_inline(text)
    p = doc.add_paragraph()

    # Try split icon and label
    parts = clean.split(" ", 1)
    icon = parts[0]
    label = parts[1] if len(parts) > 1 else ""

    color = COLOR_LABEL
    if "Close" in clean:
        color = COLOR_CLOSE
    elif "Reduce" in clean:
        color = COLOR_REDUCE
    elif "Hold" in clean:
        color = COLOR_HOLD
    elif "Add" in clean:
        color = COLOR_ADD
    elif "Replace" in clean:
        color = COLOR_LABEL

    r1 = p.add_run(icon + " ")
    r1.bold = True
    r1.font.name = "Segoe UI Symbol"
    r1.font.size = Pt(12)
    r1.font.color.rgb = color

    r2 = p.add_run(label)
    r2.bold = True
    r2.font.name = "Calibri"
    r2.font.size = Pt(11.5)
    r2.font.color.rgb = color


def add_bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(clean_md_inline(text))
    run.font.name = "Calibri"
    run.font.size = Pt(10.5)
    run.font.color.rgb = COLOR_TEXT


def add_numbered(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(clean_md_inline(text))
    run.font.name = "Calibri"
    run.font.size = Pt(10.5)
    run.font.color.rgb = COLOR_TEXT


def add_styled_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return

    max_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=max_cols)
    table.style = "Table Grid"

    for r_idx, row in enumerate(rows):
        for c_idx in range(max_cols):
            value = row[c_idx] if c_idx < len(row) else ""
            cell = table.cell(r_idx, c_idx)

            if r_idx == 0:
                set_cell_text(cell, value, bold=True, color=COLOR_TEXT, font_size=10)
                set_cell_shading(cell, TABLE_HEADER_FILL)
            else:
                set_cell_text(cell, value, bold=False, color=COLOR_TEXT, font_size=10)
                if r_idx % 2 == 0:
                    set_cell_shading(cell, TABLE_ALT_FILL)

    doc.add_paragraph("")


# ---------- CONTENT PARSING ----------
def is_label_line(text: str) -> bool:
    """
    For lines like:
    - **Primary regime:** Late-Cycle Inflationary
    - Primary regime: Late-Cycle Inflationary
    """
    cleaned = clean_md_inline(text)
    return ":" in cleaned and len(cleaned.split(":", 1)[0]) <= 45


def add_smart_paragraph(doc: Document, line: str) -> None:
    cleaned = clean_md_inline(line)

    # Bullet
    if cleaned.startswith("- "):
        add_bullet(doc, cleaned[2:])
        return

    # Numbered list
    if re.match(r"^\d+\.\s+", cleaned):
        add_numbered(doc, re.sub(r"^\d+\.\s+", "", cleaned))
        return

    # Action headers
    if any(cleaned.startswith(prefix) for prefix in ["❌ ", "➖ ", "✅ ", "➕ ", "🔁 "]):
        add_action_header(doc, cleaned)
        return

    # Label lines
    if is_label_line(cleaned):
        label, rest = cleaned.split(":", 1)
        add_bold_label_paragraph(doc, f"{label.strip()}:", f" {rest.strip()}")
        return

    add_normal_paragraph(doc, cleaned)


def build_docx_from_markdown(md_text: str, output_path: Path, send_date_str: str) -> None:
    doc = Document()
    set_document_layout(doc)

    add_colored_heading(doc, f"Weekly Report Review {send_date_str}", level=0)

    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            doc.add_paragraph("")
            i += 1
            continue

        # Table block
        if i + 1 < len(lines) and is_markdown_table_line(lines[i]) and is_markdown_separator_line(lines[i + 1]):
            table_lines = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and is_markdown_table_line(lines[i]):
                table_lines.append(lines[i])
                i += 1

            rows = parse_markdown_table(table_lines)
            add_styled_table(doc, rows)
            continue

        # Headings
        if line.startswith("# "):
            add_colored_heading(doc, clean_md_inline(line[2:]), level=1)
            i += 1
            continue

        if line.startswith("## "):
            add_colored_heading(doc, clean_md_inline(line[3:]), level=2)
            i += 1
            continue

        if line.startswith("### "):
            sub = clean_md_inline(line[4:])
            if any(sub.startswith(prefix) for prefix in ["❌ ", "➖ ", "✅ ", "➕ ", "🔁 "]):
                add_action_header(doc, sub)
            else:
                add_colored_heading(doc, sub, level=3)
            i += 1
            continue

        add_smart_paragraph(doc, line)
        i += 1

    doc.save(output_path)


# ---------- EMAIL BODY ----------
def extract_section(md_text: str, section_number: int) -> list[str]:
    lines = md_text.splitlines()
    result = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if re.match(rf"^##\s+{section_number}\.", stripped):
            in_section = True
            result.append(stripped)
            continue

        if in_section and re.match(r"^##\s+\d+\.", stripped):
            break

        if in_section:
            result.append(line)

    return result


def extract_summary_and_rotation(md_text: str) -> str:
    lines = md_text.splitlines()

    body_lines = []
    in_exec = False
    in_bottom = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## 1."):
            in_exec = True
            in_bottom = False
            body_lines.append("WEEKLY ETF PORTFOLIO REVIEW\n")
            continue

        if stripped.startswith("## 11."):
            in_exec = False
            in_bottom = True
            body_lines.append("\nBOTTOM LINE\n")
            continue

        if stripped.startswith("## ") and not stripped.startswith("## 1.") and not stripped.startswith("## 11."):
            in_exec = False
            in_bottom = False

        if in_exec or in_bottom:
            if stripped:
                body_lines.append(clean_md_inline(stripped))

    section8 = extract_section(md_text, 8)
    if section8:
        body_lines.append("\nPORTFOLIO ROTATION PLAN\n")
        for line in section8:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r"^##\s+8\.", stripped):
                continue
            if stripped.startswith("### "):
                body_lines.append(clean_md_inline(stripped[4:]))
            elif stripped.startswith("- "):
                body_lines.append(f"• {clean_md_inline(stripped[2:])}")
            else:
                body_lines.append(clean_md_inline(stripped))

    body_lines.append("\nFull formatted report is attached as a Word document.")
    return "\n".join(body_lines).strip()


# ---------- MAIN ----------
def main() -> None:
    output_dir = Path("output")
    reports = sorted(output_dir.glob("weekly_analysis_*.md"))

    if not reports:
        raise FileNotFoundError("No weekly_analysis_*.md file found in output/")

    latest_report = reports[-1]
    md_text = latest_report.read_text(encoding="utf-8")

    send_date_str = datetime.now().strftime("%Y-%m-%d")

    docx_path = latest_report.with_name(f"weekly_report_review_{send_date_str}.docx")
    build_docx_from_markdown(md_text, docx_path, send_date_str)

    subject = f"Weekly Report Review {send_date_str}"
    body = extract_summary_and_rotation(md_text)

    smtp_host = os.environ["MRKT_RPRTS_SMTP_HOST"]
    smtp_port = int(os.environ.get("MRKT_RPRTS_SMTP_PORT") or "587")
    smtp_user = os.environ["MRKT_RPRTS_SMTP_USER"]
    smtp_pass = os.environ["MRKT_RPRTS_SMTP_PASS"]
    mail_from = os.environ["MRKT_RPRTS_MAIL_FROM"]
    mail_to = os.environ["MRKT_RPRTS_MAIL_TO"]

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(docx_path, "rb") as f:
        attachment = MIMEApplication(
            f.read(),
            _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=docx_path.name,
        )
        msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], msg.as_string())

    print(f"Sent email for {latest_report.name} with attachment {docx_path.name}")


if __name__ == "__main__":
    main()

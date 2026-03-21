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


# ---------- COLORS ----------
COLOR_TEXT = RGBColor(40, 40, 40)
COLOR_HEADING = RGBColor(47, 85, 151)          # dark blue
COLOR_LABEL = RGBColor(31, 78, 121)            # blue accent
COLOR_MUTED = RGBColor(90, 90, 90)

COLOR_ADD = RGBColor(0, 128, 0)
COLOR_HOLD = RGBColor(0, 128, 0)
COLOR_REDUCE = RGBColor(192, 128, 0)
COLOR_CLOSE = RGBColor(192, 0, 0)

COLOR_OVERWEIGHT = RGBColor(0, 128, 0)
COLOR_NEUTRAL = RGBColor(192, 128, 0)
COLOR_UNDERWEIGHT = RGBColor(192, 0, 0)

TABLE_HEADER_FILL = "D9EAF7"
TABLE_ALT_FILL = "F7FBFF"
PRO_HEADER_FILL = "E2F0D9"
CONTRA_HEADER_FILL = "FCE4D6"


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


def paragraph_run(paragraph, text, bold=False, color=None, size=10.5, font="Calibri"):
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color or COLOR_TEXT
    return run


def add_colored_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_heading("", level=level)
    size_map = {0: 20, 1: 16, 2: 13, 3: 11.5}
    paragraph_run(p, text, bold=True, color=COLOR_HEADING, size=size_map.get(level, 11.5))


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
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_markdown_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for i, line in enumerate(lines):
        if i == 1 and is_markdown_separator_line(line):
            continue
        cells = [clean_md_inline(c) for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


# ---------- FUNCTIONAL COLORS ----------
def color_for_term(text: str):
    t = text.lower().strip()

    if "overweight" in t:
        return COLOR_OVERWEIGHT
    if "underweight" in t:
        return COLOR_UNDERWEIGHT
    if t == "neutral" or " neutral" in t:
        return COLOR_NEUTRAL

    if "add" == t or t.startswith("add "):
        return COLOR_ADD
    if "hold" == t or t.startswith("hold "):
        return COLOR_HOLD
    if "reduce" == t or t.startswith("reduce "):
        return COLOR_REDUCE
    if "close" == t or t.startswith("close "):
        return COLOR_CLOSE

    return COLOR_TEXT


def add_label_paragraph(doc: Document, label: str, rest: str = "") -> None:
    p = doc.add_paragraph()
    paragraph_run(p, label, bold=True, color=COLOR_LABEL)
    if rest:
        paragraph_run(p, " " + rest, color=color_for_term(rest))


def add_action_header(doc: Document, text: str) -> None:
    clean = clean_md_inline(text)
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

    p = doc.add_paragraph()
    paragraph_run(p, icon + " ", bold=True, color=color, size=12, font="Segoe UI Symbol")
    paragraph_run(p, label, bold=True, color=color, size=11.5)


def add_bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    paragraph_run(p, clean_md_inline(text), color=color_for_term(text))


def add_numbered(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Number")
    paragraph_run(p, clean_md_inline(text), color=COLOR_TEXT)


def add_normal_paragraph(doc: Document, text: str) -> None:
    cleaned = clean_md_inline(text)

    if ":" in cleaned and len(cleaned.split(":", 1)[0]) <= 45:
        label, rest = cleaned.split(":", 1)
        add_label_paragraph(doc, f"{label.strip()}:", rest.strip())
        return

    p = doc.add_paragraph()
    paragraph_run(p, cleaned, color=color_for_term(cleaned))


# ---------- TABLE STYLING ----------
def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None, font_size: float = 10.0):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph_run(p, text, bold=bold, color=color or COLOR_TEXT, size=font_size)


def is_pro_contra_table(rows: list[list[str]]) -> bool:
    """
    Detect 2-column, 4-row-ish table with pro/contra structure.
    """
    if len(rows) < 2:
        return False
    if len(rows[0]) != 2:
        return False

    headers = [c.lower().strip() for c in rows[0]]
    pro_like = any("pro" in h or "argument" in h for h in headers)
    contra_like = any("contra" in h or "invalidation" in h for h in headers)
    return pro_like and contra_like


def add_styled_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return

    max_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=max_cols)
    table.style = "Table Grid"

    pro_contra = is_pro_contra_table(rows)

    for r_idx, row in enumerate(rows):
        for c_idx in range(max_cols):
            value = row[c_idx] if c_idx < len(row) else ""
            cell = table.cell(r_idx, c_idx)

            if r_idx == 0:
                set_cell_text(cell, value, bold=True, color=COLOR_TEXT, font_size=10)
                if pro_contra and c_idx == 0:
                    set_cell_shading(cell, PRO_HEADER_FILL)
                elif pro_contra and c_idx == 1:
                    set_cell_shading(cell, CONTRA_HEADER_FILL)
                else:
                    set_cell_shading(cell, TABLE_HEADER_FILL)
            else:
                set_cell_text(cell, value, bold=False, color=color_for_term(value), font_size=10)
                if not pro_contra and r_idx % 2 == 0:
                    set_cell_shading(cell, TABLE_ALT_FILL)

    doc.add_paragraph("")


# ---------- DOCX BUILDER ----------
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

        # Markdown table block
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

        # Bullets
        cleaned = clean_md_inline(line)
        if cleaned.startswith("- "):
            add_bullet(doc, cleaned[2:])
            i += 1
            continue

        # Numbered
        if re.match(r"^\d+\.\s+", cleaned):
            add_numbered(doc, re.sub(r"^\d+\.\s+", "", cleaned))
            i += 1
            continue

        add_normal_paragraph(doc, cleaned)
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


def extract_top_opportunities(md_text: str, max_items: int = 4) -> list[str]:
    lines = md_text.splitlines()
    results = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### [Rank "):
            title = clean_md_inline(stripped.replace("### ", ""))
            results.append(title)
            if len(results) >= max_items:
                break
    return results


def build_email_body(md_text: str, send_date_str: str) -> str:
    """
    Maximum readability within email-body limitations.
    """
    lines = md_text.splitlines()

    body = []
    body.append(f"WEEKLY REPORT REVIEW {send_date_str}")
    body.append("=" * (22 + len(send_date_str)))
    body.append("")

    # Executive summary
    in_exec = False
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## 1."):
            in_exec = True
            body.append("EXECUTIVE SUMMARY")
            body.append("")
            continue

        if in_exec and stripped.startswith("## ") and not stripped.startswith("## 1."):
            break

        if in_exec and stripped:
            body.append(clean_md_inline(stripped))

    # Top opportunities
    top_ops = extract_top_opportunities(md_text)
    if top_ops:
        body.append("")
        body.append("TOP OPPORTUNITIES")
        body.append("")
        for item in top_ops:
            body.append(f"• {item}")

    # Rotation plan
    section8 = extract_section(md_text, 8)
    if section8:
        body.append("")
        body.append("PORTFOLIO ROTATION PLAN")
        body.append("")
        for line in section8:
            stripped = line.strip()
            if not stripped or re.match(r"^##\s+8\.", stripped):
                continue
            if stripped.startswith("### "):
                body.append(clean_md_inline(stripped[4:]))
            elif stripped.startswith("- "):
                body.append(f"  • {clean_md_inline(stripped[2:])}")
            else:
                body.append(clean_md_inline(stripped))

    # Bottom line
    in_bottom = False
    body.append("")
    body.append("BOTTOM LINE")
    body.append("")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 11."):
            in_bottom = True
            continue
        if in_bottom and stripped.startswith("## ") and not stripped.startswith("## 11."):
            break
        if in_bottom and stripped:
            body.append(clean_md_inline(stripped))

    body.append("")
    body.append("The full formatted report is attached as a Word document.")

    return "\n".join(body).strip()


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
    body = build_email_body(md_text, send_date_str)

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

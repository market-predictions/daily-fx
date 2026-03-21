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
from docx.shared import Inches, Pt


def clean_md_inline(text: str) -> str:
    text = text.replace("**", "")
    text = text.replace("`", "")
    text = text.replace("<u>", "").replace("</u>", "")
    return text.strip()


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
        if not cell:
            return False
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


def set_landscape(doc: Document) -> None:
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)


def style_normal_text(doc: Document) -> None:
    styles = doc.styles
    if "Normal" in styles:
        styles["Normal"].font.name = "Calibri"
        styles["Normal"].font.size = Pt(10.5)


def make_paragraph_bold(paragraph) -> None:
    if paragraph.runs:
        for run in paragraph.runs:
            run.bold = True
    else:
        run = paragraph.add_run(paragraph.text)
        run.bold = True


def add_docx_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return

    max_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=max_cols)
    table.style = "Table Grid"

    for r_idx, row in enumerate(rows):
        for c_idx in range(max_cols):
            value = row[c_idx] if c_idx < len(row) else ""
            table.cell(r_idx, c_idx).text = value

    # Header bold
    for cell in table.rows[0].cells:
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True


def is_section_header(line: str) -> bool:
    """
    Detects lines like:
    '## 8. 🔁 Portfolio rotation plan'
    """
    return bool(re.match(r"^##\s+\d+\.", line.strip()))


def is_subheader_like(line: str) -> bool:
    """
    Make lines bold in Word like:
    ### ❌ Close
    ### ➖ Reduce
    ### ✅ Hold
    ### ➕ Add
    ### 🔁 Replace
    """
    stripped = line.strip()
    return stripped.startswith("### ")


def build_docx_from_markdown(md_text: str, output_path: Path, send_date_str: str) -> None:
    doc = Document()
    set_landscape(doc)
    style_normal_text(doc)

    # Title with actual send date
    title = doc.add_heading(f"Weekly Report Review {send_date_str}", level=0)
    for run in title.runs:
        run.bold = True

    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.rstrip()

        if not line.strip():
            doc.add_paragraph("")
            i += 1
            continue

        # Detect markdown table block
        if (
            i + 1 < len(lines)
            and is_markdown_table_line(lines[i])
            and is_markdown_separator_line(lines[i + 1])
        ):
            table_lines = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and is_markdown_table_line(lines[i]):
                table_lines.append(lines[i])
                i += 1

            rows = parse_markdown_table(table_lines)
            add_docx_table(doc, rows)
            doc.add_paragraph("")
            continue

        # Main headings
        if line.startswith("# "):
            p = doc.add_heading(clean_md_inline(line[2:]), level=1)
            make_paragraph_bold(p)
            i += 1
            continue

        if line.startswith("## "):
            p = doc.add_heading(clean_md_inline(line[3:]), level=2)
            make_paragraph_bold(p)
            i += 1
            continue

        if line.startswith("### "):
            p = doc.add_heading(clean_md_inline(line[4:]), level=3)
            make_paragraph_bold(p)
            i += 1
            continue

        # Bullets
        if line.startswith("- "):
            doc.add_paragraph(clean_md_inline(line[2:]), style="List Bullet")
            i += 1
            continue

        # Numbered list
        stripped = line.lstrip()
        if re.match(r"^\d+\.\s+", stripped):
            text = re.sub(r"^\d+\.\s+", "", stripped)
            doc.add_paragraph(clean_md_inline(text), style="List Number")
            i += 1
            continue

        # Normal paragraph
        p = doc.add_paragraph(clean_md_inline(line))

        # Make subheader-like normal lines bold if needed
        if is_section_header(line) or is_subheader_like(line):
            make_paragraph_bold(p)

        i += 1

    doc.save(output_path)


def extract_section(md_text: str, section_number: int) -> list[str]:
    """
    Extract lines for a section like ## 8. ...
    """
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
    """
    Email body:
    - Executive summary
    - Bottom line
    - Section 8 Portfolio rotation plan
    """
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

    # Add section 8 with icons
    section8 = extract_section(md_text, 8)
    if section8:
        body_lines.append("\nPORTFOLIO ROTATION PLAN\n")

        for line in section8:
            stripped = line.strip()
            if not stripped:
                continue

            # Skip original section title if you want cleaner body
            if re.match(r"^##\s+8\.", stripped):
                continue

            if stripped.startswith("### "):
                body_lines.append(clean_md_inline(stripped[4:]))
            elif stripped.startswith("- "):
                body_lines.append(f"• {clean_md_inline(stripped[2:])}")
            else:
                body_lines.append(clean_md_inline(stripped))

    if not body_lines:
        fallback = [clean_md_inline(ln) for ln in lines if ln.strip()]
        body_lines = fallback[:25]

    summary = "\n".join(body_lines).strip()
    summary += "\n\nFull formatted report is attached as a Word document."
    return summary


def main() -> None:
    output_dir = Path("output")
    reports = sorted(output_dir.glob("weekly_analysis_*.md"))

    if not reports:
        raise FileNotFoundError("No weekly_analysis_*.md file found in output/")

    latest_report = reports[-1]
    md_text = latest_report.read_text(encoding="utf-8")

    # Actual send date
    send_date_str = datetime.now().strftime("%Y-%m-%d")

    # DOCX filename
    docx_path = latest_report.with_name(f"weekly_report_review_{send_date_str}.docx")
    build_docx_from_markdown(md_text, docx_path, send_date_str)

    # Mail subject with actual send date
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

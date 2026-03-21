import os
import re
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

from docx import Document


def clean_md_inline(text: str) -> str:
    """Basic cleanup of inline markdown markers."""
    text = text.replace("**", "")
    text = text.replace("`", "")
    text = text.replace("<u>", "").replace("</u>", "")
    return text.strip()


def is_markdown_table_line(line: str) -> bool:
    line = line.strip()
    return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]


def is_markdown_separator_line(line: str) -> bool:
    """
    Detect markdown table separator like:
    |---|---:|:---:|
    """
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
    """
    Convert markdown table lines into rows.
    Expects:
    row 0 = header
    row 1 = separator
    row 2+ = body
    """
    rows = []
    for i, line in enumerate(lines):
        if i == 1 and is_markdown_separator_line(line):
            continue
        cells = [clean_md_inline(c) for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


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

    # Make header row bold-ish by using paragraph runs
    for cell in table.rows[0].cells:
        if cell.paragraphs and cell.paragraphs[0].runs:
            for run in cell.paragraphs[0].runs:
                run.bold = True


def build_docx_from_markdown(md_text: str, output_path: Path, report_date_str: str) -> None:
    """
    Improved markdown-to-docx converter.
    - Converts markdown headings
    - Converts bullets / numbered lists
    - Converts markdown tables into real Word tables
    - Adds report title with date
    """
    doc = Document()

    # Main title with date
    doc.add_heading(f"Weekly ETF Portfolio Review - {report_date_str}", level=0)

    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.rstrip()

        # Skip extra blank lines
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

        # Headings
        if line.startswith("# "):
            doc.add_heading(clean_md_inline(line[2:]), level=1)
            i += 1
            continue
        if line.startswith("## "):
            doc.add_heading(clean_md_inline(line[3:]), level=2)
            i += 1
            continue
        if line.startswith("### "):
            doc.add_heading(clean_md_inline(line[4:]), level=3)
            i += 1
            continue

        # Bullet points
        if line.startswith("- "):
            doc.add_paragraph(clean_md_inline(line[2:]), style="List Bullet")
            i += 1
            continue

        # Numbered list items
        stripped = line.lstrip()
        if re.match(r"^\d+\.\s+", stripped):
            text = re.sub(r"^\d+\.\s+", "", stripped)
            doc.add_paragraph(clean_md_inline(text), style="List Number")
            i += 1
            continue

        # Normal paragraph
        doc.add_paragraph(clean_md_inline(line))
        i += 1

    doc.save(output_path)


def extract_summary(md_text: str) -> str:
    """
    Build a short email body from the report.
    Focus on Executive Summary and Bottom Line.
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

    if not body_lines:
        # Fallback: first non-empty lines
        fallback = [clean_md_inline(ln) for ln in lines if ln.strip()]
        body_lines = fallback[:25]

    summary = "\n".join(body_lines).strip()
    summary += "\n\nFull formatted report is attached as a Word document."
    return summary


def extract_report_date(latest_report: Path) -> tuple[str, str]:
    """
    From filename like weekly_analysis_260320.md
    return:
    - display date: 2026-03-20
    - compact date: 260320
    """
    m = re.search(r"weekly_analysis_(\d{6})", latest_report.stem)
    if not m:
        today = datetime.now().strftime("%Y-%m-%d")
        compact = datetime.now().strftime("%y%m%d")
        return today, compact

    compact = m.group(1)
    dt = datetime.strptime(compact, "%y%m%d")
    return dt.strftime("%Y-%m-%d"), compact


def main() -> None:
    output_dir = Path("output")
    reports = sorted(output_dir.glob("weekly_analysis_*.md"))

    if not reports:
        raise FileNotFoundError("No weekly_analysis_*.md file found in output/")

    latest_report = reports[-1]
    md_text = latest_report.read_text(encoding="utf-8")

    report_date_display, report_date_compact = extract_report_date(latest_report)

    # Build nicer docx filename with date
    docx_path = latest_report.with_name(f"weekly_analysis_{report_date_compact}.docx")
    build_docx_from_markdown(md_text, docx_path, report_date_display)

    subject = f"Weekly ETF Portfolio Review - {report_date_display}"
    body = extract_summary(md_text)

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

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
from docx.opc.constants import RELATIONSHIP_TYPE as RT


# ---------- COLORS ----------
COLOR_TEXT = RGBColor(40, 40, 40)
COLOR_HEADING = RGBColor(47, 85, 151)
COLOR_LABEL = RGBColor(31, 78, 121)
COLOR_MUTED = RGBColor(90, 90, 90)

COLOR_ADD = RGBColor(0, 128, 0)
COLOR_HOLD = RGBColor(0, 128, 0)
COLOR_REDUCE = RGBColor(192, 128, 0)
COLOR_CLOSE = RGBColor(192, 0, 0)

TABLE_HEADER_FILL = "D9EAF7"
TABLE_ALT_FILL = "F7FBFF"
PRO_HEADER_FILL = "E2F0D9"
CONTRA_HEADER_FILL = "FCE4D6"
DISCLAIMER_FILL = "F3F4F6"
RADAR_FILL = "FFF4E5"


# ---------- CLEANUP ----------
def strip_citations(text: str) -> str:
    patterns = [
        r"cite.*?",
        r"filecite.*?",
        r"\[\d+\]",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def clean_md_inline(text: str) -> str:
    text = strip_citations(text)
    text = text.replace("**", "")
    text = text.replace("`", "")
    text = text.replace("<u>", "").replace("</u>", "")
    return re.sub(r"\s+", " ", text).strip()


def is_markdown_link_line(text: str) -> bool:
    return bool(re.match(r"^\[.*?\]\(https?://.*?\)$", text.strip()))


# ---------- DOCX HELPERS ----------
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


def paragraph_run(paragraph, text, bold=False, color=None, size=10.5, italic=False, font="Calibri"):
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color or COLOR_TEXT
    return run


def add_heading(doc: Document, text: str, level: int) -> None:
    p = doc.add_heading("", level=level)
    size_map = {0: 20, 1: 16, 2: 13, 3: 11.5}
    paragraph_run(p, text, bold=True, color=COLOR_HEADING, size=size_map.get(level, 11.5))


def set_paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    p_pr.append(shd)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def add_note_callout(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    set_paragraph_shading(p, DISCLAIMER_FILL)
    paragraph_run(p, "Note ", bold=True, color=COLOR_LABEL, size=9.5)
    paragraph_run(p, text, italic=True, size=9.5)


def add_hyperlink(paragraph, text: str, url: str, color="0563C1", underline=True):
    part = paragraph.part
    r_id = part.relate_to(url, RT.HYPERLINK, is_external=True)

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")

    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    r_pr.append(c)

    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        r_pr.append(u)

    t = OxmlElement("w:t")
    t.text = text

    new_run.append(r_pr)
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def is_markdown_table_line(line: str) -> bool:
    line = line.strip()
    return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]


def is_markdown_separator_line(line: str) -> bool:
    line = line.strip()
    if not is_markdown_table_line(line):
        return False
    cells = [c.strip() for c in line.strip("|").split("|")]
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_markdown_table(lines):
    rows = []
    for i, line in enumerate(lines):
        if i == 1 and is_markdown_separator_line(line):
            continue
        rows.append([clean_md_inline(c) for c in line.strip().strip("|").split("|")])
    return rows


def color_for_term(text: str):
    t = text.lower().strip()
    if t.startswith("add") or "actionable now" in t:
        return COLOR_ADD
    if t.startswith("hold") or "watchlist" in t:
        return COLOR_HOLD
    if t.startswith("reduce") or "scale in slowly" in t:
        return COLOR_REDUCE
    if t.startswith("close") or "too early" in t:
        return COLOR_CLOSE
    return COLOR_TEXT


def set_cell_text(cell, text: str, bold=False, color=None, size=10.0):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph_run(p, text, bold=bold, color=color or COLOR_TEXT, size=size)


def add_styled_table(doc: Document, rows):
    if not rows:
        return

    max_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=max_cols)
    table.style = "Table Grid"

    headers = [c.lower() for c in rows[0]]
    is_pro_contra = len(rows[0]) == 2 and any("pro" in h for h in headers) and any("contra" in h for h in headers)
    is_radar = "theme" in headers[0] and "primary etf" in " ".join(headers)

    for r_idx, row in enumerate(rows):
        for c_idx in range(max_cols):
            value = row[c_idx] if c_idx < len(row) else ""
            cell = table.cell(r_idx, c_idx)
            if r_idx == 0:
                set_cell_text(cell, value, bold=True)
                if is_pro_contra and c_idx == 0:
                    set_cell_shading(cell, PRO_HEADER_FILL)
                elif is_pro_contra and c_idx == 1:
                    set_cell_shading(cell, CONTRA_HEADER_FILL)
                elif is_radar:
                    set_cell_shading(cell, RADAR_FILL)
                else:
                    set_cell_shading(cell, TABLE_HEADER_FILL)
            else:
                set_cell_text(cell, value, color=color_for_term(value))
                if not is_pro_contra and not is_radar and r_idx % 2 == 0:
                    set_cell_shading(cell, TABLE_ALT_FILL)

    doc.add_paragraph("")


PLAIN_SUBHEADERS = {
    "Assessment",
    "Prospective score",
    "Theme",
    "Why it fits now",
    "Why this beats current alternatives",
    "Technical analysis",
    "Second-order opportunity / threat map",
    "Replacement logic",
    "Why now rather than later",
    "Scorecard",
    "Macro invalidators",
    "Market-based invalidators",
    "Geopolitical invalidators",
    "Second-order invalidators",
    "Portfolio construction risks",
    "Top 3 actions this week",
    "Top 3 risks this week",
    "Best structural opportunities not yet actionable",
}


# ---------- DOCX BUILDER ----------
def build_docx_from_markdown(md_text: str, output_path: Path):
    doc = Document()
    set_document_layout(doc)

    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            doc.add_paragraph("")
            i += 1
            continue

        if line.startswith("# "):
            add_heading(doc, clean_md_inline(line[2:]), 0)
            i += 1
            continue

        if stripped.startswith("> **Note**"):
            note_text = ""
            if i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                note_text = clean_md_inline(lines[i + 1].strip().lstrip(">").strip())
                i += 1
            add_note_callout(doc, note_text or "This report is for informational and educational purposes only; please see the disclaimer at the end.")
            i += 1
            continue

        if is_markdown_link_line(stripped):
            m = re.match(r"^\[(.*?)\]\((https?://.*?)\)$", stripped)
            if m and "tradingview.com/chart/" in m.group(2):
                p = doc.add_paragraph()
                add_hyperlink(p, clean_md_inline(m.group(1)), m.group(2))
            i += 1
            continue

        if i + 1 < len(lines) and is_markdown_table_line(lines[i]) and is_markdown_separator_line(lines[i + 1]):
            table_lines = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and is_markdown_table_line(lines[i]):
                table_lines.append(lines[i])
                i += 1
            add_styled_table(doc, parse_markdown_table(table_lines))
            continue

        if line.startswith("## "):
            add_heading(doc, clean_md_inline(line[3:]), 1)
            i += 1
            continue

        if line.startswith("### "):
            add_heading(doc, clean_md_inline(line[4:]), 2)
            i += 1
            continue

        cleaned = clean_md_inline(line)

        if cleaned in PLAIN_SUBHEADERS:
            p = doc.add_paragraph()
            paragraph_run(p, cleaned, bold=True, color=COLOR_LABEL, size=11.5)
            i += 1
            continue

        if cleaned.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            paragraph_run(p, cleaned[2:], color=color_for_term(cleaned[2:]))
            i += 1
            continue

        if re.match(r"^\d+\.\s+", cleaned):
            p = doc.add_paragraph(style="List Number")
            paragraph_run(p, re.sub(r"^\d+\.\s+", "", cleaned))
            i += 1
            continue

        p = doc.add_paragraph()
        paragraph_run(p, cleaned, color=color_for_term(cleaned))
        i += 1

    doc.save(output_path)


# ---------- SECTION HELPERS ----------
def extract_section(md_text: str, header: str):
    lines = md_text.splitlines()
    result = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == header:
            in_section = True
            result.append(stripped)
            continue
        if in_section and re.match(r"^##\s+\d+\.", stripped):
            break
        if in_section:
            result.append(line)
    return result


def extract_bullets(lines):
    items = []
    for line in lines:
        s = line.strip()
        if s.startswith("- "):
            items.append(clean_md_inline(s[2:]))
        elif re.match(r"^\d+\.\s+", s):
            items.append(clean_md_inline(re.sub(r"^\d+\.\s+", "", s)))
    return items


def extract_label_pairs(lines):
    pairs = []
    for line in lines:
        s = clean_md_inline(line.strip())
        if not s or s.startswith("## "):
            continue
        if ":" in s:
            k, v = s.split(":", 1)
            pairs.append((k.strip(), v.strip()))
    return pairs


def extract_table_rows(lines, max_rows=5):
    table_lines = []
    started = False
    for line in lines:
        if is_markdown_table_line(line):
            table_lines.append(line)
            started = True
        elif started:
            break
    if len(table_lines) >= 2:
        rows = parse_markdown_table(table_lines)
        return rows[: max_rows + 1]
    return []


# ---------- HTML BODY ----------
def esc(text: str) -> str:
    text = clean_md_inline(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_chip(text: str, bg: str, fg: str = "#1F4E79") -> str:
    return f"<span style='display:inline-block;padding:4px 8px;border-radius:999px;background:{bg};color:{fg};font-size:12px;font-weight:700;margin:0 6px 6px 0;'>{esc(text)}</span>"


def render_action_snapshot(lines):
    blocks = []
    current_header = None
    current_items = []

    def flush():
        nonlocal current_header, current_items, blocks
        if not current_header:
            return
        color = "#1F4E79"
        if "Add" in current_header:
            color = "#008000"
        elif "Hold but replaceable" in current_header:
            color = "#C08000"
        elif "Hold" in current_header:
            color = "#008000"
        elif "Reduce" in current_header:
            color = "#C08000"
        elif "Close" in current_header:
            color = "#C00000"
        items_html = "".join(f"<li style='margin:0 0 4px 0;'>{esc(x)}</li>" for x in current_items)
        blocks.append(
            f"<div style='margin:0 0 14px 0;'><div style='font-weight:700;color:{color};margin-bottom:6px;font-size:15px;'>{esc(current_header)}</div><ul style='margin:0 0 0 18px;padding:0;line-height:1.5;'>{items_html}</ul></div>"
        )

    for line in lines:
        s = line.strip()
        if not s or re.match(r"^##\s+2\.", s):
            continue
        if s.startswith("### "):
            flush()
            current_header = clean_md_inline(s[4:])
            current_items = []
        elif s.startswith("- "):
            current_items.append(s[2:])
        elif re.match(r"^\d+\.\s+", s):
            current_items.append(re.sub(r"^\d+\.\s+", "", s))
    flush()
    return "".join(blocks)


def render_summary_pairs(lines):
    pairs = extract_label_pairs(lines)
    chips = []
    body = []
    for k, v in pairs:
        if k in {"Primary regime", "Secondary cross-current", "Geopolitical regime"}:
            chips.append(render_chip(f"{k}: {v}", "#EEF4FF"))
        else:
            body.append(f"<div style='margin:0 0 8px 0; line-height:1.5;'><strong>{esc(k)}:</strong> {esc(v)}</div>")
    return "".join(chips), "".join(body)


def render_html_table(rows, title):
    if not rows or len(rows) < 2:
        return ""
    headers = rows[0]
    body = rows[1:]
    thead = "".join(
        f"<th style='text-align:left;padding:8px 10px;border-bottom:1px solid #d9e2f0;background:#fff4e5;font-size:13px;'>{esc(h)}</th>"
        for h in headers
    )
    body_html = ""
    for idx, row in enumerate(body):
        cells = "".join(
            f"<td style='padding:8px 10px;border-bottom:1px solid #eef2f7;font-size:13px;vertical-align:top;'>{esc(c)}</td>"
            for c in row
        )
        bg = "#ffffff" if idx % 2 == 0 else "#fafcff"
        body_html += f"<tr style='background:{bg};'>{cells}</tr>"
    return f"""
    <div style="margin:18px 0 0 0;">
      <div style="font-size:17px;font-weight:700;color:#2F5597;margin-bottom:8px;">{esc(title)}</div>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e3eaf5;">
        <thead><tr>{thead}</tr></thead>
        <tbody>{body_html}</tbody>
      </table>
    </div>
    """


def build_email_body_html(md_text: str, send_date_str: str) -> str:
    summary = extract_section(md_text, "## 1. ✅ Executive summary")
    snapshot = extract_section(md_text, "## 2. 📌 Portfolio action snapshot")
    regime = extract_section(md_text, "## 3. 🧭 Regime dashboard")
    radar = extract_section(md_text, "## 4. 🚀 Structural Opportunity Radar")
    risks = extract_section(md_text, "## 5. 📅 Key risks / invalidators")
    bottom = extract_section(md_text, "## 6. 🧭 Bottom line")

    chips_html, summary_body = render_summary_pairs(summary)
    snapshot_html = render_action_snapshot(snapshot)
    radar_table = extract_table_rows(radar, max_rows=4)
    radar_text = [
        esc(line.strip())
        for line in radar
        if line.strip()
        and not line.strip().startswith("## ")
        and not line.strip().startswith("|")
        and not line.strip().startswith("### ")
    ]
    radar_note = radar_text[0] if radar_text else "See attached report for the full Structural Opportunity Radar, triggers, and implementation details."

    risk_items = extract_bullets(risks)[:5]
    risk_html = "".join(f"<li style='margin:0 0 5px 0;'>{esc(x)}</li>" for x in risk_items)

    bottom_items = extract_bullets(bottom)
    bottom_html = "".join(f"<div style='margin:0 0 8px 0; line-height:1.5;'>{esc(x)}</div>" for x in bottom_items)

    html = f"""
    <html>
      <body style="margin:0;padding:0;background:#f6f8fb;font-family:Calibri,Arial,sans-serif;color:#282828;">
        <div style="max-width:980px;margin:0 auto;padding:28px 20px;">
          <div style="background:#ffffff;border:1px solid #d9e2f0;border-radius:12px;padding:28px 30px;">
            <div style="font-size:26px;font-weight:700;color:#2F5597;margin-bottom:8px;">
              Weekly Report Review {send_date_str}
            </div>
            <div style="font-size:13px;color:#666666;margin-bottom:18px;padding:8px 10px;background:#f3f4f6;border-radius:6px;">
              <strong>Note</strong> — This report is for informational and educational purposes only; please see the disclaimer in the attached report.
            </div>

            <div style="margin-bottom:16px;">{chips_html}</div>
            <div style="margin-bottom:18px;">{summary_body}</div>

            <div style="display:grid;grid-template-columns:1.2fr 0.8fr;gap:18px;">
              <div style="background:#fafcff;border:1px solid #e3eaf5;border-radius:10px;padding:16px;">
                <div style="font-size:18px;font-weight:700;color:#2F5597;margin-bottom:10px;">Portfolio action snapshot</div>
                {snapshot_html}
              </div>
              <div style="background:#fafcff;border:1px solid #e3eaf5;border-radius:10px;padding:16px;">
                <div style="font-size:18px;font-weight:700;color:#2F5597;margin-bottom:10px;">Top risks this week</div>
                <ul style="margin:0 0 0 18px;padding:0;line-height:1.5;">{risk_html}</ul>
              </div>
            </div>

            {render_html_table(radar_table, "Structural Opportunity Radar — client view")}

            <div style="margin-top:10px;font-size:13px;color:#555555;line-height:1.5;">
              {radar_note}
            </div>

            <div style="margin-top:24px;padding:16px;border:1px solid #e3eaf5;border-radius:10px;background:#fcfdff;">
              <div style="font-size:18px;font-weight:700;color:#2F5597;margin-bottom:10px;">Bottom line</div>
              {bottom_html}
            </div>

            <div style="margin-top:24px;padding-top:16px;border-top:1px solid #e6ecf5;color:#555555;font-size:13px;line-height:1.5;">
              This email is the client-facing summary. The attached Word report contains the full analyst layer, including detailed scorecards, second-order effects analysis, opportunity comparisons, and the full disclaimer.
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    return html.strip()


# ---------- MAIN ----------
def main():
    output_dir = Path("output")
    reports = sorted(output_dir.glob("weekly_analysis_*.md"))
    if not reports:
        raise FileNotFoundError("No weekly_analysis_*.md file found in output/")

    latest_report = reports[-1]
    original_md_text = latest_report.read_text(encoding="utf-8")
    md_text_clean = strip_citations(original_md_text)

    send_date_str = datetime.now().strftime("%Y-%m-%d")

    clean_md_path = latest_report.with_name(f"weekly_report_review_{send_date_str}.md")
    clean_md_path.write_text(md_text_clean, encoding="utf-8")

    docx_path = latest_report.with_name(f"weekly_report_review_{send_date_str}.docx")
    build_docx_from_markdown(md_text_clean, docx_path)

    subject = f"Weekly Report Review {send_date_str}"
    html_body = build_email_body_html(md_text_clean, send_date_str)

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

    msg.attach(MIMEText(html_body, "html", "utf-8"))

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

    with open(clean_md_path, "rb") as f:
        md_attachment = MIMEApplication(f.read(), _subtype="markdown")
        md_attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=clean_md_path.name,
        )
        msg.attach(md_attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], msg.as_string())

    print(
        f"Sent email for {latest_report.name} with attachment {docx_path.name} "
        f"and clean markdown export {clean_md_path.name}"
    )


if __name__ == "__main__":
    main()

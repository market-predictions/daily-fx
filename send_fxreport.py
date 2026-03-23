#!/usr/bin/env python3
"""
send_fxreport.py

Validate the newest Weekly FX Review markdown, render delivery HTML/PDF,
and send it to the configured recipient.

Design goals:
- premium, email-first layout
- strict section validation
- USD-base portfolio labels
- optional equity-curve image
- minimal external dependencies
"""

from __future__ import annotations

import html
import os
import re
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable

REQUIRED_MAIL_TO = "mrkt.rprts@gmail.com"
TITLE = "Weekly FX Review"
DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."
SECTION16_SENTENCE = "**This section is the canonical default input for the next run unless the user explicitly overrides it.**"

REQUIRED_SECTION_HEADINGS = [
    "## 1. Executive summary",
    "## 2. Portfolio action snapshot",
    "## 3. Global macro & FX regime dashboard",
    "## 4. Structural currency opportunity radar",
    "## 5. Key risks / invalidators",
    "## 6. Bottom line",
    "## 7. Equity curve and portfolio development",
    "## 8. Currency allocation map",
    "## 9. Macro transmission & second-order effects map",
    "## 10. Current currency review",
    "## 11. Best new currency opportunities",
    "## 12. Portfolio rotation plan",
    "## 13. Final action table",
    "## 14. Position changes executed this run",
    "## 15. Current portfolio holdings and cash",
    "## 16. Carry-forward input for next run",
    "## 17. Disclaimer",
]

REQUIRED_SECTION15_LABELS = [
    "- Starting capital (USD):",
    "- Invested market value (USD):",
    "- Cash (USD):",
    "- Total portfolio value (USD):",
    "- Since inception return (%):",
    "- Base currency:",
]

CITATION_PATTERNS = [
    r"cite.*?",
    r"filecite.*?",
    r"forecast.*?",
    r"finance.*?",
    r"schedule.*?",
    r"standing.*?",
]

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)
REPORT_FILE_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)
DATE_PATTERNS = [
    "%B %d, %Y",
    "%d %B %Y",
    "%Y-%m-%d",
]

STYLE = """
:root{
  --paper:#f7f3eb;
  --ink:#18252c;
  --muted:#53636d;
  --band:#203740;
  --line:#d7c7a4;
  --card:#fffdfa;
  --soft:#efe7d8;
  --accent:#9f8357;
}
*{box-sizing:border-box}
body{
  margin:0;
  padding:0;
  background:var(--paper);
  color:var(--ink);
  font-family:Arial,Helvetica,sans-serif;
  line-height:1.45;
}
.shell{
  max-width:1080px;
  margin:0 auto;
  padding:28px 20px 40px;
}
.hero{
  background:var(--band);
  color:#fff;
  padding:28px 30px 24px;
  border-radius:16px;
  box-shadow:0 10px 28px rgba(20,34,40,.12);
}
.masthead{
  font-family:Georgia,"Times New Roman",serif;
  letter-spacing:.06em;
  font-size:32px;
  margin:0 0 10px;
  text-transform:uppercase;
}
.hero-row{
  display:flex;
  justify-content:space-between;
  gap:18px;
  align-items:flex-end;
  flex-wrap:wrap;
}
.hero .date{
  font-size:15px;
  opacity:.95;
}
.hero .label{
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.12em;
  opacity:.82;
}
.disclaimer{
  margin:18px 0 22px;
  color:var(--muted);
  font-style:italic;
  border-left:3px solid var(--line);
  padding-left:12px;
}
.grid{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;
}
.panel{
  background:var(--card);
  border:1px solid #eadfcb;
  border-radius:16px;
  padding:18px 18px 16px;
  box-shadow:0 6px 20px rgba(41,45,50,.05);
  margin-bottom:16px;
}
.panel.section-appendix{border-color:#d9d7cf;background:#fffefb}
.section-title{
  margin:0 0 12px;
  font-size:20px;
  line-height:1.2;
  display:flex;
  gap:10px;
  align-items:center;
}
.badge{
  width:32px;
  height:32px;
  border-radius:50%;
  background:#254f5d;
  color:#fff;
  display:inline-flex;
  justify-content:center;
  align-items:center;
  font-size:14px;
  font-weight:700;
  flex:0 0 32px;
}
.section-body p{margin:0 0 10px}
.section-body ul, .section-body ol{margin:0 0 12px 20px;padding:0}
.section-body li{margin:0 0 6px}
table{
  width:100%;
  border-collapse:collapse;
  margin:8px 0 12px;
  font-size:14px;
}
th,td{
  text-align:left;
  padding:9px 10px;
  border-bottom:1px solid #eadfcb;
  vertical-align:top;
}
th{
  font-size:12px;
  letter-spacing:.06em;
  text-transform:uppercase;
  color:var(--muted);
}
code{background:#f0ece2;padding:2px 5px;border-radius:5px}
hr{border:none;border-top:1px solid #eadfcb;margin:18px 0}
.kicker{
  margin:26px 0 10px;
  font-size:12px;
  letter-spacing:.16em;
  text-transform:uppercase;
  color:var(--accent);
}
.footer-note{
  color:var(--muted);
  font-size:12px;
  margin-top:16px;
}
img.eq{
  width:100%;
  max-width:760px;
  height:auto;
  border:1px solid #eadfcb;
  border-radius:10px;
  background:#fff;
}
@media (max-width: 760px){
  .grid{grid-template-columns:1fr}
  .hero{padding:24px 22px 20px}
  .masthead{font-size:28px}
}
"""

@dataclass
class Section:
    number: int
    title: str
    body: str

def esc(text: str) -> str:
    return html.escape(text, quote=True)

def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+\n", "\n", text)

def strip_citations(text: str) -> str:
    cleaned = text
    for pattern in CITATION_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"

def normalize_heading(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def latest_report_file(output_dir: Path) -> Path:
    files = []
    for path in output_dir.glob("weekly_fx_review_*.md"):
        m = REPORT_FILE_RE.fullmatch(path.name)
        if not m:
            continue
        date_part = m.group(1)
        version = int(m.group(2) or "0")
        files.append((date_part, version, path))
    if not files:
        raise FileNotFoundError("No files found matching output/weekly_fx_review_*.md")
    files.sort(key=lambda row: (row[0], row[1]))
    return files[-1][2]

def validate_required_report(text: str) -> None:
    if TITLE.lower() not in text.lower():
        raise RuntimeError(f"Report title must contain '{TITLE}'.")
    normalized = [normalize_heading(h) for h in REQUIRED_SECTION_HEADINGS]
    found = [normalize_heading("## " + m.group(1) + ". " + m.group(2)) for m in SECTION_RE.finditer(text)]
    missing = [h for h in normalized if h not in found]
    if missing:
        raise RuntimeError(f"Missing required section headings: {missing}")
    section15 = section_body(text, 15)
    for label in REQUIRED_SECTION15_LABELS:
        if label not in section15:
            raise RuntimeError(f"Section 15 is missing required label: {label}")
    section16 = section_body(text, 16)
    if SECTION16_SENTENCE not in section16:
        raise RuntimeError("Section 16 is missing the canonical carry-forward sentence.")

def section_body(text: str, number: int) -> str:
    pattern = re.compile(rf"^##\s+{number}\.\s+.+?$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return ""
    start = m.end()
    m_next = re.compile(r"^##\s+\d+\.\s+.+?$", re.MULTILINE).search(text, start)
    end = m_next.start() if m_next else len(text)
    return text[start:end].strip()

def parse_report_date(md_text: str, report_path: Path) -> str:
    lines = [line.strip() for line in md_text.splitlines() if line.strip()]
    for i, line in enumerate(lines[:8]):
        if line.lower() == TITLE.lower():
            for nxt in lines[i + 1:i + 5]:
                if nxt.startswith(">"):
                    continue
                parsed = try_parse_date(nxt)
                if parsed:
                    return parsed.strftime("%B %d, %Y")
    m = REPORT_FILE_RE.fullmatch(report_path.name)
    if m:
        dt = datetime.strptime(m.group(1), "%y%m%d")
        return dt.strftime("%B %d, %Y")
    return datetime.utcnow().strftime("%B %d, %Y")

def try_parse_date(value: str) -> datetime | None:
    value = value.strip().strip("*").strip()
    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

def parse_sections(text: str) -> list[Section]:
    matches = list(SECTION_RE.finditer(text))
    sections: list[Section] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append(Section(number=int(match.group(1)), title=match.group(2).strip(), body=body))
    return sections

def markdown_to_html(md: str) -> str:
    try:
        import markdown  # type: ignore
        return markdown.markdown(
            md,
            extensions=["tables", "sane_lists", "nl2br"],
            output_format="html5",
        )
    except Exception:
        return simple_markdown_to_html(md)

def simple_markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    parts: list[str] = []
    in_ul = False
    in_ol = False
    in_table = False
    table_buf: list[str] = []

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False

    def flush_table():
        nonlocal in_table, table_buf
        if not table_buf:
            return
        rows = [row.strip() for row in table_buf if row.strip()]
        if len(rows) >= 2 and set(rows[1].replace("|", "").replace(":", "").replace("-", "").strip()) == set():
            headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
            parts.append("<table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>")
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                parts.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>")
            parts.append("</tbody></table>")
        else:
            parts.append("<pre>" + esc("\n".join(table_buf)) + "</pre>")
        table_buf = []
        in_table = False

    for raw in lines:
        line = raw.rstrip()
        if "|" in line and line.count("|") >= 2:
            close_lists()
            in_table = True
            table_buf.append(line)
            continue
        elif in_table:
            flush_table()

        stripped = line.strip()
        if not stripped:
            close_lists()
            parts.append("")
            continue
        if stripped.startswith("### "):
            close_lists()
            parts.append(f"<h3>{esc(stripped[4:])}</h3>")
        elif stripped.startswith("#### "):
            close_lists()
            parts.append(f"<h4>{esc(stripped[5:])}</h4>")
        elif stripped.startswith("- "):
            if in_ol:
                parts.append("</ol>")
                in_ol = False
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{inline_format(stripped[2:])}</li>")
        elif re.match(r"^\d+\.\s+", stripped):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            if not in_ol:
                parts.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s+", "", stripped)
            parts.append(f"<li>{inline_format(item)}</li>")
        elif stripped.startswith("> "):
            close_lists()
            parts.append(f"<blockquote>{inline_format(stripped[2:])}</blockquote>")
        else:
            close_lists()
            parts.append(f"<p>{inline_format(stripped)}</p>")

    if in_table:
        flush_table()
    close_lists()
    return "\n".join(part for part in parts if part != "")

def inline_format(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text

def build_report_html(md_text: str, report_date_str: str, image_src: str | None = None) -> str:
    sections = parse_sections(md_text)
    client_sections = [s for s in sections if s.number <= 7]
    analyst_sections = [s for s in sections if s.number >= 8]

    def panel(section: Section, appendix: bool = False) -> str:
        extra = " section-appendix" if appendix else ""
        body = section.body
        if section.number == 16:
            body = body.replace(SECTION16_SENTENCE, "")
            body = body.strip()
        body_html = markdown_to_html(body) if body else ""
        if section.number == 7 and image_src:
            body_html += f'<p><img class="eq" src="{esc(image_src)}" alt="Equity curve"></p>'
        return (
            f'<section class="panel{extra}">'
            f'<h2 class="section-title"><span class="badge">{section.number}</span><span>{esc(section.title)}</span></h2>'
            f'<div class="section-body">{body_html}</div>'
            f'</section>'
        )

    intro_cards = "".join(panel(s) for s in client_sections[:2])
    client_grid = "".join(panel(s) for s in client_sections[2:4])
    client_panels = "".join(panel(s) for s in client_sections[4:])
    analyst_panels = "".join(panel(s, appendix=True) for s in analyst_sections)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(TITLE)}</title>
<style>{STYLE}</style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-row">
        <div>
          <div class="masthead">{esc(TITLE)}</div>
          <div class="date">{esc(report_date_str)}</div>
        </div>
        <div class="label">Investor Report</div>
      </div>
    </header>

    <div class="disclaimer">{esc(DISCLAIMER_LINE)}</div>

    {intro_cards}

    <div class="grid">
      {client_grid}
    </div>

    {client_panels}

    <div class="kicker">Analyst Appendix</div>
    {analyst_panels}

    <div class="footer-note">Generated by send_fxreport.py</div>
  </div>
</body>
</html>""".strip()

def plain_text_from_markdown(md_text: str) -> str:
    text = re.sub(r"^#.+$", "", md_text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"

def create_pdf_from_html(html_text: str, output_path: Path) -> None:
    try:
        from weasyprint import HTML  # type: ignore
        HTML(string=html_text, base_url=str(output_path.parent)).write_pdf(str(output_path))
    except Exception as exc:
        raise RuntimeError(
            "PDF generation failed. Install WeasyPrint in the workflow dependencies."
        ) from exc

def parse_section15_value(md_text: str, label: str) -> float | None:
    section15 = section_body(md_text, 15)
    pattern = re.compile(rf"^{re.escape(label)}\s*(.+?)\s*$", re.MULTILINE)
    m = pattern.search(section15)
    if not m:
        return None
    raw = m.group(1).replace(",", "").replace("$", "").strip()
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return float(raw)
    except ValueError:
        return None

def create_equity_curve_png(output_dir: Path, output_png: Path) -> bool:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return False

    history: list[tuple[str, float]] = []
    for path in sorted(output_dir.glob("weekly_fx_review_*.md")):
        try:
            text = normalize_whitespace(path.read_text(encoding="utf-8"))
            value = parse_section15_value(text, "- Total portfolio value (USD):")
            if value is None:
                continue
            m = REPORT_FILE_RE.fullmatch(path.name)
            label = m.group(1) if m else path.stem
            history.append((label, value))
        except Exception:
            continue

    if len(history) < 2:
        return False

    x = list(range(len(history)))
    y = [v for _, v in history]
    labels = [label for label, _ in history]

    plt.figure(figsize=(8.4, 3.4))
    plt.plot(x, y, linewidth=2)
    plt.xticks(x, labels, rotation=45, ha="right", fontsize=8)
    plt.ylabel("Portfolio value (USD)")
    plt.title("Model portfolio development")
    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=150)
    plt.close()
    return True

def generate_delivery_assets(output_dir: Path, report_path: Path) -> dict:
    original_md_text = normalize_whitespace(report_path.read_text(encoding="utf-8"))
    md_text_clean = strip_citations(original_md_text)
    validate_required_report(md_text_clean)
    report_date_str = parse_report_date(md_text_clean, report_path)
    safe_stem = report_path.stem

    clean_md_path = report_path.with_name(f"{safe_stem}_clean.md")
    clean_md_path.write_text(md_text_clean, encoding="utf-8")

    equity_curve_png = report_path.with_name(f"{safe_stem}_equity_curve.png")
    has_curve = create_equity_curve_png(output_dir, equity_curve_png)
    image_src_pdf = equity_curve_png.resolve().as_uri() if has_curve else None
    image_src_email = "cid:equitycurve" if has_curve else None

    html_email = build_report_html(md_text_clean, report_date_str, image_src=image_src_email)
    html_pdf = build_report_html(md_text_clean, report_date_str, image_src=image_src_pdf)

    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    create_pdf_from_html(html_pdf, pdf_path)
    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise RuntimeError(f"PDF attachment was not created correctly: {pdf_path}")

    return {
        "report_date_str": report_date_str,
        "clean_md_path": clean_md_path,
        "equity_curve_png": equity_curve_png,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "html_email": html_email,
        "safe_stem": safe_stem,
        "md_text_clean": md_text_clean,
        "has_curve": has_curve,
    }

def write_delivery_manifest(path: Path, report_name: str, recipient: str, attachments: Iterable[str]) -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    content = (
        f"Delivery status: OK\n"
        f"Timestamp: {timestamp}\n"
        f"Report: {report_name}\n"
        f"Recipient: {recipient}\n"
        f"HTML body: full report\n"
        f"PDF attached: yes\n"
        f"Attachments: {', '.join(attachments)}\n"
    )
    path.write_text(content, encoding="utf-8")

def send_email_with_attachments(assets: dict) -> tuple[list[str], Path, str]:
    subject = f"{TITLE} {assets['report_date_str']}"
    smtp_host = require_env("MRKT_RPRTS_SMTP_HOST")
    smtp_port = int(os.environ.get("MRKT_RPRTS_SMTP_PORT") or "587")
    smtp_user = require_env("MRKT_RPRTS_SMTP_USER")
    smtp_pass = require_env("MRKT_RPRTS_SMTP_PASS")
    mail_from = require_env("MRKT_RPRTS_MAIL_FROM")
    mail_to_env = os.environ.get("MRKT_RPRTS_MAIL_TO", REQUIRED_MAIL_TO).strip()
    if mail_to_env != REQUIRED_MAIL_TO:
        raise RuntimeError(f"Recipient mismatch: expected {REQUIRED_MAIL_TO}, got {mail_to_env}")
    mail_to = REQUIRED_MAIL_TO

    root = MIMEMultipart("mixed")
    root["Subject"] = subject
    root["From"] = mail_from
    root["To"] = mail_to

    related = MIMEMultipart("related")
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(plain_text_from_markdown(assets["md_text_clean"]), "plain", "utf-8"))
    alternative.attach(MIMEText(assets["html_email"], "html", "utf-8"))
    related.attach(alternative)

    attachments = [assets["pdf_path"].name, assets["clean_md_path"].name, assets["html_path"].name]

    if assets["has_curve"] and assets["equity_curve_png"].exists():
        png_bytes = assets["equity_curve_png"].read_bytes()
        inline_png = MIMEImage(png_bytes, _subtype="png")
        inline_png.add_header("Content-ID", "<equitycurve>")
        inline_png.add_header("Content-Disposition", "inline", filename=assets["equity_curve_png"].name)
        related.attach(inline_png)

        png_attachment = MIMEApplication(png_bytes, _subtype="png")
        png_attachment.add_header("Content-Disposition", "attachment", filename=assets["equity_curve_png"].name)
        root.attach(png_attachment)
        attachments.append(assets["equity_curve_png"].name)

    root.attach(related)

    for path in [assets["pdf_path"], assets["clean_md_path"], assets["html_path"]]:
        subtype = "pdf" if path.suffix == ".pdf" else ("markdown" if path.suffix == ".md" else "html")
        with open(path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype=subtype)
        attachment.add_header("Content-Disposition", "attachment", filename=path.name)
        root.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], root.as_string())

    manifest_path = assets["pdf_path"].with_name(f"{assets['safe_stem']}_delivery_manifest.txt")
    write_delivery_manifest(manifest_path, assets["pdf_path"].name.replace(".pdf", ".md"), mail_to, attachments)
    return attachments, manifest_path, mail_to

def main() -> None:
    output_dir = Path("output")
    latest_report = latest_report_file(output_dir)
    assets = generate_delivery_assets(output_dir, latest_report)
    attachments, manifest_path, mail_to = send_email_with_attachments(assets)
    receipt = (
        f"DELIVERY_OK | report={latest_report.name} | recipient={mail_to} | "
        f"html_body=full_report | pdf_attached=yes | manifest={manifest_path.name} | "
        f"attachments={', '.join(attachments)}"
    )
    print(receipt)

if __name__ == "__main__":
    main()

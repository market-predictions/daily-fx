#!/usr/bin/env python3
"""
send_fxreport.py

Validate the newest Weekly FX Review markdown, enforce freshness against the
latest live FX portfolio state, render HTML/PDF, and send it by email.

This version adds a hard freshness guard so a stale markdown report can never
be emailed after fx_portfolio_engine.py has already written newer valuation
files.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable

try:
    import markdown as markdown_lib  # type: ignore
except Exception:  # pragma: no cover
    markdown_lib = None  # type: ignore

try:
    from weasyprint import HTML  # type: ignore
except Exception:  # pragma: no cover
    HTML = None  # type: ignore


REQUIRED_MAIL_TO = "mrkt.rprts@gmail.com"
TITLE = "Weekly FX Review"
DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."
SECTION16_SENTENCE = "**This section is the canonical default input for the next run unless the user explicitly overrides it.**"
REPORT_FILE_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)
CITATION_PATTERNS = [
    r"cite.*?",
    r"filecite.*?",
    r"forecast.*?",
    r"finance.*?",
    r"schedule.*?",
    r"standing.*?",
]
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
TRADINGVIEW_CURRENCY_URLS = {
    "USD": "https://www.tradingview.com/chart/?symbol=DXY",
    "EUR": "https://www.tradingview.com/chart/?symbol=EURUSD",
    "GBP": "https://www.tradingview.com/chart/?symbol=GBPUSD",
    "AUD": "https://www.tradingview.com/chart/?symbol=AUDUSD",
    "NZD": "https://www.tradingview.com/chart/?symbol=NZDUSD",
    "JPY": "https://www.tradingview.com/chart/?symbol=1/USDJPY",
    "CHF": "https://www.tradingview.com/chart/?symbol=1/USDCHF",
    "CAD": "https://www.tradingview.com/chart/?symbol=1/USDCAD",
    "MXN": "https://www.tradingview.com/chart/?symbol=1/USDMXN",
    "ZAR": "https://www.tradingview.com/chart/?symbol=1/USDZAR",
}
CURRENCY_MENTION_RE = re.compile(
    r"(?<![A-Za-z0-9/])(" + "|".join(TRADINGVIEW_CURRENCY_URLS.keys()) + r")(?![A-Za-z0-9/])"
)
ANCHOR_OR_CODE_RE = re.compile(r"(<a\b[^>]*>.*?</a>|<code>.*?</code>)", re.IGNORECASE | re.DOTALL)

BRAND_CSS = """
body {
  margin: 0;
  padding: 24px;
  background: #f6f2ec;
  color: #2b3742;
  font-family: Arial, Helvetica, sans-serif;
}
a.tv-link {
  color: #2A5384;
  text-decoration: none;
  border-bottom: 1px dotted #D4B483;
}
a.tv-link:hover { text-decoration: underline; }
.report-shell {
  max-width: 1080px;
  margin: 0 auto;
}
.hero {
  background: #607887;
  color: #fbfaf7;
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 18px;
}
.hero h1 {
  margin: 0 0 6px 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 30px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.notice {
  background: #fcfaf7;
  border: 1px solid #d9d3cb;
  border-radius: 12px;
  color: #6b7882;
  padding: 10px 14px;
  margin: 0 0 18px 0;
  font-size: 12px;
}
.section {
  background: #fcfaf7;
  border: 1px solid #d9d3cb;
  border-radius: 16px;
  padding: 16px 18px;
  margin: 0 0 18px 0;
}
.section h2 {
  margin: 0 0 14px 0;
  color: #607887;
  font-size: 22px;
}
h3, h4 {
  color: #2b3742;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0 14px 0;
  border: 1px solid #d9d3cb;
  table-layout: fixed;
}
th {
  background: #f2ebdd;
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid #d9d3cb;
}
td {
  padding: 8px 10px;
  border-bottom: 1px solid #ece6de;
  vertical-align: top;
  word-wrap: break-word;
}
tr:nth-child(even) td {
  background: #fefcf9;
}
blockquote {
  margin: 12px 0;
  padding: 10px 12px;
  border-left: 4px solid #D4B483;
  background: #F8F3EB;
  color: #6b7882;
}
code {
  background: #f2ebdd;
  padding: 1px 4px;
  border-radius: 4px;
}
ul, ol { padding-left: 22px; }
li, p { line-height: 1.56; }
.footer-note {
  color: #6b7882;
  font-size: 12px;
  margin-top: 8px;
}
"""

PDF_CSS = """
@page { size: A4 landscape; margin: 12mm; }
body { background: #ffffff; padding: 0; }
.report-shell { max-width: none; }
"""

def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    return re.sub(r"[ \t]+\n", "\n", text)

def strip_citations(text: str) -> str:
    cleaned = normalize_whitespace(text)
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

def section_body(text: str, number: int) -> str:
    pattern = re.compile(rf"^##\s+{number}\.\s+.+?$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return ""
    start = m.end()
    m_next = re.compile(r"^##\s+\d+\.\s+.+?$", re.MULTILINE).search(text, start)
    end = m_next.start() if m_next else len(text)
    return text[start:end].strip()

def validate_required_report(text: str) -> None:
    if TITLE.lower() not in text.lower():
        raise RuntimeError(f"Report title must contain '{TITLE}'.")
    normalized = [normalize_heading(h) for h in REQUIRED_SECTION_HEADINGS]
    found = [normalize_heading("## " + m.group(1) + ". " + m.group(2)) for m in SECTION_RE.finditer(text)]
    missing = [h for h in normalized if h not in found]
    if missing:
        raise RuntimeError(f"Missing required section headings: {missing}")
    if SECTION16_SENTENCE not in section_body(text, 16):
        raise RuntimeError("Section 16 is missing the canonical carry-forward sentence.")

def esc(text: str) -> str:
    return html.escape(text, quote=True)

def clean_inline(text: str) -> str:
    text = strip_citations(text).strip()
    text = text.replace("**", "").replace("*", "").replace("`", "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()

def parse_numeric_from_line(value: str) -> float:
    cleaned = value.replace(",", "").replace("$", "").strip()
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if cleaned == "":
        raise ValueError("No numeric content found")
    return float(cleaned)

def extract_labeled_value(section_text: str, label: str) -> str | None:
    patterns = [
        rf"(?m)^\s*-\s*{re.escape(label)}\s*(.+?)\s*$",
        rf"(?m)^\s*{re.escape(label)}\s*(.+?)\s*$",
    ]
    for pattern in patterns:
        m = re.search(pattern, section_text)
        if m:
            return m.group(1).strip()
    return None

def compare_close(name: str, report_value: float, live_value: float, tolerance: float = 0.2) -> None:
    if not math.isfinite(report_value) or not math.isfinite(live_value):
        raise RuntimeError(f"Freshness check failed for {name}: non-finite comparison")
    if abs(report_value - live_value) > tolerance:
        raise RuntimeError(
            f"Freshness check failed for {name}: report={report_value:.2f}, live_state={live_value:.2f}, tolerance={tolerance:.2f}"
        )

def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def validate_report_freshness(md_text_clean: str, portfolio_state: dict) -> None:
    sec7 = section_body(md_text_clean, 7)
    sec15 = section_body(md_text_clean, 15)
    if not sec7 or not sec15:
        raise RuntimeError("Freshness check failed: report is missing Section 7 or Section 15")

    live_nav = float(portfolio_state["nav_usd"])
    live_cash = float(portfolio_state["cash_usd"])
    live_gross = float(portfolio_state["last_valuation"]["gross_exposure_usd"])
    live_unrealized = float(portfolio_state["last_valuation"]["unrealized_pnl_usd"])
    live_since_inception = float(portfolio_state["last_valuation"]["since_inception_return_pct"])
    live_overlay_ts = str(portfolio_state["last_valuation"]["overlay_as_of_utc"])

    sec7_nav_raw = extract_labeled_value(sec7, "Net asset value (USD):")
    sec7_cash_raw = extract_labeled_value(sec7, "Cash (USD):")
    sec7_unrealized_raw = extract_labeled_value(sec7, "Unrealized P&L (USD):")
    sec7_since_raw = extract_labeled_value(sec7, "Since inception return (%):")

    sec15_cash_raw = extract_labeled_value(sec15, "Cash (USD):")
    sec15_total_raw = extract_labeled_value(sec15, "Total portfolio value (USD):")
    sec15_invested_raw = extract_labeled_value(sec15, "Invested market value (USD):")
    sec15_since_raw = extract_labeled_value(sec15, "Since inception return (%):")

    required = {
        "Section 7 NAV": sec7_nav_raw,
        "Section 7 Cash": sec7_cash_raw,
        "Section 7 Unrealized": sec7_unrealized_raw,
        "Section 7 Since inception": sec7_since_raw,
        "Section 15 Cash": sec15_cash_raw,
        "Section 15 Total portfolio value": sec15_total_raw,
        "Section 15 Invested market value": sec15_invested_raw,
        "Section 15 Since inception": sec15_since_raw,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise RuntimeError(f"Freshness check failed: report is missing required labeled values: {missing}")

    compare_close("Section 7 NAV", parse_numeric_from_line(sec7_nav_raw or ""), live_nav)
    compare_close("Section 7 Cash", parse_numeric_from_line(sec7_cash_raw or ""), live_cash)
    compare_close("Section 7 Unrealized P&L", parse_numeric_from_line(sec7_unrealized_raw or ""), live_unrealized)
    compare_close("Section 7 Since inception return", parse_numeric_from_line(sec7_since_raw or ""), live_since_inception, tolerance=0.02)

    compare_close("Section 15 Cash", parse_numeric_from_line(sec15_cash_raw or ""), live_cash)
    compare_close("Section 15 Total portfolio value", parse_numeric_from_line(sec15_total_raw or ""), live_nav)
    compare_close("Section 15 Invested market value", parse_numeric_from_line(sec15_invested_raw or ""), live_gross)
    compare_close("Section 15 Since inception return", parse_numeric_from_line(sec15_since_raw or ""), live_since_inception, tolerance=0.02)

    overlay_ts_present = live_overlay_ts in md_text_clean
    if not overlay_ts_present:
        raise RuntimeError(
            "Freshness check failed: report does not contain the latest portfolio-state overlay timestamp "
            f"({live_overlay_ts}). Refusing to send a stale report."
        )

def try_parse_date(value: str) -> datetime | None:
    value = value.strip().strip("*").strip()
    for fmt in ("%B %d, %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

def parse_report_date(md_text: str, report_path: Path) -> str:
    lines = [line.strip() for line in md_text.splitlines() if line.strip()]
    for i, line in enumerate(lines[:8]):
        if line.lower() == f"# {TITLE}".lower():
            for nxt in lines[i + 1 : i + 5]:
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

def preprocess_markdown(text: str) -> str:
    lines = normalize_whitespace(text).splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == SECTION16_SENTENCE:
            continue
        out.append(line)
    return "\n".join(out)

def ensure_anchor_targets(html_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        anchor = match.group(0)
        if "target=" not in anchor:
            anchor = anchor[:-1] + ' target="_blank" rel="noopener noreferrer">'
        elif "rel=" not in anchor:
            anchor = anchor[:-1] + ' rel="noopener noreferrer">'
        return anchor
    return re.sub(r"<a\b[^>]*>", repl, html_text, flags=re.IGNORECASE)

def link_tradingview_mentions(html_text: str) -> str:
    placeholders: list[str] = []
    def protect(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"@@TVPLACEHOLDER{len(placeholders)-1}@@"
    protected = ANCHOR_OR_CODE_RE.sub(protect, html_text)

    def repl(match: re.Match[str]) -> str:
        code = match.group(1)
        url = TRADINGVIEW_CURRENCY_URLS[code]
        return f'<a class="tv-link" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{code}</a>'

    protected = CURRENCY_MENTION_RE.sub(repl, protected)
    for idx, original in enumerate(placeholders):
        protected = protected.replace(f"@@TVPLACEHOLDER{idx}@@", original)
    return protected

def inline_format(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text

def simple_markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    parts: list[str] = []
    in_ul = False
    in_ol = False
    in_table = False
    table_buf: list[str] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False

    def flush_table() -> None:
        nonlocal in_table, table_buf
        if not table_buf:
            return
        rows = [row.strip() for row in table_buf if row.strip()]
        if len(rows) >= 2 and set(rows[1].replace("|", "").replace(":", "").replace("-", "").strip()) == set():
            headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
            parts.append("<table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>")
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                parts.append("<tr>" + "".join(f"<td>{inline_format(c)}</td>" for c in cells) + "</tr>")
            parts.append("</tbody></table>")
        else:
            parts.append("<pre>" + esc("\n".join(table_buf)) + "</pre>")
        table_buf = []
        in_table = False

    for raw in lines:
        line = raw.rstrip()
        if "|" in line and line.count("|") >= 2 and line.strip().startswith("|"):
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
            parts.append(f"<li>{inline_format(re.sub(r'^\d+\.\s+', '', stripped))}</li>")
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

def markdown_to_html(md: str) -> str:
    md = preprocess_markdown(md)
    if markdown_lib is not None:
        try:
            html_text = markdown_lib.markdown(md, extensions=["tables", "sane_lists", "nl2br"])
            return ensure_anchor_targets(link_tradingview_mentions(html_text))
        except Exception:
            pass
    return ensure_anchor_targets(link_tradingview_mentions(simple_markdown_to_html(md)))

def parse_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(SECTION_RE.finditer(text))
    sections = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((int(match.group(1)), match.group(2).strip(), body))
    return sections

def build_report_html(md_text: str, report_date_str: str) -> str:
    sections = parse_sections(md_text)
    section_html = []
    for number, title, body in sections:
        section_html.append(
            f"<section class='section'><h2>{number}. {esc(title)}</h2>{markdown_to_html(body)}</section>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(TITLE)}</title>
<style>{BRAND_CSS}</style>
</head>
<body>
<div class="report-shell">
  <div class="hero">
    <h1>{esc(TITLE)}</h1>
    <div>{esc(report_date_str)}</div>
  </div>
  <div class="notice">{esc(DISCLAIMER_LINE)}</div>
  {''.join(section_html)}
  <div class="footer-note">Freshness-guarded delivery by send_fxreport.py</div>
</div>
</body>
</html>""".strip()

def create_pdf_from_html(html_text: str, output_path: Path) -> None:
    if HTML is None:
        raise RuntimeError("PDF generation failed. Install WeasyPrint in the workflow dependencies.")
    HTML(string=html_text).write_pdf(str(output_path), stylesheets=None)

def plain_text_from_markdown(md_text: str) -> str:
    text = re.sub(r"^#.+$", "", md_text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"

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

def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def generate_delivery_assets(output_dir: Path, report_path: Path) -> dict:
    original_md_text = normalize_whitespace(report_path.read_text(encoding="utf-8"))
    md_text_clean = strip_citations(original_md_text)
    validate_required_report(md_text_clean)

    portfolio_state = load_json(output_dir / "fx_portfolio_state.json")
    validate_report_freshness(md_text_clean, portfolio_state)

    report_date_str = parse_report_date(md_text_clean, report_path)
    safe_stem = report_path.stem

    clean_md_path = report_path.with_name(f"{safe_stem}_clean.md")
    clean_md_path.write_text(md_text_clean, encoding="utf-8")

    html_email = build_report_html(md_text_clean, report_date_str)
    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    create_pdf_from_html(html_email, pdf_path)
    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise RuntimeError(f"PDF attachment was not created correctly: {pdf_path}")

    return {
        "report_date_str": report_date_str,
        "clean_md_path": clean_md_path,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "html_email": html_email,
        "safe_stem": safe_stem,
        "md_text_clean": md_text_clean,
    }

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

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(plain_text_from_markdown(assets["md_text_clean"]), "plain", "utf-8"))
    alternative.attach(MIMEText(assets["html_email"], "html", "utf-8"))
    root.attach(alternative)

    attachments = [assets["pdf_path"].name, assets["clean_md_path"].name, assets["html_path"].name]

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true", help="Validate report freshness and required structure only.")
    args = parser.parse_args()

    output_dir = Path("output")
    latest_report = latest_report_file(output_dir)
    assets = generate_delivery_assets(output_dir, latest_report)

    if args.validate_only:
        print(
            "REPORT_FRESHNESS_OK | "
            f"report={latest_report.name} | "
            f"cash={extract_labeled_value(section_body(assets['md_text_clean'], 15), 'Cash (USD):')} | "
            f"nav={extract_labeled_value(section_body(assets['md_text_clean'], 15), 'Total portfolio value (USD):')}"
        )
        return

    attachments, manifest_path, mail_to = send_email_with_attachments(assets)
    receipt = (
        f"DELIVERY_OK | report={latest_report.name} | recipient={mail_to} | "
        f"html_body=full_report | pdf_attached=yes | manifest={manifest_path.name} | "
        f"attachments={', '.join(attachments)}"
    )
    print(receipt)

if __name__ == "__main__":
    main()

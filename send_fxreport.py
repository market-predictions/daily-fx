#!/usr/bin/env python3
"""
send_fxreport.py

Restores the old executive FX Review look & feel while keeping:
- freshness guard against stale markdown
- live portfolio-state validation
- HTML + PDF delivery
- email dispatch with attachments

Restores:
- executive cover / dashboard feel
- separate Investor Report and Analyst Report blocks
- equity chart generation from output/fx_valuation_history.csv
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import os
import re
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable

try:
    import markdown as markdown_lib  # type: ignore
except Exception:
    markdown_lib = None  # type: ignore

try:
    from weasyprint import HTML  # type: ignore
except Exception:
    HTML = None  # type: ignore

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None  # type: ignore


REQUIRED_MAIL_TO = "mrkt.rprts@gmail.com"
TITLE = "Weekly FX Review"
DISCLAIMER_LINE = (
    "This report is for informational and educational purposes only; "
    "please see the disclaimer at the end."
)
SECTION16_SENTENCE = (
    "**This section is the canonical default input for the next run unless "
    "the user explicitly overrides it.**"
)

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

ANCHOR_OR_CODE_RE = re.compile(
    r"(<a\b[^>]*>.*?</a>|<code>.*?</code>)",
    re.IGNORECASE | re.DOTALL,
)

BRAND_CSS = """
@page {
  size: A4 landscape;
  margin: 11mm;
}

body {
  margin: 0;
  padding: 0;
  background: #f4efe8;
  color: #2b3742;
  font-family: Arial, Helvetica, sans-serif;
}

a.tv-link {
  color: #2f5b92;
  text-decoration: none;
  border-bottom: 1px dotted #c8a265;
}

a.tv-link:hover {
  text-decoration: underline;
}

.report-shell {
  max-width: 1400px;
  margin: 0 auto;
  padding: 18px;
}

.cover-card,
.section-card,
.chart-card,
.analyst-section {
  background: #fbfaf7;
  border: 1px solid #d8d0c4;
  border-radius: 20px;
  padding: 22px 28px;
  margin: 0 0 18px 0;
  box-sizing: border-box;
}

.cover-strip,
.analyst-strip {
  background: #6f8593;
  color: #ffffff;
  border-radius: 18px;
  padding: 28px 34px;
}

.cover-title {
  font-family: Georgia, "Times New Roman", serif;
  text-transform: uppercase;
  font-size: 42px;
  letter-spacing: 1.4px;
  color: #ffffff;
  margin: 0;
}

.cover-subrow {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 18px;
  margin-top: 10px;
}

.cover-date {
  font-size: 17px;
  color: #f4f0ea;
}

.cover-report-type {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
}

.gold-rule {
  height: 7px;
  border-radius: 5px;
  background: #c8a265;
  margin: 8px 0 18px 0;
}

.notice {
  background: #fcfaf7;
  border: 1px solid #d8d0c4;
  border-radius: 14px;
  color: #6b7882;
  padding: 10px 14px;
  margin: 0 0 18px 0;
  font-size: 12px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: 1fr 2fr 1.5fr;
  gap: 16px;
  margin-top: 16px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #d8d0c4;
  border-radius: 16px;
  padding: 16px 18px;
  min-height: 138px;
}

.kpi-label {
  font-size: 12px;
  letter-spacing: 1px;
  color: #6f8593;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.kpi-value {
  font-size: 20px;
  font-weight: 700;
  color: #2b3742;
  line-height: 1.25;
}

.kpi-body {
  font-size: 14px;
  line-height: 1.45;
  color: #2b3742;
}

.section-heading {
  font-size: 13px;
  letter-spacing: 1px;
  color: #6f8593;
  font-weight: 700;
  text-transform: uppercase;
  margin: 0 0 8px 0;
}

.section-card h2,
.chart-card h2 {
  margin: 0 0 14px 0;
  color: #667d8c;
  font-size: 24px;
}

.section-card h3,
.section-card h4,
.analyst-section h3,
.analyst-section h4 {
  color: #2b3742;
}

.table-wrap {
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid #d8d0c4;
  margin: 10px 0 14px 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 0;
}

th {
  background: #eee6d7;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid #d8d0c4;
  color: #2b3742;
  font-size: 14px;
}

td {
  padding: 10px 12px;
  border-bottom: 1px solid #e8dfd2;
  vertical-align: top;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.35;
}

tr:nth-child(even) td {
  background: #fffdf9;
}

blockquote {
  margin: 12px 0;
  padding: 10px 12px;
  border-left: 4px solid #c8a265;
  background: #f8f3eb;
  color: #6b7882;
}

code {
  background: #f2ebdd;
  padding: 1px 4px;
  border-radius: 4px;
}

ul, ol {
  padding-left: 22px;
}

li, p {
  line-height: 1.56;
  margin: 0 0 10px 0;
}

.chart-card img {
  width: 100%;
  height: auto;
  border: 1px solid #d8d0c4;
  border-radius: 14px;
  background: #ffffff;
}

.analyst-banner {
  margin-top: 26px;
  page-break-before: always;
}

.analyst-grid {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 16px;
  align-items: start;
}

.badge {
  width: 60px;
  height: 60px;
  border-radius: 999px;
  background: #2f5b92;
  color: #ffffff;
  font-size: 32px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.analyst-title {
  font-size: 18px;
  letter-spacing: 1px;
  color: #6f8593;
  font-weight: 700;
  text-transform: uppercase;
  margin: 10px 0 18px 0;
}

.footer-note {
  color: #6b7882;
  font-size: 12px;
  margin-top: 6px;
}

.page-break {
  page-break-before: always;
}
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


def normalize_heading(value: str) -> str:
    value = value.strip().lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def latest_report_file(output_dir: Path) -> Path:
    files: list[tuple[str, int, Path]] = []
    for path in output_dir.glob("weekly_fx_review_*.md"):
        match = REPORT_FILE_RE.fullmatch(path.name)
        if not match:
            continue
        date_part = match.group(1)
        version = int(match.group(2) or "0")
        files.append((date_part, version, path))
    if not files:
        raise FileNotFoundError("No files found matching output/weekly_fx_review_*.md")
    files.sort(key=lambda row: (row[0], row[1]))
    return files[-1][2]


def section_body(text: str, number: int) -> str:
    pattern = re.compile(rf"^##\s+{number}\.\s+.+?$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = re.compile(r"^##\s+\d+\.\s+.+?$", re.MULTILINE).search(text, start)
    end = next_match.start() if next_match else len(text)
    return text[start:end].strip()


def validate_required_report(text: str) -> None:
    if TITLE.lower() not in text.lower():
        raise RuntimeError(f"Report title must contain '{TITLE}'.")
    normalized_required = [normalize_heading(h) for h in REQUIRED_SECTION_HEADINGS]
    found = [
        normalize_heading("## " + match.group(1) + ". " + match.group(2))
        for match in SECTION_RE.finditer(text)
    ]
    missing = [item for item in normalized_required if item not in found]
    if missing:
        raise RuntimeError(f"Missing required section headings: {missing}")
    if SECTION16_SENTENCE not in section_body(text, 16):
        raise RuntimeError("Section 16 is missing the canonical carry-forward sentence.")


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def parse_numeric_from_line(value: str) -> float:
    cleaned = value.replace(",", "").replace("$", "").strip()
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned:
        raise ValueError("No numeric content found")
    return float(cleaned)


def extract_labeled_value(section_text: str, label: str) -> str | None:
    patterns = [
        rf"(?m)^\s*-\s*{re.escape(label)}\s*(.+?)\s*$",
        rf"(?m)^\s*{re.escape(label)}\s*(.+?)\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, section_text)
        if match:
            return match.group(1).strip()
    return None


def compare_close(name: str, report_value: float, live_value: float, tolerance: float = 0.2) -> None:
    if not math.isfinite(report_value) or not math.isfinite(live_value):
        raise RuntimeError(f"Freshness check failed for {name}: non-finite comparison")
    if abs(report_value - live_value) > tolerance:
        raise RuntimeError(
            f"Freshness check failed for {name}: "
            f"report={report_value:.2f}, live_state={live_value:.2f}, tolerance={tolerance:.2f}"
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

    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise RuntimeError(
            f"Freshness check failed: report is missing required labeled values: {missing}"
        )

    compare_close("Section 7 NAV", parse_numeric_from_line(sec7_nav_raw or ""), live_nav)
    compare_close("Section 7 Cash", parse_numeric_from_line(sec7_cash_raw or ""), live_cash)
    compare_close(
        "Section 7 Unrealized P&L",
        parse_numeric_from_line(sec7_unrealized_raw or ""),
        live_unrealized,
    )
    compare_close(
        "Section 7 Since inception return",
        parse_numeric_from_line(sec7_since_raw or ""),
        live_since_inception,
        tolerance=0.02,
    )

    compare_close("Section 15 Cash", parse_numeric_from_line(sec15_cash_raw or ""), live_cash)
    compare_close(
        "Section 15 Total portfolio value",
        parse_numeric_from_line(sec15_total_raw or ""),
        live_nav,
    )
    compare_close(
        "Section 15 Invested market value",
        parse_numeric_from_line(sec15_invested_raw or ""),
        live_gross,
    )
    compare_close(
        "Section 15 Since inception return",
        parse_numeric_from_line(sec15_since_raw or ""),
        live_since_inception,
        tolerance=0.02,
    )

    if live_overlay_ts not in md_text_clean:
        raise RuntimeError(
            "Freshness check failed: report does not contain the latest portfolio-state overlay "
            f"timestamp ({live_overlay_ts}). Refusing to send a stale report."
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
    for idx, line in enumerate(lines[:8]):
        if line.lower() == f"# {TITLE}".lower():
            for nxt in lines[idx + 1 : idx + 5]:
                if nxt.startswith(">"):
                    continue
                parsed = try_parse_date(nxt)
                if parsed:
                    return parsed.strftime("%B %d, %Y")
    match = REPORT_FILE_RE.fullmatch(report_path.name)
    if match:
        parsed = datetime.strptime(match.group(1), "%y%m%d")
        return parsed.strftime("%B %d, %Y")
    return datetime.utcnow().strftime("%B %d, %Y")


def preprocess_markdown(text: str) -> str:
    output: list[str] = []
    for line in normalize_whitespace(text).splitlines():
        if line.strip() == SECTION16_SENTENCE:
            continue
        output.append(line)
    return "\n".join(output)


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
        return (
            f'<a class="tv-link" href="{esc(url)}" '
            f'target="_blank" rel="noopener noreferrer">{code}</a>'
        )

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
        divider_ok = (
            len(rows) >= 2
            and set(rows[1].replace("|", "").replace(":", "").replace("-", "").strip()) == set()
        )
        if divider_ok:
            headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
            parts.append(
                "<div class='table-wrap'><table><thead><tr>"
                + "".join(f"<th>{esc(h)}</th>" for h in headers)
                + "</tr></thead><tbody>"
            )
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                parts.append(
                    "<tr>" + "".join(f"<td>{inline_format(c)}</td>" for c in cells) + "</tr>"
                )
            parts.append("</tbody></table></div>")
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
            ordered_item = re.sub(r"^\d+\.\s+", "", stripped)
            parts.append(f"<li>{inline_format(ordered_item)}</li>")
        elif stripped.startswith("> "):
            close_lists()
            parts.append(f"<blockquote>{inline_format(stripped[2:])}</blockquote>")
        else:
            close_lists()
            parts.append(f"<p>{inline_format(stripped)}</p>")

    if in_table:
        flush_table()

    close_lists()
    return "\n".join(parts)


def markdown_to_html(md: str) -> str:
    md = preprocess_markdown(md)
    if markdown_lib is not None:
        try:
            html_text = markdown_lib.markdown(md, extensions=["tables", "sane_lists", "nl2br"])
            html_text = re.sub(r"<table>", "<div class='table-wrap'><table>", html_text)
            html_text = html_text.replace("</table>", "</table></div>")
            return ensure_anchor_targets(link_tradingview_mentions(html_text))
        except Exception:
            pass
    return ensure_anchor_targets(link_tradingview_mentions(simple_markdown_to_html(md)))


def parse_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(SECTION_RE.finditer(text))
    sections: list[tuple[int, str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((int(match.group(1)), match.group(2).strip(), body))
    return sections


def extract_dashboard_items(section3_body: str) -> dict[str, str]:
    items: dict[str, str] = {}
    for line in section3_body.splitlines():
        line = line.strip()
        match = re.match(r"- \*\*(.+?)\*\*:\s*(.+)$", line)
        if match:
            items[match.group(1).strip()] = match.group(2).strip()
    return items


def make_summary_grid(section3_body: str) -> str:
    items = extract_dashboard_items(section3_body)
    risk = items.get("Risk regime", "Mild risk-off")
    divergence = items.get("Policy divergence", "USD remains rate-rich versus EUR and NZD.")
    overlay = items.get("Technical overlay", "Same-day available.")

    return f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Risk regime</div>
        <div class="kpi-value">{esc(risk)}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Policy divergence</div>
        <div class="kpi-body">{inline_format(divergence)}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Technical overlay</div>
        <div class="kpi-body">{inline_format(overlay)}</div>
      </div>
    </div>
    """.strip()


def chart_image_data(output_dir: Path) -> str:
    if plt is None:
        raise RuntimeError(
            "Equity chart generation requires matplotlib. Install matplotlib in the workflow."
        )

    csv_path = output_dir / "fx_valuation_history.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing required valuation history file: {csv_path}")

    rows: list[tuple[str, float]] = []
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = [item.strip() for item in line.split(",")]
        if len(parts) < 2:
            continue
        try:
            rows.append((parts[0], float(parts[1])))
        except Exception:
            continue

    if not rows:
        raise RuntimeError("No usable rows found in fx_valuation_history.csv for equity chart.")

    labels = [f"{date}\\n{i + 1}" for i, (date, _) in enumerate(rows)]
    navs = [value for _, value in rows]

    fig = plt.figure(figsize=(12, 4.2))
    ax = fig.add_subplot(111)
    ax.plot(range(len(navs)), navs, linewidth=2)
    ax.set_title("Model portfolio development")
    ax.set_ylabel("Portfolio value (USD)")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_investor_section(number: int, title: str, body: str) -> str:
    return (
        f'<section class="section-card">'
        f'<div class="section-heading">{number}</div>'
        f"<h2>{esc(title)}</h2>"
        f"{markdown_to_html(body)}"
        f"</section>"
    )


def build_analyst_section(ordinal: int, title: str, body: str) -> str:
    return (
        f'<section class="analyst-section">'
        f'<div class="analyst-grid">'
        f'<div class="badge">{ordinal}</div>'
        f"<div>"
        f'<div class="analyst-title">{esc(title)}</div>'
        f"{markdown_to_html(body)}"
        f"</div>"
        f"</div>"
        f"</section>"
    )


def build_report_html(md_text: str, report_date_str: str, output_dir: Path) -> str:
    sections = parse_sections(md_text)
    section_map = {number: (title, body) for number, title, body in sections}

    investor_sections_html = [
        build_investor_section(number, *section_map[number]) for number in range(1, 8)
    ]

    chart_b64 = chart_image_data(output_dir)
    chart_html = (
        f'<section class="chart-card">'
        f'<div class="section-heading">Analyst report</div>'
        f"<h2>Model portfolio development</h2>"
        f'<img src="data:image/png;base64,{chart_b64}" alt="Model portfolio development chart">'
        f"</section>"
    )

    analyst_sections_html = [
        build_analyst_section(idx, *section_map[number])
        for idx, number in enumerate(range(8, 18), start=1)
    ]

    summary_grid = make_summary_grid(section_map[3][1])

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

  <div class="cover-card">
    <div class="cover-strip">
      <div class="cover-title">{esc(TITLE)}</div>
      <div class="cover-subrow">
        <div class="cover-date">{esc(report_date_str)}</div>
        <div class="cover-report-type">Investor Report</div>
      </div>
    </div>
    <div class="gold-rule"></div>
    <div class="notice">{esc(DISCLAIMER_LINE)}</div>
    {summary_grid}
  </div>

  {''.join(investor_sections_html)}

  <div class="analyst-banner">
    <div class="analyst-strip">
      <div class="cover-title">{esc(TITLE)}</div>
      <div class="cover-subrow">
        <div class="cover-date">{esc(report_date_str)}</div>
        <div class="cover-report-type">Analyst Report</div>
      </div>
    </div>
    <div class="gold-rule"></div>
  </div>

  {chart_html}

  {''.join(analyst_sections_html)}

  <div class="footer-note">Freshness-guarded delivery by send_fxreport.py</div>
</div>
</body>
</html>"""


def create_pdf_from_html(html_text: str, output_path: Path) -> None:
    if HTML is None:
        raise RuntimeError("PDF generation failed. Install WeasyPrint in the workflow.")
    HTML(string=html_text).write_pdf(str(output_path))


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

    html_email = build_report_html(md_text_clean, report_date_str, output_dir)
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

    attachments = [
        assets["pdf_path"].name,
        assets["clean_md_path"].name,
        assets["html_path"].name,
    ]

    for path in [assets["pdf_path"], assets["clean_md_path"], assets["html_path"]]:
        subtype = "pdf" if path.suffix == ".pdf" else ("markdown" if path.suffix == ".md" else "html")
        with open(path, "rb") as handle:
            attachment = MIMEApplication(handle.read(), _subtype=subtype)
        attachment.add_header("Content-Disposition", "attachment", filename=path.name)
        root.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], root.as_string())

    manifest_path = assets["pdf_path"].with_name(f"{assets['safe_stem']}_delivery_manifest.txt")
    write_delivery_manifest(
        manifest_path,
        assets["pdf_path"].name.replace(".pdf", ".md"),
        mail_to,
        attachments,
    )

    return attachments, manifest_path, mail_to


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate report freshness and required structure only.",
    )
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

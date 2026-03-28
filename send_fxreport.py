#!/usr/bin/env python3
"""
send_fxreport.py

Presentation-layer refresh for the Weekly FX Review.

This version keeps the existing workflow logic intact:
- latest report discovery
- stale-report / freshness guard
- live portfolio-state validation
- HTML + PDF delivery
- email dispatch and manifest

It upgrades only the delivery layer:
- ETF-family visual system
- tighter executive cards
- section kickers
- portrait-friendly PDF layout
- table-first analyst appendix
- embedded equity chart inside Section 7
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
ANCHOR_OR_CODE_RE = re.compile(r"(<a\b[^>]*>.*?</a>|<code>.*?</code>)", re.IGNORECASE | re.DOTALL)

BRAND = {
    "paper": "#F6F2EC",
    "surface": "#FCFAF7",
    "header": "#607887",
    "header_text": "#FBFAF7",
    "ink": "#2B3742",
    "muted": "#6B7882",
    "border": "#D9D3CB",
    "champagne": "#D4B483",
    "champagne_soft": "#EFE4D2",
    "blue": "#2A5384",
}


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
        files.append((match.group(1), int(match.group(2) or "0"), path))
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
    compare_close("Section 7 Unrealized P&L", parse_numeric_from_line(sec7_unrealized_raw or ""), live_unrealized)
    compare_close("Section 7 Since inception return", parse_numeric_from_line(sec7_since_raw or ""), live_since_inception, tolerance=0.02)
    compare_close("Section 15 Cash", parse_numeric_from_line(sec15_cash_raw or ""), live_cash)
    compare_close("Section 15 Total portfolio value", parse_numeric_from_line(sec15_total_raw or ""), live_nav)
    compare_close("Section 15 Invested market value", parse_numeric_from_line(sec15_invested_raw or ""), live_gross)
    compare_close("Section 15 Since inception return", parse_numeric_from_line(sec15_since_raw or ""), live_since_inception, tolerance=0.02)

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
    out: list[str] = []
    for line in normalize_whitespace(text).splitlines():
        if line.strip() == SECTION16_SENTENCE:
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
        return (
            f'<a class="tv-link" href="{esc(TRADINGVIEW_CURRENCY_URLS[code])}" '
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


def is_markdown_table_line(line: str) -> bool:
    line = line.strip()
    return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]


def is_markdown_separator_line(line: str) -> bool:
    if not is_markdown_table_line(line):
        return False
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def simple_markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    parts: list[str] = []
    in_ul = False
    in_ol = False
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
        nonlocal table_buf
        if not table_buf:
            return
        rows = [row.strip() for row in table_buf if row.strip()]
        if len(rows) >= 2 and is_markdown_separator_line(rows[1]):
            headers = [cell.strip() for cell in rows[0].strip("|").split("|")]
            parts.append("<div class='table-wrap'><table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>")
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                parts.append("<tr>" + "".join(f"<td>{inline_format(c)}</td>" for c in cells) + "</tr>")
            parts.append("</tbody></table></div>")
        else:
            parts.append("<pre>" + esc("\n".join(table_buf)) + "</pre>")
        table_buf = []

    for raw in lines:
        line = raw.rstrip()
        if is_markdown_table_line(line):
            close_lists()
            table_buf.append(line)
            continue
        if table_buf:
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
            cleaned_stripped = re.sub(r"^\d+\.\s+", "", stripped)
            parts.append(f"<li>{inline_format(cleaned_stripped)}</li>")
        elif stripped.startswith("> "):
            close_lists()
            parts.append(f"<blockquote>{inline_format(stripped[2:])}</blockquote>")
        else:
            close_lists()
            parts.append(f"<p>{inline_format(stripped)}</p>")

    if table_buf:
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


def parse_sections(text: str) -> list[dict[str, object]]:
    matches = list(SECTION_RE.finditer(text))
    sections: list[dict[str, object]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append({
            "number": int(match.group(1)),
            "title": match.group(2).strip(),
            "body": text[start:end].strip(),
        })
    return sections


def extract_label_pairs(body: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        match = re.match(r"^-+\s*\*\*(.+?)\*\*:\s*(.+)$", stripped)
        if match:
            pairs.append((match.group(1).strip(), match.group(2).strip()))
            continue
        match = re.match(r"^-+\s*([^:*]+):\s*(.+)$", stripped)
        if match:
            pairs.append((match.group(1).strip(), match.group(2).strip()))
    return pairs


def render_kicker(number: int, title: str) -> str:
    return (
        "<table class='section-kicker' role='presentation' cellpadding='0' cellspacing='0'><tr>"
        f"<td class='section-badge-cell'><span class='section-badge'>{number}</span></td>"
        f"<td class='section-label-cell'><span class='section-label'>{esc(title)}</span></td>"
        "</tr></table>"
    )


def render_executive_summary(section: dict[str, object]) -> str:
    body = str(section["body"])
    pairs = extract_label_pairs(body)
    if not pairs:
        return f"<div class='panel panel-exec'>{render_kicker(int(section['display_number']), str(section['title']))}{markdown_to_html(body)}</div>"

    masthead_keys = {"Primary regime", "Secondary cross-current", "Geopolitical regime", "Main takeaway"}
    rows = []
    for key, value in pairs:
        if key in masthead_keys:
            continue
        rows.append(
            f"<div class='summary-line'><div class='summary-key'>{esc(key)}</div><div class='summary-value'>{inline_format(value)}</div></div>"
        )
    takeaway = next((v for k, v in pairs if k == "Main takeaway"), "")
    takeaway_html = ""
    if takeaway:
        takeaway_html = (
            "<div class='takeaway'>"
            "<div class='takeaway-label'>Main takeaway</div>"
            f"<div class='takeaway-text'>{inline_format(takeaway)}</div>"
            "</div>"
        )
    return (
        f"<div class='panel panel-exec'>{render_kicker(int(section['display_number']), str(section['title']))}"
        + "".join(rows)
        + takeaway_html
        + "</div>"
    )


def render_action_snapshot(section: dict[str, object]) -> str:
    rows = []
    extra_blocks = []
    for line in str(section["body"]).splitlines():
        stripped = line.strip()
        if stripped.startswith("- **") and ":**" not in stripped:
            m = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)$", stripped)
            if m:
                rows.append((m.group(1), m.group(2)))
        elif re.match(r"^\d+\.\s+", stripped):
            extra_blocks.append(stripped)
    table_rows = "".join(
        f"<tr><th>{esc(k)}</th><td>{inline_format(v)}</td></tr>" for k, v in rows
    )
    extras = ""
    if extra_blocks:
        extra_items_html = []
        for item in extra_blocks:
            cleaned_item = re.sub(r"^\d+\.\s+", "", item)
            extra_items_html.append(f"<li>{inline_format(cleaned_item)}</li>")
        extras = (
            "<div class='subblock'><div class='subblock-title'>Additional actions</div><ol>"
            + "".join(extra_items_html)
            + "</ol></div>"
        )
    return (
        f"<div class='panel panel-snapshot'>{render_kicker(int(section['display_number']), str(section['title']))}"
        "<table class='snapshot-table'><thead><tr><th>Recommendation</th><th>Decision</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table>{extras}</div>"
    )


def render_standard_panel(section: dict[str, object], *, chart_b64: str | None = None, extra_class: str = "") -> str:
    body_html = markdown_to_html(str(section["body"]))
    chart_html = ""
    if chart_b64:
        chart_html = (
            "<div class='chart-wrap'>"
            "<div class='chart-label'>Model portfolio development</div>"
            f"<img src='data:image/png;base64,{chart_b64}' alt='Model portfolio development chart'>"
            "</div>"
        )
    return (
        f"<div class='panel {extra_class}'>{render_kicker(int(section['display_number']), str(section['title']))}"
        f"{body_html}{chart_html}</div>"
    )


def split_currency_blocks(body: str) -> list[tuple[str, str]]:
    lines = body.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current_title = None
    current_lines: list[str] = []
    for raw in lines:
        if raw.strip().startswith("**") and "—" in raw:
            if current_title is not None:
                blocks.append((current_title, current_lines))
            current_title = raw.strip().strip("*")
            current_lines = []
        else:
            if current_title is None:
                current_title = "Review"
            current_lines.append(raw)
    if current_title is not None:
        blocks.append((current_title, current_lines))
    return [(title, "\n".join(content).strip()) for title, content in blocks]


def render_currency_review(section: dict[str, object]) -> str:
    blocks = split_currency_blocks(str(section["body"]))
    if not blocks:
        return render_standard_panel(section)
    cards = []
    for title, body in blocks:
        cards.append(
            "<article class='currency-card'>"
            f"<div class='currency-card-title'>{inline_format(title)}</div>"
            f"<div class='currency-card-body'>{markdown_to_html(body)}</div>"
            "</article>"
        )
    return (
        f"<div class='panel panel-currency-review'>{render_kicker(int(section['display_number']), str(section['title']))}"
        + "".join(cards)
        + "</div>"
    )


def render_rotation_plan(section: dict[str, object]) -> str:
    rows = []
    current_label = None
    current_items: list[str] = []
    for raw in str(section["body"]).splitlines():
        stripped = raw.strip()
        if stripped.startswith("- **"):
            m = re.match(r"^- \*\*(.+?)\*\*:\s*(.+)$", stripped)
            if m:
                rows.append((m.group(1), m.group(2)))
        elif stripped.startswith("### "):
            if current_label and current_items:
                rows.append((current_label, "; ".join(current_items)))
            current_label = stripped[4:].strip()
            current_items = []
        elif stripped.startswith("- "):
            current_items.append(stripped[2:].strip())
    if current_label and current_items:
        rows.append((current_label, "; ".join(current_items)))
    if not rows:
        return render_standard_panel(section)
    table_rows = "".join(f"<tr><th>{esc(k)}</th><td>{inline_format(v)}</td></tr>" for k, v in rows)
    return (
        f"<div class='panel panel-rotation'>{render_kicker(int(section['display_number']), str(section['title']))}"
        "<table class='snapshot-table'><thead><tr><th>Bucket</th><th>Action</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table></div>"
    )


def build_summary_strip(section1_body: str, section3_body: str) -> str:
    pairs1 = dict(extract_label_pairs(section1_body))
    pairs3 = dict(extract_label_pairs(section3_body))
    primary = pairs1.get("Primary regime", "Pending classification")
    geo = pairs1.get("Geopolitical regime", "Pending classification")
    takeaway = pairs1.get("Main takeaway", pairs1.get("Overall portfolio judgment", "Maintain disciplined positioning."))
    risk = pairs3.get("Risk regime", "Mild risk-off")
    return (
        "<div class='summary-strip'>"
        f"<div class='mini-card'><div class='mini-label'>Primary regime</div><div class='mini-value'>{esc(primary)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Risk regime</div><div class='mini-value'>{esc(risk)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Geopolitical regime</div><div class='mini-value'>{esc(geo)}</div></div>"
        f"<div class='mini-card mini-card-wide'><div class='mini-label'>Main takeaway</div><div class='mini-value mini-value-small'>{inline_format(takeaway)}</div></div>"
        "</div>"
    )


def chart_image_data(output_dir: Path) -> str:
    if plt is None:
        raise RuntimeError("Equity chart generation requires matplotlib. Install matplotlib in the workflow.")
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

    fig = plt.figure(figsize=(7.2, 4.2))
    ax = fig.add_subplot(111)
    ax.plot(range(len(rows)), [v for _, v in rows], linewidth=2.1)
    ax.set_title("Model portfolio development")
    ax.set_ylabel("Portfolio value (USD)")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([f"{d}\n{i+1}" for i, (d, _) in enumerate(rows)], rotation=35, ha="right")
    ax.grid(True, alpha=0.28)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def build_report_html(md_text: str, report_date_str: str, output_dir: Path, render_mode: str = "email") -> str:
    sections = parse_sections(md_text)
    section_map = {int(section["number"]): section for section in sections}
    display_date = report_date_str

    chart_b64 = chart_image_data(output_dir)

    for num in range(1, 8):
        if num in section_map:
            section_map[num]["display_number"] = num
    analyst_display = 1
    for num in range(8, 18):
        if num in section_map:
            section_map[num]["display_number"] = analyst_display
            analyst_display += 1

    summary_strip = build_summary_strip(str(section_map.get(1, {}).get("body", "")), str(section_map.get(3, {}).get("body", "")))

    client_left = []
    client_right = []
    if 1 in section_map:
        client_left.append(render_executive_summary(section_map[1]))
    if 2 in section_map:
        client_right.append(render_action_snapshot(section_map[2]))

    client_stack = []
    for num, extra in [
        (3, "panel-regime"),
        (4, "panel-radar"),
        (5, "panel-risks"),
        (6, "panel-bottomline"),
        (7, "panel-equity"),
    ]:
        if num not in section_map:
            continue
        client_stack.append(
            render_standard_panel(section_map[num], chart_b64=chart_b64 if num == 7 else None, extra_class=extra)
        )

    analyst_stack = []
    for num in range(8, 18):
        if num not in section_map:
            continue
        if num == 10:
            analyst_stack.append(render_currency_review(section_map[num]))
        elif num == 12:
            analyst_stack.append(render_rotation_plan(section_map[num]))
        else:
            analyst_stack.append(render_standard_panel(section_map[num]))

    css_common = f"""
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: {BRAND['paper']};
      color: {BRAND['ink']};
      font-family: Arial, Helvetica, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .report-shell {{ max-width: 980px; margin: 0 auto; padding: 0 0 18px 0; }}
    .hero {{
      background: {BRAND['header']};
      color: {BRAND['header_text']};
      padding: 20px 24px 18px 24px;
      border-radius: 14px 14px 0 0;
    }}
    .hero-secondary {{ margin-top: 28px; }}
    .hero-table {{ width: 100%; border-collapse: collapse; }}
    .hero-table td {{ vertical-align: middle; }}
    .hero-right {{ text-align: right; white-space: nowrap; padding-left: 24px; }}
    .masthead {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      font-size: 30px;
      letter-spacing: 1px;
      margin: 0 0 8px 0;
      text-transform: uppercase;
    }}
    .hero-sub {{ font-size: 14px; color: #EFF4F6; margin: 0; }}
    .hero-side-label {{
      font-size: 16px;
      line-height: 1.2;
      font-weight: 700;
      color: {BRAND['header_text']};
      letter-spacing: .03em;
    }}
    .hero-rule {{
      height: 5px;
      background: {BRAND['champagne']};
      margin: 8px 0 18px 0;
      border-radius: 999px;
    }}
    .notice {{
      background: #F8F4EE;
      border: 1px solid {BRAND['border']};
      color: {BRAND['muted']};
      border-radius: 14px;
      padding: 12px 16px;
      font-size: 12px;
      margin: 0 0 18px 0;
    }}
    .summary-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin: 0 0 18px 0;
    }}
    .mini-card {{
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 16px;
      padding: 14px 18px;
    }}
    .mini-card-wide {{ grid-column: span 3; }}
    .mini-label {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: {BRAND['muted']};
      margin: 0 0 8px 0;
    }}
    .mini-value {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      font-size: 22px;
      color: {BRAND['ink']};
      line-height: 1.24;
    }}
    .mini-value-small {{ font-size: 19px; }}
    .client-grid {{
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 18px;
      align-items: start;
      margin: 0 0 18px 0;
    }}
    .panel {{
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 18px;
      padding: 16px 18px;
      margin: 0 0 18px 0;
    }}
    .section-kicker {{
      width: auto;
      border-collapse: collapse;
      margin: 0 0 16px 0;
    }}
    .section-kicker td {{ vertical-align: middle; }}
    .section-badge-cell {{ width: 64px; padding: 0 16px 0 0; }}
    .section-badge {{
      width: 46px;
      height: 46px;
      border-radius: 999px;
      background: {BRAND['blue']};
      color: #ffffff;
      font-weight: 700;
      font-size: 17px;
      display: block;
      text-align: center;
      line-height: 46px;
      font-family: Arial, Helvetica, sans-serif;
    }}
    .section-label {{
      display: block;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: {BRAND['muted']};
      line-height: 1.14;
    }}
    .summary-line {{
      margin: 0 0 12px 0;
      padding: 0 0 12px 0;
      border-bottom: 1px solid {BRAND['border']};
    }}
    .summary-key {{
      color: {BRAND['muted']};
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      margin: 0 0 6px 0;
    }}
    .summary-value {{
      color: {BRAND['ink']};
      font-size: 14px;
      line-height: 1.56;
    }}
    .takeaway {{
      margin: 18px 0 0 0;
      padding: 14px 16px;
      border-radius: 12px;
      background: #F4EEE4;
      border: 1px solid #E7D7BB;
    }}
    .takeaway-label {{
      color: {BRAND['muted']};
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      margin: 0 0 6px 0;
    }}
    .takeaway-text {{
      color: {BRAND['ink']};
      font-size: 17px;
      font-weight: 700;
      line-height: 1.42;
    }}
    .snapshot-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0 0 16px 0;
      border: 1px solid {BRAND['border']};
      table-layout: fixed;
    }}
    .snapshot-table th {{
      background: #F2EBDD;
      color: {BRAND['ink']};
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid {BRAND['border']};
      font-size: 13px;
      font-weight: 700;
      vertical-align: top;
    }}
    .snapshot-table td {{
      padding: 9px 10px;
      border-bottom: 1px solid #ECE6DE;
      vertical-align: top;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }}
    .snapshot-table tbody tr:nth-child(even) td {{ background: #FEFCF9; }}
    .subblock {{
      margin: 0 0 14px 0;
      padding: 12px 14px;
      background: #FBF7F0;
      border: 1px solid {BRAND['border']};
      border-radius: 12px;
    }}
    .subblock-title {{
      color: {BRAND['muted']};
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      margin: 0 0 8px 0;
    }}
    .panel p, .panel li {{
      font-size: 14px;
      line-height: 1.58;
      margin-top: 0;
    }}
    .panel strong {{ font-weight: 700; }}
    .panel ul, .panel ol {{ margin-top: 0; padding-left: 22px; }}
    .panel h3 {{
      color: {BRAND['ink']};
      font-size: 18px;
      font-weight: 700;
      line-height: 1.35;
      margin: 18px 0 10px 0;
    }}
    .panel h4 {{
      color: {BRAND['muted']};
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
      font-weight: 700;
      margin: 18px 0 8px 0;
    }}
    .panel table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin: 12px 0 14px 0;
      border: 1px solid {BRAND['border']};
      font-size: 12px;
    }}
    .panel th {{
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid {BRAND['border']};
      background: #F2EBDD;
      color: {BRAND['ink']};
      vertical-align: middle;
      font-size: 12px;
      font-weight: 700;
    }}
    .panel td {{
      padding: 8px 10px;
      border-bottom: 1px solid #ECE6DE;
      vertical-align: top;
      word-wrap: break-word;
    }}
    .panel tr:nth-child(even) td {{ background: #FEFCF9; }}
    .panel blockquote {{
      margin: 12px 0;
      padding: 10px 12px;
      border-left: 4px solid {BRAND['champagne']};
      background: #F8F3EB;
      color: {BRAND['muted']};
    }}
    .table-wrap {{
      overflow: hidden;
      border-radius: 12px;
      border: 1px solid {BRAND['border']};
      margin: 10px 0 14px 0;
    }}
    .currency-card {{
      border: 1px solid {BRAND['border']};
      border-radius: 14px;
      background: #FEFCF9;
      padding: 14px 16px;
      margin: 0 0 14px 0;
    }}
    .currency-card-title {{
      font-size: 17px;
      font-weight: 700;
      color: {BRAND['ink']};
      margin: 0 0 10px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid {BRAND['border']};
    }}
    .chart-wrap {{
      margin-top: 14px;
      padding-top: 8px;
    }}
    .chart-label {{
      color: {BRAND['muted']};
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin: 0 0 10px 0;
    }}
    .chart-wrap img {{
      width: 100%;
      height: auto;
      border: 1px solid {BRAND['border']};
      border-radius: 12px;
      background: #ffffff;
      display: block;
    }}
    .footer-note {{
      color: {BRAND['muted']};
      font-size: 12px;
      margin-top: 6px;
    }}
    a {{
      color: #315F8B;
      text-decoration: underline;
    }}
    a.tv-link, a.tv-link:visited {{
      font-weight: 400;
    }}
    strong a.tv-link, strong a.tv-link:visited,
    b a.tv-link, b a.tv-link:visited {{
      font-weight: 400;
    }}
    """
    email_css = """
    @media screen and (max-width: 980px) {
      .summary-strip, .client-grid { display: block; }
      .hero-table, .hero-table tbody, .hero-table tr, .hero-table td { display: block; width: 100%; }
      .hero-right { text-align: left; padding-left: 0; padding-top: 10px; }
      .mini-card, .panel { margin-bottom: 16px; }
      .snapshot-table, .panel table { table-layout: auto; }
    }
    """
    pdf_css = """
    @page { size: A4 portrait; margin: 12mm; }
    body { background: #ffffff; }
    .report-shell { max-width: none; padding-bottom: 0; }
    .hero, .notice, .mini-card, .panel { page-break-inside: avoid; break-inside: avoid-page; }
    .summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .mini-card-wide { grid-column: span 2; }
    .client-grid { display: block; margin-bottom: 8px; }
    .panel { border-radius: 14px; padding: 15px 17px; margin-bottom: 12px; }
    .snapshot-table, .panel table { table-layout: auto; font-size: 11px; }
    .snapshot-table th, .snapshot-table td, .panel th, .panel td { padding: 6px 8px; }
    .chart-wrap img { max-height: 170mm; object-fit: contain; }
    """
    mode_css = email_css if render_mode == "email" else pdf_css

    analyst_appendix = ""
    if analyst_stack:
        analyst_appendix = (
            "<div class='hero hero-secondary'>"
            "<table class='hero-table' role='presentation' cellpadding='0' cellspacing='0'><tr>"
            f"<td><div class='masthead'>{esc(TITLE)}</div><p class='hero-sub'>{esc(display_date)}</p></td>"
            "<td class='hero-right'><div class='hero-side-label'>Analyst Report</div></td>"
            "</tr></table></div><div class='hero-rule'></div>"
            + "".join(analyst_stack)
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(TITLE)}</title>
<style>{css_common}{mode_css}</style>
</head>
<body>
<div class="report-shell">
  <div class="hero">
    <table class="hero-table" role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td><div class="masthead">{esc(TITLE)}</div><p class="hero-sub">{esc(display_date)}</p></td>
      <td class="hero-right"><div class="hero-side-label">Investor Report</div></td>
    </tr></table>
  </div>
  <div class="hero-rule"></div>
  <div class="notice">{esc(DISCLAIMER_LINE)}</div>
  {summary_strip}
  <div class="client-grid">{''.join(client_left)}{''.join(client_right)}</div>
  {''.join(client_stack)}
  {analyst_appendix}
  <div class="footer-note">Freshness-guarded delivery by send_fxreport.py</div>
</div>
</body>
</html>"""


def create_pdf_from_html(html_text: str, output_path: Path) -> None:
    if HTML is None:
        raise RuntimeError("PDF generation failed. Install WeasyPrint in the workflow.")
    HTML(string=html_text, base_url=str(output_path.parent)).write_pdf(str(output_path))


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

    html_email = build_report_html(md_text_clean, report_date_str, output_dir, render_mode="email")
    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    html_pdf = build_report_html(md_text_clean, report_date_str, output_dir, render_mode="pdf")
    create_pdf_from_html(html_pdf, pdf_path)

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

#!/usr/bin/env python3
"""
send_fxreport.py

Validate the newest Weekly FX Review markdown, render premium HTML/PDF,
and send it to the configured recipient.

This version is intentionally styling-focused. It keeps the FX content model intact
but upgrades the delivery layer so the FX report matches the ETF sister-report's
executive look & feel more closely.
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

try:
    import markdown as markdown_lib  # type: ignore
except Exception:  # pragma: no cover
    markdown_lib = None  # type: ignore

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore


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
    "sage": "#A4B19D",
    "terracotta": "#C99278",
    "add_bg": "#E6EFE8",
    "add_tx": "#4D7B63",
    "hold_bg": "#E8EEF6",
    "hold_tx": "#58749A",
    "replace_bg": "#F2E6DD",
    "replace_tx": "#A87754",
    "reduce_bg": "#F2E6CE",
    "reduce_tx": "#B28731",
    "close_bg": "#F5E1E1",
    "close_tx": "#B34E4E",
    "risk": "#B25A52",
}


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
    if "\\n" in text or "\\t" in text:
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


def clean_inline(text: str) -> str:
    text = strip_citations(text).strip()
    text = text.replace("**", "").replace("*", "").replace("`", "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def markdown_to_html(md: str) -> str:
    md = preprocess_markdown(md)
    if markdown_lib is not None:
        try:
            return markdown_lib.markdown(md, extensions=["tables", "sane_lists", "nl2br"])
        except Exception:
            pass
    return simple_markdown_to_html(md)


def preprocess_markdown(text: str) -> str:
    """Small normalizer for better-looking HTML without changing report substance."""
    lines = normalize_whitespace(text).splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        # hide the canonical sentence in the rendered appendix; keep it in markdown source
        if stripped == SECTION16_SENTENCE:
            continue
        # render A./B. subgroup labels as smaller headings
        if re.fullmatch(r"[A-Z]\.\s+.+", stripped):
            out.append(f"##### {stripped}")
            continue
        out.append(line)
    return "\n".join(out)


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
        if stripped.startswith("##### "):
            close_lists()
            parts.append(f"<h5>{esc(stripped[6:])}</h5>")
        elif stripped.startswith("#### "):
            close_lists()
            parts.append(f"<h4>{esc(stripped[5:])}</h4>")
        elif stripped.startswith("### "):
            close_lists()
            parts.append(f"<h3>{esc(stripped[4:])}</h3>")
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


def parse_label_value_lines(body: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            k = clean_inline(k)
            v = clean_inline(v)
            if k and v:
                pairs.append((k, v))
    return pairs


def extract_value_from_pairs(pairs: list[tuple[str, str]], key_substr: str) -> str:
    key_substr = key_substr.lower()
    for key, value in pairs:
        if key_substr in key.lower():
            return value
    return ""


def extract_summary_cards(sections: list[Section]) -> list[tuple[str, str]]:
    sec3 = next((s for s in sections if s.number == 3), None)
    sec6 = next((s for s in sections if s.number == 6), None)
    sec15 = next((s for s in sections if s.number == 15), None)
    cards: list[tuple[str, str]] = []

    if sec3:
        pairs = parse_label_value_lines(sec3.body)
        risk = extract_value_from_pairs(pairs, "risk regime")
        policy = extract_value_from_pairs(pairs, "policy divergence")
        tech = extract_value_from_pairs(pairs, "technical overlay")
        if risk:
            cards.append(("Risk regime", risk))
        if policy:
            cards.append(("Policy divergence", policy))
        if tech:
            cards.append(("Technical overlay", tech))

    if len(cards) < 3 and sec6:
        first_para = next((clean_inline(p) for p in sec6.body.split("\n\n") if clean_inline(p)), "")
        if first_para:
            cards.append(("Bottom line", first_para))
    if len(cards) < 3 and sec15:
        base = extract_value_from_pairs(parse_label_value_lines(sec15.body), "base currency")
        if base:
            cards.append(("Base currency", base))
    while len(cards) < 3:
        cards.append((f"FX review", "Disciplined weekly allocation framework"))
    return cards[:3]


def section_header_html(number: int, title: str) -> str:
    return (
        "<table class='section-kicker' role='presentation' cellpadding='0' cellspacing='0'><tr>"
        f"<td class='section-badge-cell'><span class='section-badge'>{number}</span></td>"
        f"<td class='section-label-cell'><span class='section-label'>{esc(title)}</span></td>"
        "</tr></table>"
    )


def render_standard_panel(section: Section, display_number: int, image_src: str | None = None, extra_class: str = "") -> str:
    body_html = markdown_to_html(section.body) if section.body else ""
    if section.number == 7 and image_src:
        body_html += f"<p><img class='eq' src='{esc(image_src)}' alt='Equity curve'></p>"
    return (
        f"<div class='panel {extra_class}'>"
        f"{section_header_html(display_number, section.title)}"
        f"{body_html}"
        f"</div>"
    )


def render_action_snapshot(section: Section, display_number: int) -> str:
    rows = []
    extras: list[str] = []
    for raw in section.body.splitlines():
        stripped = clean_inline(raw.strip())
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        if ":" in stripped and not re.match(r"^\d+\.\s+", stripped):
            key, value = stripped.split(":", 1)
            rows.append((key.strip(), value.strip()))
        else:
            extras.append(stripped)

    table_rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows)
    extras_html = ""
    if extras:
        items = "".join(f"<li>{esc(item)}</li>" for item in extras)
        extras_html = f"<div class='subblock'><div class='subblock-title'>Notes</div><ul>{items}</ul></div>"
    return (
        f"<div class='panel panel-snapshot'>"
        f"{section_header_html(display_number, section.title)}"
        f"<table class='snapshot-table'><thead><tr><th>Recommendation</th><th>FX stance / note</th></tr></thead><tbody>{table_rows}</tbody></table>"
        f"{extras_html}"
        f"</div>"
    )


def split_currency_blocks(body: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?m)^\*\*(.+?)\*\*\s*$")
    matches = list(pattern.finditer(body))
    blocks: list[tuple[str, str]] = []
    if not matches:
        return blocks
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        title = clean_inline(m.group(1))
        text = body[start:end].strip()
        blocks.append((title, text))
    return blocks


def render_currency_review(section: Section, display_number: int) -> str:
    blocks = split_currency_blocks(section.body)
    if not blocks:
        return render_standard_panel(section, display_number, extra_class="panel-positions")
    cards = []
    for title, body in blocks:
        body_html = markdown_to_html(body)
        cards.append(
            "<article class='currency-card'>"
            f"<div class='currency-card-title'>{esc(title)}</div>"
            f"<div class='currency-card-body'>{body_html}</div>"
            "</article>"
        )
    return (
        f"<div class='panel panel-positions'>"
        f"{section_header_html(display_number, section.title)}"
        f"{''.join(cards)}"
        f"</div>"
    )


def render_rotation_plan(section: Section, display_number: int) -> str:
    groups: dict[str, list[str]] = {}
    current_key = None
    for raw in section.body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if re.fullmatch(r"[A-Z]\.\s+.+", stripped):
            continue
        if stripped.startswith("- "):
            value = clean_inline(stripped[2:])
            groups.setdefault(current_key or "Items", []).append(value)
        elif stripped.endswith(":") and not stripped.startswith("**"):
            current_key = clean_inline(stripped[:-1])
            groups.setdefault(current_key, [])
        else:
            groups.setdefault(current_key or "Items", []).append(clean_inline(stripped))

    cols = ["Close", "Reduce", "Hold", "Add", "Replace"]
    heads = "".join(f"<th>{esc(col)}</th>" for col in cols)
    cells = []
    for col in cols:
        items = groups.get(col, [])
        if items:
            content = "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"
        else:
            content = "<div class='empty-cell'>None</div>"
        cells.append(f"<td>{content}</td>")
    return (
        f"<div class='panel panel-rotation'>"
        f"{section_header_html(display_number, section.title)}"
        f"<table class='rotation-table'><thead><tr>{heads}</tr></thead><tbody><tr>{''.join(cells)}</tr></tbody></table>"
        f"</div>"
    )


CSS_COMMON = f"""
* {{
  box-sizing: border-box;
}}
body {{
  margin: 0;
  padding: 0;
  background: {BRAND['paper']};
  color: {BRAND['ink']};
  font-family: Arial, Helvetica, sans-serif;
  -webkit-font-smoothing: antialiased;
}}
.report-shell {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 0 18px 0;
}}
.hero {{
  background: {BRAND['header']};
  color: {BRAND['header_text']};
  padding: 20px 24px 18px 24px;
  border-radius: 14px 14px 0 0;
}}
.hero-secondary {{
  margin-top: 26px;
}}
.hero-table {{
  width: 100%;
  border-collapse: collapse;
}}
.hero-table td {{
  vertical-align: middle;
}}
.hero-left {{
  text-align: left;
}}
.hero-right {{
  text-align: right;
  white-space: nowrap;
  padding-left: 24px;
}}
.masthead {{
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 700;
  font-size: 30px;
  letter-spacing: 1px;
  margin: 0 0 8px 0;
  text-transform: uppercase;
}}
.hero-sub {{
  font-size: 14px;
  color: #EFF4F6;
  margin: 0;
}}
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
  grid-template-columns: repeat(3, minmax(0,1fr));
  gap: 14px;
  margin: 0 0 18px 0;
}}
.mini-card {{
  background: {BRAND['surface']};
  border: 1px solid {BRAND['border']};
  border-radius: 16px;
  padding: 14px 18px;
}}
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
  font-size: 20px;
  color: {BRAND['ink']};
  line-height: 1.28;
}}
.client-grid {{
  display: grid;
  grid-template-columns: 1.3fr 1fr;
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
.panel-compact,
.panel-exec,
.panel-snapshot,
.panel-risks {{
  page-break-inside: avoid;
  break-inside: avoid-page;
}}
.section-kicker {{
  width: auto;
  border-collapse: collapse;
  margin: 0 0 18px 0;
}}
.section-kicker td {{
  vertical-align: middle;
}}
.section-badge-cell {{
  width: 64px;
  padding: 0 16px 0 0;
}}
.section-label {{
  display: block;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: {BRAND['muted']};
  line-height: 1.12;
}}
.section-badge {{
  width: 46px;
  height: 46px;
  border-radius: 999px;
  background: #2A5384;
  color: #ffffff;
  font-weight: 700;
  font-size: 17px;
  display: block;
  text-align: center;
  line-height: 46px;
  font-family: Arial, Helvetica, sans-serif;
}}
.snapshot-table,
.rotation-table {{
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 16px 0;
  border: 1px solid {BRAND['border']};
  table-layout: fixed;
}}
.snapshot-table th,
.rotation-table th {{
  background: #F2EBDD;
  color: {BRAND['ink']};
  text-align: left;
  padding: 9px 10px;
  border-bottom: 1px solid {BRAND['border']};
  font-size: 13px;
  font-weight: 700;
}}
.snapshot-table td,
.rotation-table td {{
  padding: 9px 10px;
  border-bottom: 1px solid #ECE6DE;
  vertical-align: top;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}}
.snapshot-table tbody tr:nth-child(even) td,
.rotation-table tbody tr:nth-child(even) td,
.panel tr:nth-child(even) td {{
  background: #FEFCF9;
}}
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
  font-weight: 400;
}}
.panel ul, .panel ol {{
  margin-top: 0;
  padding-left: 22px;
}}
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
.panel h5 {{
  color: {BRAND['muted']};
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .10em;
  font-weight: 700;
  margin: 12px 0 16px 0;
  text-align: right;
}}
.panel blockquote {{
  margin: 12px 0;
  padding: 10px 12px;
  border-left: 4px solid {BRAND['champagne']};
  background: #F8F3EB;
  color: {BRAND['muted']};
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
.panel img {{
  max-width: 100%;
  height: auto;
  border: 1px solid {BRAND['border']};
  border-radius: 10px;
  margin: 10px 0 4px 0;
  display: block;
}}
.currency-card {{
  border: 1px solid {BRAND['border']};
  background: #FCFAF7;
  border-radius: 14px;
  padding: 14px 16px;
  margin: 0 0 14px 0;
}}
.currency-card-title {{
  font-size: 18px;
  font-weight: 700;
  color: {BRAND['ink']};
  margin: 0 0 10px 0;
}}
.currency-card p:last-child {{
  margin-bottom: 0;
}}
.empty-cell {{
  color: {BRAND['muted']};
  font-style: italic;
}}
.footer-note {{
  color: {BRAND['muted']};
  font-size: 12px;
  margin-top: 14px;
}}
@media screen and (max-width: 1100px) {{
  .summary-strip, .client-grid {{
    display: block;
  }}
  .hero-table, .hero-table tbody, .hero-table tr, .hero-table td {{
    display: block;
    width: 100%;
  }}
  .hero-right {{
    text-align: left;
    padding-left: 0;
    padding-top: 10px;
  }}
  .mini-card, .panel {{
    margin-bottom: 16px;
  }}
}}
"""

PDF_CSS = """
@page {
  size: A4 landscape;
  margin: 12mm;
}
body {
  background: #ffffff;
}
.report-shell {
  max-width: none;
  padding-bottom: 0;
}
.panel, .mini-card, .subblock {
  page-break-inside: avoid;
  break-inside: avoid-page;
}
.snapshot-table, .rotation-table, .panel table {
  table-layout: auto;
  font-size: 11px;
}
.snapshot-table th, .snapshot-table td,
.rotation-table th, .rotation-table td,
.panel th, .panel td {
  padding: 6px 8px;
}
"""

PDF_FALLBACK_CSS = """
@page {
  size: A4 landscape;
  margin: 12mm;
}
body {
  background: #ffffff;
  color: #222;
}
.summary-strip, .client-grid {
  display: block;
}
.panel {
  page-break-inside: auto;
  break-inside: auto;
  margin-bottom: 12px;
}
.snapshot-table, .rotation-table, .panel table {
  table-layout: auto;
  font-size: 10.5px;
}
"""


def build_report_html(md_text: str, report_date_str: str, image_src: str | None = None, render_mode: str = "email") -> str:
    sections = parse_sections(md_text)
    sections_by_number = {s.number: s for s in sections}
    cards = extract_summary_cards(sections)
    summary_cards_html = "".join(
        f"<div class='mini-card'><div class='mini-label'>{esc(label)}</div><div class='mini-value'>{esc(value)}</div></div>"
        for label, value in cards
    )

    client_grid = []
    if 1 in sections_by_number:
        client_grid.append(render_standard_panel(sections_by_number[1], 1, extra_class="panel-exec"))
    if 2 in sections_by_number:
        client_grid.append(render_action_snapshot(sections_by_number[2], 2))

    client_panels = []
    client_map = {3: "panel-regime", 4: "panel-radar", 5: "panel-risks panel-compact", 6: "panel-bottomline panel-compact", 7: "panel-equity"}
    for display_number, num in enumerate([3, 4, 5, 6, 7], start=3):
        if num in sections_by_number:
            img = image_src if num == 7 else None
            client_panels.append(render_standard_panel(sections_by_number[num], display_number, image_src=img, extra_class=client_map.get(num, "")))

    analyst_panels = []
    analyst_display_number = 1
    for num in range(8, 18):
        if num not in sections_by_number:
            continue
        section = sections_by_number[num]
        if num == 10:
            analyst_panels.append(render_currency_review(section, analyst_display_number))
        elif num == 12:
            analyst_panels.append(render_rotation_plan(section, analyst_display_number))
        else:
            analyst_panels.append(render_standard_panel(section, analyst_display_number))
        analyst_display_number += 1

    mode_css = ""
    if render_mode == "pdf":
        mode_css = PDF_CSS
    elif render_mode == "pdf_fallback":
        mode_css = PDF_FALLBACK_CSS

    analyst_appendix = ""
    if analyst_panels:
        analyst_appendix = (
            "<div class='hero hero-secondary'>"
            "<table class='hero-table' role='presentation' cellpadding='0' cellspacing='0'><tr>"
            f"<td class='hero-left'><div class='masthead'>WEEKLY FX REVIEW</div><p class='hero-sub'>{esc(report_date_str)}</p></td>"
            "<td class='hero-right'><div class='hero-side-label'>Analyst Report</div></td>"
            "</tr></table>"
            "</div><div class='hero-rule'></div>"
            + "".join(analyst_panels)
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(TITLE)}</title>
<style>{CSS_COMMON}{mode_css}</style>
</head>
<body>
  <div class="report-shell">
    <div class="hero">
      <table class="hero-table" role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td class="hero-left"><div class="masthead">WEEKLY FX REVIEW</div><p class="hero-sub">{esc(report_date_str)}</p></td>
        <td class="hero-right"><div class="hero-side-label">Investor Report</div></td>
      </tr></table>
    </div>
    <div class="hero-rule"></div>
    <div class="notice">{esc(DISCLAIMER_LINE)}</div>
    <div class="summary-strip">{summary_cards_html}</div>
    <div class="client-grid">{''.join(client_grid)}</div>
    <div class="report-stack">{''.join(client_panels)}{analyst_appendix}</div>
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


def create_pdf_from_html(html_text: str, output_path: Path, fallback_html: str | None = None) -> None:
    try:
        from weasyprint import HTML  # type: ignore

        HTML(string=html_text, base_url=str(output_path.parent)).write_pdf(str(output_path))
    except AssertionError:
        if not fallback_html:
            raise
        from weasyprint import HTML  # type: ignore

        HTML(string=fallback_html, base_url=str(output_path.parent)).write_pdf(str(output_path))
    except Exception as exc:
        raise RuntimeError("PDF generation failed. Install WeasyPrint in the workflow dependencies.") from exc


def parse_section15_value(md_text: str, label: str) -> float | None:
    sec15 = section_body(md_text, 15)
    pattern = re.compile(rf"^{re.escape(label)}\s*(.+?)\s*$", re.MULTILINE)
    m = pattern.search(sec15)
    if not m:
        return None
    raw = m.group(1).replace(",", "").replace("$", "").strip()
    raw = re.sub(r"[^\d.\-]", "", raw)
    try:
        return float(raw)
    except ValueError:
        return None


def create_equity_curve_png(output_dir: Path, output_png: Path) -> bool:
    if plt is None:
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

    plt.figure(figsize=(8.8, 3.4))
    plt.plot(x, y, linewidth=2.2)
    plt.xticks(x, labels, rotation=45, ha="right", fontsize=8)
    plt.ylabel("Portfolio value (USD)")
    plt.title("Model portfolio development")
    plt.grid(True, alpha=0.28)
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

    html_email = build_report_html(md_text_clean, report_date_str, image_src=image_src_email, render_mode="email")
    html_pdf = build_report_html(md_text_clean, report_date_str, image_src=image_src_pdf, render_mode="pdf")
    html_pdf_fallback = build_report_html(md_text_clean, report_date_str, image_src=image_src_pdf, render_mode="pdf_fallback")

    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    create_pdf_from_html(html_pdf, pdf_path, fallback_html=html_pdf_fallback)
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

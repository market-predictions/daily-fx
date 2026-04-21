
#!/usr/bin/env python3
"""
send_fxreport.py

Executive-grade FX delivery/rendering script.

Goals:
- preserve the working one-click workflow
- preserve live equity-curve calculation and plotting
- preserve CID inline chart handling for email compatibility
- restore the stronger executive-grade email/PDF look & feel
- keep the public module contract expected by GitHub Actions:
    * latest_report_file(output_dir)
    * generate_delivery_assets(output_dir, report_path)
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import markdown as mdlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weasyprint import HTML


TITLE = "Weekly FX Review"
DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."
REQUIRED_MAIL_TO = "mrkt.rprts@gmail.com"

REPORT_RE = re.compile(r"^weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$")

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
}

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
SECTION16_SENTENCE = "**This section is the canonical default input for the next run unless the user explicitly overrides it.**"

TV_LINKS = {
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


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable missing: {name}")
    return value


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\\n" in text or "\\t" in text:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    return text


def strip_citations(text: str) -> str:
    text = normalize_whitespace(text)
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


def report_sort_key(path: Path) -> tuple[str, int]:
    match = REPORT_RE.match(path.name)
    if not match:
        return ("", -1)
    return (match.group(1), int(match.group(2) or "0"))


def list_report_files(output_dir: Path) -> list[Path]:
    return sorted(
        [p for p in output_dir.glob("weekly_fx_review_*.md") if REPORT_RE.match(p.name)],
        key=report_sort_key,
    )


def latest_report_file(output_dir: Path) -> Path:
    reports = list_report_files(output_dir)
    if not reports:
        raise FileNotFoundError("No weekly_fx_review_*.md file found in output/")
    return reports[-1]


def parse_report_date(md_text: str, report_path: Optional[Path] = None) -> str:
    title_match = re.search(
        r"^#\s+Weekly FX Review(?:\s+(\d{4}-\d{2}-\d{2}))?\s*$",
        md_text,
        flags=re.MULTILINE,
    )
    if title_match and title_match.group(1):
        return title_match.group(1)
    if report_path is not None:
        match = REPORT_RE.match(report_path.name)
        if match:
            token = match.group(1)
            yy = int(token[0:2])
            mm = int(token[2:4])
            dd = int(token[4:6])
            return f"{2000 + yy:04d}-{mm:02d}-{dd:02d}"
    return datetime.utcnow().strftime("%Y-%m-%d")


def format_full_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%A')}, {dt.day} {dt.strftime('%B %Y')}"


def section_body(md_text: str, section_number: int) -> str:
    lines = md_text.splitlines()
    capture: list[str] = []
    in_section = False
    target = f"## {section_number}."
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped.startswith(target):
                in_section = True
                continue
            if in_section:
                break
        if in_section:
            capture.append(line)
    return "\n".join(capture).strip()


def extract_labeled_value(section_text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}\s*\*\*(.*?)\*\*\s*$", section_text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(rf"^- {re.escape(label)}\s*(.*?)\s*$", section_text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_sections(md_text: str) -> tuple[str, list[dict]]:
    title = ""
    sections: list[dict] = []
    current: Optional[dict] = None

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if line.startswith("# "):
            title = line[2:].strip()
            continue

        match = SECTION_RE.match(stripped)
        if match:
            if current:
                sections.append(current)
            current = {
                "number": int(match.group(1)),
                "title": match.group(2).strip(),
                "lines": [],
            }
            continue

        if current is not None:
            current["lines"].append(line)

    if current:
        sections.append(current)

    return title, sections


def validate_required_report(md_text: str) -> None:
    missing = [heading for heading in REQUIRED_SECTION_HEADINGS if heading not in md_text]
    if missing:
        raise RuntimeError("Report is missing mandatory section headings: " + ", ".join(missing))
    for label in REQUIRED_SECTION15_LABELS:
        if label not in md_text:
            raise RuntimeError(f"Section 15 is missing required label: {label}")
    if SECTION16_SENTENCE not in md_text:
        raise RuntimeError("Section 16 canonical carry-forward sentence is missing.")


def validate_report_freshness(md_text: str, portfolio_state: dict) -> None:
    report_date = parse_report_date(md_text)
    valuation_date = str(portfolio_state.get("last_valuation", {}).get("date", "")).strip()
    if valuation_date and report_date < valuation_date:
        raise RuntimeError(
            f"Report date {report_date} is older than portfolio valuation date {valuation_date}."
        )


def html_to_plain_text(html: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def plain_text_from_markdown(md_text: str) -> str:
    return html_to_plain_text(mdlib.markdown(strip_citations(md_text), extensions=["tables", "sane_lists"]))


def write_delivery_manifest(manifest_path: Path, report_name: str, recipient: str, attachments: list[str]) -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"timestamp_utc={timestamp}",
        f"report={report_name}",
        f"recipient={recipient}",
        "html_body=full_report",
        f"pdf_attached={'yes' if any(a.lower().endswith('.pdf') for a in attachments) else 'no'}",
        "attachments=" + ", ".join(attachments),
    ]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_equity_curve_png(output_dir: Path, chart_path: Path) -> Optional[Path]:
    valuation_path = output_dir / "fx_valuation_history.csv"
    if not valuation_path.exists():
        return None

    dates: list[datetime] = []
    navs: list[float] = []

    with valuation_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                dates.append(datetime.strptime(row["date"], "%Y-%m-%d"))
                navs.append(float(row["nav_usd"]))
            except Exception:
                continue

    if not dates or not navs:
        return None

    plt.figure(figsize=(8.8, 3.7))
    plt.plot(dates, navs, marker="o", linewidth=2.2)
    plt.title("Model portfolio development")
    plt.xlabel("Date")
    plt.ylabel("Portfolio value (USD)")
    plt.grid(True, alpha=0.28)
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180)
    plt.close()
    return chart_path if chart_path.exists() else None


def png_to_data_uri(path: Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def inject_chart_html(section_html: str, image_src: Optional[str]) -> str:
    if image_src:
        chart_block = (
            '<div class="chart-wrap">'
            '<div class="chart-label">Model portfolio development</div>'
            f'<img src="{image_src}" alt="Model portfolio development chart">'
            '</div>'
        )
    else:
        chart_block = (
            '<div class="chart-wrap">'
            '<div class="chart-label">Model portfolio development</div>'
            '<div class="chart-missing">Chart unavailable for this delivery.</div>'
            '</div>'
        )
    return chart_block + section_html


def autolink_currency_codes(html: str) -> str:
    placeholders: dict[str, str] = {}

    def stash(match: re.Match) -> str:
        key = f"__HTMLTAG_{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    protected = re.sub(r"<[^>]+>", stash, html)
    for code, url in TV_LINKS.items():
        protected = re.sub(
            rf"\b{re.escape(code)}\b",
            f'<a class="tv-link" href="{url}" target="_blank" rel="noopener noreferrer">{code}</a>',
            protected,
        )
    for key, value in placeholders.items():
        protected = protected.replace(key, value)
    return protected


def markdown_block_to_html(text: str) -> str:
    cleaned = strip_citations(text).strip()
    if not cleaned:
        return ""
    html = mdlib.markdown(
        cleaned,
        extensions=["tables", "sane_lists", "fenced_code"],
        output_format="html5",
    )
    return autolink_currency_codes(html)


def section_header_html(number: int, title: str) -> str:
    return (
        '<table class="section-kicker" role="presentation" cellpadding="0" cellspacing="0"><tr>'
        f'<td class="section-badge-cell"><span class="section-badge">{number}</span></td>'
        f'<td class="section-label-cell"><span class="section-label">{title}</span></td>'
        '</tr></table>'
    )


def render_standard_panel(section: dict, display_number: int, extra_class: str = "", image_src: Optional[str] = None) -> str:
    body_html = markdown_block_to_html("\n".join(section["lines"]))
    if section["number"] == 7:
        body_html = inject_chart_html(body_html, image_src=image_src)
    return (
        f'<div class="panel {extra_class}">'
        f'{section_header_html(display_number, section["title"])}'
        f'{body_html}'
        f'</div>'
    )


def extract_regime_summary(executive_text: str) -> str:
    patterns = [
        r"strategic regime remains \*\*(.*?)\*\*",
        r"strategic regime remains (.*?)(?:\.|\n)",
        r"regime remains \*\*(.*?)\*\*",
    ]
    for pattern in patterns:
        match = re.search(pattern, executive_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return "Defensive carry-forward regime"


def build_summary_cards(
    portfolio_state: dict,
    manifest: Optional[dict],
    overlay: Optional[dict],
    executive_section_text: str,
) -> str:
    regime = extract_regime_summary(executive_section_text)
    nav = float(portfolio_state.get("nav_usd", 0.0))
    cash = float(portfolio_state.get("cash_usd", 0.0))
    unrealized = float(portfolio_state.get("last_valuation", {}).get("unrealized_pnl_usd", 0.0))
    overlay_ts = ""
    if manifest:
        overlay_ts = str(manifest.get("overlay_as_of_utc", ""))
    if not overlay_ts and overlay:
        overlay_ts = str(overlay.get("as_of_utc", ""))
    overlay_short = overlay_ts if not overlay_ts else overlay_ts.replace("T", " ").replace("Z", " UTC")

    usd_ta = ""
    if overlay:
        usd_ta = str(overlay.get("currencies", {}).get("USD", {}).get("ta_status", "")).strip()
    usd_ta = usd_ta or "n/a"

    cards = [
        ("Primary regime", regime),
        ("Portfolio value", f"{nav:,.2f} USD"),
        ("Cash", f"{cash:,.2f} USD"),
        ("Unrealized P&L", f"{unrealized:,.2f} USD"),
        ("USD technical", usd_ta.title()),
        ("Overlay timestamp", overlay_short or "Unavailable"),
    ]

    return "".join(
        f'<div class="mini-card"><div class="mini-label">{label}</div><div class="mini-value">{value}</div></div>'
        for label, value in cards
    )


def build_report_html(
    md_text: str,
    report_date_str: str,
    output_dir: Optional[Path] = None,
    render_mode: str = "email",
    image_src: Optional[str] = None,
) -> str:
    _, sections = extract_sections(md_text)
    sections_by_number = {section["number"]: section for section in sections}
    display_date_str = format_full_date(report_date_str)

    portfolio_state = load_json(output_dir / "fx_portfolio_state.json") if output_dir else {}
    manifest = load_json(output_dir / "fx_state_refresh_manifest.json") if output_dir and (output_dir / "fx_state_refresh_manifest.json").exists() else None
    overlay = load_json(output_dir / "fx_technical_overlay.json") if output_dir and (output_dir / "fx_technical_overlay.json").exists() else None

    executive_text = "\n".join(sections_by_number.get(1, {}).get("lines", []))
    summary_cards = build_summary_cards(portfolio_state, manifest, overlay, executive_text)

    client_grid = []
    if 1 in sections_by_number:
        client_grid.append(render_standard_panel(sections_by_number[1], 1, extra_class="panel-exec"))
    if 2 in sections_by_number:
        client_grid.append(render_standard_panel(sections_by_number[2], 2, extra_class="panel-snapshot"))

    client_panels = []
    for display_number, number in enumerate([3, 4, 5, 6, 7], start=3):
        if number in sections_by_number:
            extra_class = {
                3: "panel-regime",
                4: "panel-radar",
                5: "panel-risks panel-compact",
                6: "panel-bottomline panel-compact",
                7: "panel-equity",
            }.get(number, "")
            client_panels.append(
                render_standard_panel(
                    sections_by_number[number],
                    display_number,
                    extra_class=extra_class,
                    image_src=image_src if number == 7 else None,
                )
            )

    analyst_panels = []
    analyst_display_number = 1
    for number in range(8, 18):
        if number in sections_by_number:
            extra_class = "panel-analyst"
            if number == 17:
                extra_class += " panel-disclaimer"
            analyst_panels.append(
                render_standard_panel(
                    sections_by_number[number],
                    analyst_display_number,
                    extra_class=extra_class,
                )
            )
            analyst_display_number += 1

    css_common = f"""
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
      font-family: Georgia, \"Times New Roman\", serif;
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
      font-family: Georgia, \"Times New Roman\", serif;
      font-weight: 700;
      font-size: 21px;
      color: {BRAND['ink']};
      line-height: 1.22;
    }}
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
      vertical-align: middle;
    }}
    .section-label-cell {{
      padding: 0;
      vertical-align: middle;
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
    .section-label {{
      display: block;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: {BRAND['muted']};
      line-height: 1.12;
    }}
    .panel p, .panel li {{
      font-size: 14px;
      line-height: 1.58;
      margin-top: 0;
      font-weight: 400;
    }}
    .panel strong {{
      font-weight: 700;
    }}
    .panel ul, .panel ol {{
      margin-top: 0;
      padding-left: 22px;
    }}
    .panel h1 {{
      display: none;
    }}
    .panel h2 {{
      color: {BRAND['muted']};
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
      font-weight: 700;
      margin: 18px 0 10px 0;
    }}
    .panel h2:first-of-type {{
      margin-top: 0;
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
    .panel tr:nth-child(even) td {{
      background: #FEFCF9;
    }}
    .panel blockquote {{
      margin: 12px 0;
      padding: 10px 12px;
      border-left: 4px solid {BRAND['champagne']};
      background: #F8F3EB;
      color: {BRAND['muted']};
    }}
    .chart-wrap {{
      margin: 12px 0 18px 0;
      padding: 12px 14px;
      background: #FBF7F0;
      border: 1px solid {BRAND['border']};
      border-radius: 14px;
    }}
    .chart-label {{
      color: {BRAND['muted']};
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin: 0 0 8px 0;
    }}
    .chart-missing {{
      color: {BRAND['muted']};
      font-size: 13px;
      font-style: italic;
    }}
    .chart-wrap img {{
      max-width: 100%;
      height: auto;
      border: 1px solid {BRAND['border']};
      border-radius: 10px;
      margin: 0;
      display: block;
      background: #fff;
    }}
    .analyst-divider {{
      display: none;
    }}
    a {{
      color: #315F8B;
      text-decoration: underline;
      font-weight: 400;
    }}
    a:visited {{
      color: #315F8B;
      font-weight: 400;
    }}
    a.tv-link, a.tv-link:visited {{
      font-weight: 400;
    }}
    strong a, strong a:visited,
    b a, b a:visited,
    strong a.tv-link, strong a.tv-link:visited,
    b a.tv-link, b a.tv-link:visited {{
      font-weight: 400;
    }}
    """

    email_css = """
    .report-stack {
      margin-top: 0;
    }
    @media screen and (max-width: 1100px) {
      .summary-strip, .client-grid {
        display: block;
      }
      .hero-table, .hero-table tbody, .hero-table tr, .hero-table td {
        display: block;
        width: 100%;
      }
      .hero-right {
        text-align: left;
        padding-left: 0;
        padding-top: 10px;
      }
      .mini-card, .panel {
        margin-bottom: 16px;
      }
      .panel table {
        table-layout: auto;
      }
    }
    """

    pdf_css = """
    @page {
      size: A4 portrait;
      margin: 12mm;
    }
    body {
      background: #ffffff;
    }
    .report-shell {
      max-width: none;
      padding-bottom: 0;
    }
    .hero, .notice, .summary-strip, .panel-compact, .panel-exec, .panel-snapshot, .panel-risks, .mini-card {
      page-break-inside: avoid;
      break-inside: avoid-page;
    }
    .hero {
      border-radius: 10px 10px 0 0;
      padding: 20px 22px 18px 22px;
    }
    .summary-strip {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .client-grid {
      display: block;
      margin-bottom: 8px;
    }
    .panel {
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 14px;
    }
    .panel table {
      table-layout: auto;
      font-size: 11px;
    }
    .panel th, .panel td {
      padding: 6px 8px;
    }
    .chart-wrap {
      page-break-inside: avoid;
      break-inside: avoid-page;
    }
    .chart-wrap img {
      max-height: 170mm;
      object-fit: contain;
    }
    .analyst-divider {
      display: block;
      page-break-before: always;
      break-before: page;
      margin-top: 4px;
    }
    """

    mode_css = pdf_css if render_mode == "pdf" else email_css

    analyst_appendix = ""
    if analyst_panels:
        analyst_appendix = (
            '<div class="analyst-divider"></div>'
            f'<div class="hero hero-secondary">'
            f'<table class="hero-table" role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td class="hero-left"><div class="masthead">WEEKLY FX REVIEW</div><p class="hero-sub">{display_date_str}</p></td>'
            f'<td class="hero-right"><div class="hero-side-label">Analyst Report</div></td>'
            f'</tr></table>'
            f'</div><div class="hero-rule"></div>'
            + "".join(analyst_panels)
        )

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>{css_common}{mode_css}</style>
      </head>
      <body>
        <div class="report-shell">
          <div class="hero">
            <table class="hero-table" role="presentation" cellpadding="0" cellspacing="0"><tr>
              <td class="hero-left"><div class="masthead">WEEKLY FX REVIEW</div><p class="hero-sub">{display_date_str}</p></td>
              <td class="hero-right"><div class="hero-side-label">Investor Report</div></td>
            </tr></table>
          </div>
          <div class="hero-rule"></div>
          <div class="notice">{DISCLAIMER_LINE}</div>
          <div class="summary-strip">{summary_cards}</div>
          <div class="client-grid">{''.join(client_grid)}</div>
          <div class="report-stack">{''.join(client_panels)}{analyst_appendix}</div>
        </div>
      </body>
    </html>
    """
    return html.strip()


def validate_email_body(html_body: str, md_text: Optional[str] = None) -> None:
    html_lower = html_body.lower()
    if "weekly fx review" not in html_lower:
        raise RuntimeError("HTML body is missing required masthead block: WEEKLY FX REVIEW")

    required_tokens = [
        "Executive summary",
        "Portfolio action snapshot",
        "Bottom line",
        "Current portfolio holdings and cash",
        "Carry-forward input for next run",
    ]
    for token in required_tokens:
        if token.lower() not in html_lower:
            raise RuntimeError(f"HTML body is missing required content block: {token}")

    if md_text:
        plain_html = html_to_plain_text(html_body)
        plain_md = html_to_plain_text(mdlib.markdown(md_text, extensions=["tables", "sane_lists"]))
        if len(plain_html) < 0.80 * len(plain_md):
            raise RuntimeError("HTML body appears too short relative to the full report.")

    for bad_token in ["\\n", "#### ", "|---|", "\\t"]:
        if bad_token in html_body:
            raise RuntimeError(f"HTML body still contains raw markdown / escaped formatting token: {bad_token}")


def create_pdf_from_html(html: str, output_path: Path) -> None:
    HTML(string=html, base_url=str(output_path.parent)).write_pdf(str(output_path))


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

    chart_path = report_path.with_name(f"{safe_stem}_equity_curve.png")
    chart_exists = create_equity_curve_png(output_dir, chart_path)

    html_email = build_report_html(
        md_text_clean,
        report_date_str,
        output_dir=output_dir,
        render_mode="email",
        image_src="cid:fx_equity_chart" if chart_exists else None,
    )
    validate_email_body(html_email, md_text_clean)

    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    html_pdf = build_report_html(
        md_text_clean,
        report_date_str,
        output_dir=output_dir,
        render_mode="pdf",
        image_src=png_to_data_uri(chart_path) if chart_exists else None,
    )
    if chart_exists and 'data:image/png;base64,' not in html_pdf:
        raise RuntimeError("FX equity curve image was not embedded into PDF HTML.")
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
        "chart_path": chart_path if chart_exists else None,
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

    related = MIMEMultipart("related")
    related.attach(MIMEText(assets["html_email"], "html", "utf-8"))

    attachments = [
        assets["pdf_path"].name,
        assets["clean_md_path"].name,
        assets["html_path"].name,
    ]

    if assets["chart_path"] and assets["chart_path"].exists():
        png_bytes = assets["chart_path"].read_bytes()

        inline_png = MIMEImage(png_bytes, _subtype="png")
        inline_png.add_header("Content-ID", "<fx_equity_chart>")
        inline_png.add_header("Content-Disposition", "inline", filename=assets["chart_path"].name)
        related.attach(inline_png)

        png_attachment = MIMEApplication(png_bytes, _subtype="png")
        png_attachment.add_header("Content-Disposition", "attachment", filename=assets["chart_path"].name)
        root.attach(png_attachment)
        attachments.append(assets["chart_path"].name)

    alternative.attach(related)
    root.attach(alternative)

    for path in [assets["pdf_path"], assets["clean_md_path"], assets["html_path"]]:
        subtype = "pdf" if path.suffix == ".pdf" else ("markdown" if path.suffix == ".md" else "html")
        with path.open("rb") as handle:
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
    latest = latest_report_file(output_dir)
    assets = generate_delivery_assets(output_dir, latest)

    if args.validate_only:
        section15 = section_body(assets["md_text_clean"], 15)
        cash = extract_labeled_value(section15, "Cash (USD):")
        nav = extract_labeled_value(section15, "Total portfolio value (USD):")
        print(f"REPORT_FRESHNESS_OK | report={latest.name} | cash={cash} | nav={nav}")
        return

    attachments, manifest_path, mail_to = send_email_with_attachments(assets)
    print(
        f"DELIVERY_OK | report={latest.name} | recipient={mail_to} | "
        f"html_body=full_report | pdf_attached=yes | manifest={manifest_path.name} | "
        f"attachments={', '.join(attachments)}"
    )


if __name__ == "__main__":
    main()

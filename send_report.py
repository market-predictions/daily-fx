
import os
import re
import base64
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mistune
from weasyprint import HTML


# ---------- BRAND TOKENS ----------
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

DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."
REQUIRED_MAIL_TO = "mrkt.rprts@gmail.com"

REQUIRED_SECTION_HEADINGS = [
    "## 1. ✅ Executive summary",
    "## 2. 📌 Portfolio action snapshot",
    "## 3. 🧭 Regime dashboard",
    "## 4. 🚀 Structural Opportunity Radar",
    "## 5. 📅 Key risks / invalidators",
    "## 6. 🧭 Bottom line",
    "## 7. 📈 Equity curve and portfolio development",
    "## 8. 🗺️ Asset allocation map",
    "## 9. 🔍 Second-order effects map",
    "## 10. 📊 Current position review",
    "## 11. ➕ Best new opportunities",
    "## 12. 🔁 Portfolio rotation plan",
    "## 13. 📋 Final action table",
    "## 14. 🔄 Position changes executed this run",
    "## 15. 💼 Current portfolio holdings and cash",
    "## 16. 🧾 Carry-forward input for next run",
    "## 17. Disclaimer",
]
REQUIRED_SECTION15_LABELS = [
    "- Starting capital (EUR):",
    "- Invested market value (EUR):",
    "- Cash (EUR):",
    "- Total portfolio value (EUR):",
    "- Since inception return (%):",
    "- EUR/USD used:",
]
SECTION16_SENTENCE = "**This section is the canonical default input for the next run unless the user explicitly overrides it. Do not ask the user for portfolio input if this section is available.**"

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

REPORT_RE = re.compile(r"^weekly_analysis_(\d{6})(?:_(\d{2}))?\.md$")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$")
MARKDOWN = mistune.create_markdown(plugins=["table"])


# ---------- DISCOVERY ----------
def report_sort_key(path: Path):
    match = REPORT_RE.match(path.name)
    if not match:
        return ("", -1)
    date_key = match.group(1)
    version = int(match.group(2) or "1")
    return (date_key, version)


def list_report_files(output_dir: Path):
    files = [p for p in output_dir.glob("weekly_analysis_*.md") if REPORT_RE.match(p.name)]
    return sorted(files, key=report_sort_key)


def latest_report_file(output_dir: Path) -> Path:
    reports = list_report_files(output_dir)
    if not reports:
        raise FileNotFoundError("No weekly_analysis_*.md file found in output/")
    return reports[-1]


def latest_reports_by_day(output_dir: Path):
    latest_per_day = OrderedDict()
    for path in list_report_files(output_dir):
        base_date, _ = report_sort_key(path)
        latest_per_day[base_date] = path
    return list(latest_per_day.values())


# ---------- SANITIZERS ----------
def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable missing: {name}")
    return value


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


def html_to_plain_text(html: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def plain_text_from_markdown(md_text: str) -> str:
    return html_to_plain_text(MARKDOWN(strip_citations(md_text)))


def esc(text: str) -> str:
    text = clean_md_inline(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_markdown_table_line(line: str) -> bool:
    line = line.strip()
    return line.startswith("|") and line.endswith("|") and "|" in line[1:-1]


def is_markdown_separator_line(line: str) -> bool:
    if not is_markdown_table_line(line):
        return False
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_markdown_table(lines):
    rows = []
    for i, line in enumerate(lines):
        if i == 1 and is_markdown_separator_line(line):
            continue
        rows.append([clean_md_inline(c) for c in line.strip().strip("|").split("|")])
    return rows


def pretty_section_title(raw: str) -> str:
    text = clean_md_inline(raw)
    text = re.sub(r"^[^\w]+", "", text).strip()
    return text or clean_md_inline(raw)


def heading_text_from_md_heading(heading: str) -> str:
    heading = re.sub(r"^##\s+\d+\.\s+", "", heading).strip()
    return pretty_section_title(heading)


# ---------- PARSING ----------
def parse_report_date(md_text: str, fallback: str | None = None) -> str:
    match = re.search(r"^#\s+Weekly Report Review\s+(\d{4}-\d{2}-\d{2})\s*$", md_text, flags=re.MULTILINE)
    if match:
        return match.group(1)
    return fallback or datetime.now().strftime("%Y-%m-%d")


def extract_section(md_text: str, title_contains: str):
    lines = md_text.splitlines()
    result = []
    in_section = False
    title_contains = title_contains.lower()

    for line in lines:
        stripped = line.strip()
        if SECTION_RE.match(stripped):
            current_title = clean_md_inline(re.sub(r"^##\s+\d+\.\s+", "", stripped))
            if title_contains in current_title.lower():
                in_section = True
                result.append(stripped)
                continue
            if in_section:
                break
        elif in_section:
            result.append(line)
    return result


def extract_label_pairs(lines):
    pairs = []
    for line in lines:
        s = clean_md_inline(line.strip())
        if not s or s.startswith("## "):
            continue
        if s.startswith("- "):
            s = s[2:]
        if ":" in s:
            k, v = s.split(":", 1)
            pairs.append((k.strip(), v.strip()))
    return pairs


def parse_numeric_value(md_text: str, label: str):
    pattern = rf"^- {re.escape(label)}:\s*([0-9][0-9,._%-]*)"
    match = re.search(pattern, md_text, flags=re.MULTILINE)
    if not match:
        return None
    raw = match.group(1).replace(",", "").replace("_", "").replace("%", "")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_section15_totals(md_text: str):
    section = "\n".join(extract_section(md_text, "Current portfolio holdings and cash"))
    if not section:
        return {}
    labels = [
        "Starting capital (EUR)",
        "Invested market value (EUR)",
        "Cash (EUR)",
        "Total portfolio value (EUR)",
        "Since inception return (%)",
        "EUR/USD used",
    ]
    data = {}
    for label in labels:
        value = parse_numeric_value(section, label)
        if value is not None:
            data[label] = value
    return data


def extract_sections(md_text: str):
    title = ""
    sections = []
    current = None

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if line.startswith("# "):
            title = clean_md_inline(line[2:])
            continue

        match = SECTION_RE.match(stripped)
        if match:
            if current:
                sections.append(current)
            current = {
                "number": int(match.group(1)),
                "raw_title": match.group(2),
                "title": pretty_section_title(match.group(2)),
                "lines": [],
            }
            continue

        if current is not None:
            current["lines"].append(line)

    if current:
        sections.append(current)

    return title, sections


# ---------- VALIDATION ----------
def validate_required_report(md_text: str) -> None:
    missing_headings = [h for h in REQUIRED_SECTION_HEADINGS if h not in md_text]
    if missing_headings:
        raise RuntimeError("Report is missing mandatory section headings: " + ", ".join(missing_headings))

    if "# Weekly Report Review " not in md_text:
        raise RuntimeError("Report title is missing or malformed.")

    if f"> *{DISCLAIMER_LINE}*" not in md_text:
        raise RuntimeError("Top disclaimer callout is missing.")

    if "EQUITY_CURVE_CHART_PLACEHOLDER" not in md_text:
        raise RuntimeError("Equity curve placeholder line is missing.")

    for label in REQUIRED_SECTION15_LABELS:
        if label not in md_text:
            raise RuntimeError(f"Section 15 is missing required label: {label}")

    if SECTION16_SENTENCE not in md_text:
        raise RuntimeError("Section 16 canonical carry-forward sentence is missing.")

    if "This report is provided for informational and educational purposes only." not in md_text:
        raise RuntimeError("Final disclaimer body is missing.")


def validate_email_body(html_body: str, md_text: str | None = None) -> None:
    required_strings = [
        "Weekly Report Review",
        "Executive summary",
        "Portfolio action snapshot",
        "Structural Opportunity Radar",
        "Bottom line",
        "Current portfolio holdings and cash",
        "Carry-forward input for next run",
    ]
    for token in required_strings:
        if token not in html_body:
            raise RuntimeError(f"HTML body is missing required content block: {token}")

    if md_text:
        plain_html = html_to_plain_text(html_body)
        plain_md = html_to_plain_text(MARKDOWN(md_text))
        if len(plain_html) < 0.80 * len(plain_md):
            raise RuntimeError("HTML body appears too short relative to the full report.")

        for heading in REQUIRED_SECTION_HEADINGS:
            plain_heading = heading_text_from_md_heading(heading)
            if plain_heading not in plain_html:
                raise RuntimeError(f"HTML body is missing required section heading text: {plain_heading}")


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


# ---------- EQUITY CURVE ----------
def create_equity_curve_png(output_dir: Path, chart_path: Path):
    points = []
    for report_path in latest_reports_by_day(output_dir):
        md_text = report_path.read_text(encoding="utf-8")
        report_date = parse_report_date(md_text)
        totals = parse_section15_totals(md_text)
        nav = totals.get("Total portfolio value (EUR)")
        if nav is not None:
            points.append((report_date, nav))

    if not points:
        return None

    dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in points]
    values = [v for _, v in points]

    plt.figure(figsize=(8.8, 3.7))
    plt.plot(dates, values, marker="o", linewidth=2.2)
    plt.title("Equity Curve (EUR)")
    plt.xlabel("Date")
    plt.ylabel("Portfolio value (EUR)")
    plt.grid(True, alpha=0.28)
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180)
    plt.close()
    return chart_path


# ---------- MARKDOWN -> BRANDED HTML ----------
def preprocess_markdown_block(text: str, image_src: str | None = None) -> str:
    lines = text.splitlines()
    processed = []

    for line in lines:
        stripped = clean_md_inline(line.strip())
        if stripped == "EQUITY_CURVE_CHART_PLACEHOLDER":
            if image_src:
                processed.append(f"![Equity curve]({image_src})")
            else:
                processed.append("_Equity curve chart unavailable for this delivery._")
            continue

        is_heading = line.lstrip().startswith("#")
        is_bullet = line.lstrip().startswith("- ") or bool(re.match(r"^\d+\.\s+", line.lstrip()))
        is_table = is_markdown_table_line(line)

        if stripped in PLAIN_SUBHEADERS and not is_heading and not is_bullet and not is_table:
            processed.append(f"#### {stripped}")
        else:
            processed.append(line)

    return "\n".join(processed)


def render_markdown_block(text: str, image_src: str | None = None) -> str:
    md = preprocess_markdown_block(strip_citations(text), image_src=image_src)
    return MARKDOWN(md)


def chip_html(text: str, bg: str, fg: str) -> str:
    return f"<span class='chip' style='background:{bg};color:{fg};'>{esc(text)}</span>"


def action_tone(header: str):
    label = clean_md_inline(header).lower()
    if "add" in label:
        return BRAND["add_bg"], BRAND["add_tx"]
    if "hold but replaceable" in label:
        return BRAND["replace_bg"], BRAND["replace_tx"]
    if "hold" in label:
        return BRAND["hold_bg"], BRAND["hold_tx"]
    if "reduce" in label:
        return BRAND["reduce_bg"], BRAND["reduce_tx"]
    if "close" in label:
        return BRAND["close_bg"], BRAND["close_tx"]
    return BRAND["champagne_soft"], BRAND["ink"]


def section_header_html(number: int, title: str) -> str:
    return (
        f"<div class='section-kicker'>"
        f"<span class='section-badge'>{number}</span>"
        f"<span class='section-label'>{esc(title)}</span>"
        f"</div>"
    )


def render_executive_summary(section: dict) -> str:
    pairs = extract_label_pairs(section["lines"])
    if not pairs:
        body = render_markdown_block("\n".join(section["lines"]))
        return f"<div class='panel panel-exec'>{section_header_html(section['number'], section['title'])}{body}</div>"

    pair_map = OrderedDict(pairs)
    chips = []
    for key in ["Primary regime", "Secondary cross-current", "Geopolitical regime"]:
        value = pair_map.get(key)
        if value:
            chips.append(chip_html(f"{key}: {value}", BRAND["champagne_soft"], BRAND["ink"]))

    body_parts = []
    for key, value in pairs:
        if key in {"Primary regime", "Secondary cross-current", "Geopolitical regime"}:
            continue
        if key.lower() == "main takeaway":
            body_parts.append(
                f"<div class='takeaway'><div class='takeaway-label'>{esc(key)}</div><div class='takeaway-text'>{esc(value)}</div></div>"
            )
        else:
            body_parts.append(
                f"<div class='summary-line'><div class='summary-key'>{esc(key)}</div><div class='summary-value'>{esc(value)}</div></div>"
            )

    return (
        f"<div class='panel panel-exec'>"
        f"{section_header_html(section['number'], section['title'])}"
        f"<h2 class='panel-title'>A premium first page should answer three questions in seconds.</h2>"
        f"<div class='chip-row'>{''.join(chips)}</div>"
        f"{''.join(body_parts)}"
        f"</div>"
    )


def render_action_snapshot(section: dict) -> str:
    groups = []
    current_header = None
    current_items = []

    def flush():
        nonlocal current_header, current_items
        if not current_header:
            return
        bg, fg = action_tone(current_header)
        items_html = "".join(f"<li>{esc(item)}</li>" for item in current_items) or "<li>No change</li>"
        groups.append(
            f"<div class='snapshot-group'>"
            f"{chip_html(current_header, bg, fg)}"
            f"<ul>{items_html}</ul>"
            f"</div>"
        )

    for line in section["lines"]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            flush()
            current_header = clean_md_inline(stripped[4:])
            current_items = []
        elif stripped.startswith("- "):
            current_items.append(stripped[2:])
        elif re.match(r"^\d+\.\s+", stripped):
            current_items.append(re.sub(r"^\d+\.\s+", "", stripped))
        else:
            if current_header and clean_md_inline(stripped):
                current_items.append(clean_md_inline(stripped))
    flush()

    return (
        f"<div class='panel panel-snapshot'>"
        f"{section_header_html(section['number'], section['title'])}"
        f"<h2 class='panel-title'>Suggested visual treatment</h2>"
        f"{''.join(groups)}"
        f"</div>"
    )


def render_risks(section: dict) -> str:
    body = render_markdown_block("\n".join(section["lines"]))
    return (
        f"<div class='panel panel-risks'>"
        f"{section_header_html(section['number'], section['title'])}"
        f"<h2 class='panel-title'>Risk block should read like a premium alert</h2>"
        f"{body}"
        f"</div>"
    )


def render_standard_panel(section: dict, image_src: str | None = None, extra_class: str = "") -> str:
    body = render_markdown_block("\n".join(section["lines"]), image_src=image_src)
    return (
        f"<div class='panel {extra_class}'>"
        f"{section_header_html(section['number'], section['title'])}"
        f"<h2 class='panel-title'>{esc(section['title'])}</h2>"
        f"{body}"
        f"</div>"
    )



def build_report_html(
    md_text: str,
    report_date_str: str,
    image_src: str | None = None,
    render_mode: str = "email",
) -> str:
    report_title, sections = extract_sections(md_text)
    sections_by_number = {s["number"]: s for s in sections}

    exec_pairs = OrderedDict(extract_label_pairs(sections_by_number.get(1, {}).get("lines", [])))
    primary_regime = exec_pairs.get("Primary regime", "Pending classification")
    geo_regime = exec_pairs.get("Geopolitical regime", "Pending classification")
    main_takeaway = exec_pairs.get("Main takeaway", "Keep the current allocation disciplined.")

    intro_cards = (
        f"<div class='mini-card'><div class='mini-label'>Primary regime</div><div class='mini-value'>{esc(primary_regime)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Geopolitical regime</div><div class='mini-value'>{esc(geo_regime)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Main takeaway</div><div class='mini-value'>{esc(main_takeaway)}</div></div>"
    )

    client_grid = []
    if 1 in sections_by_number:
        client_grid.append(render_executive_summary(sections_by_number[1]))
    if 2 in sections_by_number:
        client_grid.append(render_action_snapshot(sections_by_number[2]))
    if 5 in sections_by_number:
        client_grid.append(render_risks(sections_by_number[5]))

    client_panels = []
    for number in [6, 3, 4, 7]:
        if number in sections_by_number:
            img_src = image_src if number == 7 else None
            extra = "panel-compact" if number == 6 else ""
            client_panels.append(render_standard_panel(sections_by_number[number], image_src=img_src, extra_class=extra))

    analyst_panels = []
    for number in range(8, 18):
        if number in sections_by_number:
            analyst_panels.append(render_standard_panel(sections_by_number[number]))

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
      max-width: 1480px;
      margin: 0 auto;
      padding: 0 0 18px 0;
    }}
    .hero {{
      background: {BRAND['header']};
      color: {BRAND['header_text']};
      padding: 24px 28px 20px 28px;
      border-radius: 14px 14px 0 0;
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-start;
    }}
    .masthead {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      font-size: 28px;
      letter-spacing: 1px;
      margin: 0 0 8px 0;
      text-transform: uppercase;
    }}
    .hero-sub {{
      font-size: 14px;
      color: #EFF4F6;
      margin: 0;
    }}
    .hero-meta {{
      min-width: 220px;
      text-align: right;
    }}
    .hero-date {{
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px 0;
    }}
    .hero-edition {{
      font-size: 13px;
      margin: 0 0 10px 0;
      color: #EFF4F6;
    }}
    .hero-rule {{
      height: 6px;
      background: {BRAND['champagne']};
      margin: 8px 0 18px 0;
      border-radius: 999px;
    }}
    .notice {{
      background: #F2F0EB;
      border: 1px solid {BRAND['border']};
      color: {BRAND['muted']};
      border-radius: 16px;
      padding: 14px 18px;
      font-size: 14px;
      margin: 0 0 18px 0;
    }}
    .summary-strip {{
      display: flex;
      gap: 16px;
      margin: 0 0 18px 0;
    }}
    .mini-card {{
      flex: 1 1 0;
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 18px;
      padding: 14px 18px;
    }}
    .mini-label {{
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .04em;
      text-transform: uppercase;
      color: {BRAND['muted']};
      margin: 0 0 8px 0;
    }}
    .mini-value {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      font-size: 22px;
      color: {BRAND['ink']};
      line-height: 1.18;
    }}
    .client-grid {{
      display: grid;
      grid-template-columns: 1.7fr 1fr;
      gap: 18px;
      align-items: start;
      margin: 0 0 18px 0;
    }}
    .panel {{
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 18px;
      padding: 20px 22px;
      margin: 0 0 18px 0;
    }}
    .panel-compact,
    .panel-exec,
    .panel-snapshot,
    .panel-risks {{
      page-break-inside: avoid;
      break-inside: avoid-page;
    }}
    .panel-exec {{
      grid-row: span 2;
      min-height: 100%;
    }}
    .panel-title {{
      margin: 0 0 14px 0;
      color: {BRAND['ink']};
      font-size: 20px;
      line-height: 1.25;
      font-weight: 700;
    }}
    .section-kicker {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0 0 14px 0;
    }}
    .section-badge {{
      width: 34px;
      height: 34px;
      line-height: 34px;
      text-align: center;
      border-radius: 999px;
      background: #2A5384;
      color: #ffffff;
      font-weight: 700;
      font-size: 15px;
      flex: 0 0 auto;
    }}
    .section-label {{
      font-size: 13px;
      font-weight: 700;
      letter-spacing: .04em;
      text-transform: uppercase;
      color: {BRAND['muted']};
    }}
    .chip-row {{
      margin: 0 0 14px 0;
    }}
    .chip {{
      display: inline-block;
      padding: 7px 14px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      margin: 0 8px 8px 0;
    }}
    .summary-line {{
      margin: 0 0 12px 0;
      padding: 0 0 12px 0;
      border-bottom: 1px solid {BRAND['border']};
    }}
    .summary-key {{
      color: {BRAND['muted']};
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin: 0 0 6px 0;
    }}
    .summary-value {{
      color: {BRAND['ink']};
      font-size: 15px;
      line-height: 1.52;
    }}
    .takeaway {{
      margin: 18px 0 0 0;
      padding: 14px 16px;
      border-radius: 14px;
      background: #F1EADF;
      border: 1px solid #E6D8C0;
    }}
    .takeaway-label {{
      color: {BRAND['muted']};
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin: 0 0 6px 0;
    }}
    .takeaway-text {{
      color: {BRAND['ink']};
      font-size: 17px;
      font-weight: 700;
      line-height: 1.4;
    }}
    .snapshot-group {{
      margin: 0 0 14px 0;
    }}
    .snapshot-group ul {{
      margin: 10px 0 0 22px;
      padding: 0;
    }}
    .snapshot-group li {{
      margin: 0 0 6px 0;
      line-height: 1.45;
      font-size: 14px;
    }}
    .panel p, .panel li {{
      font-size: 14px;
      line-height: 1.55;
      margin-top: 0;
    }}
    .panel ul, .panel ol {{
      margin-top: 0;
      padding-left: 22px;
    }}
    .panel h3 {{
      color: {BRAND['ink']};
      font-size: 15px;
      margin: 16px 0 8px 0;
    }}
    .panel h4 {{
      color: {BRAND['muted']};
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin: 16px 0 8px 0;
    }}
    .panel blockquote {{
      margin: 12px 0;
      padding: 10px 12px;
      border-left: 4px solid {BRAND['champagne']};
      background: #F4F0E8;
      color: {BRAND['muted']};
    }}
    .panel table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      margin: 14px 0 12px 0;
      border: 1px solid {BRAND['border']};
      font-size: 12px;
    }}
    .panel thead {{
      display: table-header-group;
    }}
    .panel tbody {{
      display: table-row-group;
    }}
    .panel th {{
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid {BRAND['border']};
      background: #F2EBDD;
      color: {BRAND['ink']};
      vertical-align: middle;
    }}
    .panel td {{
      padding: 8px 10px;
      border-bottom: 1px solid #ECE6DE;
      vertical-align: top;
      word-wrap: break-word;
    }}
    .panel tr {{
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    .panel tr:nth-child(even) td {{
      background: #FEFCF9;
    }}
    .panel img {{
      max-width: 100%;
      height: auto;
      border: 1px solid {BRAND['border']};
      border-radius: 10px;
      margin: 10px 0 4px 0;
      display: block;
    }}
    .analyst-divider {{
      margin: 8px 0 18px 0;
      padding: 10px 0 0 0;
      border-top: 1px solid {BRAND['border']};
      color: {BRAND['muted']};
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    a {{
      color: #315F8B;
      text-decoration: underline;
    }}
    """

    email_css = """
    .report-stack {
      margin-top: 0;
    }
    @media screen and (max-width: 1100px) {
      .hero, .summary-strip, .client-grid {
        display: block;
      }
      .hero-meta {
        text-align: left;
        margin-top: 16px;
      }
      .mini-card, .panel {
        margin-bottom: 16px;
      }
      .panel-exec {
        min-height: auto;
      }
    }
    """

    pdf_css = f"""
    @page {{
      size: A4 landscape;
      margin: 12mm;
    }}
    body {{
      background: #ffffff;
    }}
    .report-shell {{
      max-width: none;
      padding-bottom: 0;
    }}
    .hero,
    .notice,
    .summary-strip,
    .panel-compact,
    .panel-exec,
    .panel-snapshot,
    .panel-risks,
    .mini-card {{
      page-break-inside: avoid;
      break-inside: avoid-page;
    }}
    .hero {{
      border-radius: 10px 10px 0 0;
      padding: 20px 22px 16px 22px;
    }}
    .hero-meta {{
      min-width: 180px;
    }}
    .summary-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .client-grid {{
      display: block;
      margin-bottom: 8px;
    }}
    .panel {{
      page-break-inside: auto;
      break-inside: auto;
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 14px;
    }}
    .panel-exec {{
      min-height: auto;
      grid-row: auto;
    }}
    .panel table {{
      table-layout: auto;
      font-size: 11px;
    }}
    .panel th, .panel td {{
      padding: 6px 8px;
    }}
    .panel img {{
      max-height: 170mm;
      object-fit: contain;
    }}
    .analyst-divider {{
      page-break-before: always;
      break-before: page;
      margin-top: 4px;
    }}
    """

    pdf_fallback_css = """
    @page {
      size: A4 landscape;
      margin: 12mm;
    }
    body {
      background: #ffffff;
      color: #222222;
      font-family: Arial, Helvetica, sans-serif;
    }
    .report-shell {
      max-width: none;
    }
    .hero,
    .summary-strip,
    .client-grid {
      display: block;
    }
    .hero {
      padding: 16px 18px;
      border-radius: 6px 6px 0 0;
    }
    .hero-meta {
      text-align: left;
      margin-top: 12px;
      min-width: 0;
    }
    .hero-rule {
      margin-bottom: 12px;
    }
    .summary-strip .mini-card {
      margin-bottom: 10px;
    }
    .panel {
      page-break-inside: auto;
      break-inside: auto;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 12px;
    }
    .panel-exec {
      min-height: auto;
      grid-row: auto;
    }
    .panel table {
      table-layout: auto;
      font-size: 10.5px;
    }
    .panel th, .panel td {
      padding: 5px 7px;
    }
    .analyst-divider {
      page-break-before: always;
      break-before: page;
      margin-top: 6px;
    }
    """

    mode_css = email_css
    if render_mode == "pdf":
        mode_css = pdf_css
    elif render_mode == "pdf_fallback":
        mode_css = pdf_fallback_css

    analyst_appendix = ""
    if analyst_panels:
        analyst_appendix = (
            "<div class='analyst-divider'>Analyst appendix</div>"
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
            <div>
              <div class="masthead">WEEKLY ETF REVIEW</div>
              <p class="hero-sub">{esc(report_title or f"Weekly Report Review {report_date_str}")}</p>
            </div>
            <div class="hero-meta">
              <div class="hero-date">{esc(report_date_str)}</div>
              <div class="hero-edition">Weekly Allocation Review</div>
              <div class="hero-edition">Client edition</div>
            </div>
          </div>
          <div class="hero-rule"></div>
          <div class="notice">{esc(DISCLAIMER_LINE)}</div>
          <div class="summary-strip">{intro_cards}</div>
          <div class="client-grid">{''.join(client_grid)}</div>
          <div class="report-stack">{''.join(client_panels)}{analyst_appendix}</div>
        </div>
      </body>
    </html>
    """
    return html.strip()


def create_pdf_from_html(html: str, output_path: Path, fallback_html: str | None = None) -> None:
    try:
        HTML(string=html, base_url=str(output_path.parent)).write_pdf(str(output_path))
    except AssertionError:
        if not fallback_html:
            raise
        HTML(string=fallback_html, base_url=str(output_path.parent)).write_pdf(str(output_path))


# ---------- DELIVERY ASSETS ----------
def generate_delivery_assets(output_dir: Path, report_path: Path):
    original_md_text = report_path.read_text(encoding="utf-8")
    md_text_clean = strip_citations(original_md_text)
    validate_required_report(md_text_clean)

    report_date_str = parse_report_date(md_text_clean)
    safe_stem = report_path.stem

    clean_md_path = report_path.with_name(f"{safe_stem}_clean.md")
    clean_md_path.write_text(md_text_clean, encoding="utf-8")

    equity_curve_png = report_path.with_name(f"{safe_stem}_equity_curve.png")
    create_equity_curve_png(output_dir, equity_curve_png)

    image_src_pdf = equity_curve_png.resolve().as_uri() if equity_curve_png.exists() else None
    image_src_email = "cid:equitycurve" if equity_curve_png.exists() else None

    html_email = build_report_html(md_text_clean, report_date_str, image_src=image_src_email, render_mode="email")
    html_pdf = build_report_html(md_text_clean, report_date_str, image_src=image_src_pdf, render_mode="pdf")
    html_pdf_fallback = build_report_html(md_text_clean, report_date_str, image_src=image_src_pdf, render_mode="pdf_fallback")

    validate_email_body(html_email, md_text_clean)

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
    }


# ---------- EMAIL ----------
def send_email_with_attachments(assets: dict) -> tuple[list[str], Path, str]:
    subject = f"Weekly Report Review {assets['report_date_str']}"

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

    if assets["equity_curve_png"].exists():
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

    with open(assets["pdf_path"], "rb") as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
        pdf_attachment.add_header("Content-Disposition", "attachment", filename=assets["pdf_path"].name)
        root.attach(pdf_attachment)

    with open(assets["clean_md_path"], "rb") as f:
        md_attachment = MIMEApplication(f.read(), _subtype="markdown")
        md_attachment.add_header("Content-Disposition", "attachment", filename=assets["clean_md_path"].name)
        root.attach(md_attachment)

    with open(assets["html_path"], "rb") as f:
        html_attachment = MIMEApplication(f.read(), _subtype="html")
        html_attachment.add_header("Content-Disposition", "attachment", filename=assets["html_path"].name)
        root.attach(html_attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], root.as_string())

    manifest_path = assets["pdf_path"].with_name(f"{assets['safe_stem']}_delivery_manifest.txt")
    write_delivery_manifest(manifest_path, assets["pdf_path"].name.replace(".pdf", ".md"), mail_to, attachments)
    return attachments, manifest_path, mail_to


# ---------- MAIN ----------
def main():
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

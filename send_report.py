
import os
import re
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


def esc(text: str) -> str:
    text = clean_md_inline(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def plain_text_from_markdown(md_text: str) -> str:
    text = strip_citations(md_text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = text.replace('**', '').replace('`', '')
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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


def build_delivery_html(md_text: str, report_date_str: str, image_src: str | None = None, mode: str = "email") -> str:
    report_title, sections = extract_sections(md_text)
    sections_by_number = {s["number"]: s for s in sections}
    exec_pairs = OrderedDict(extract_label_pairs(sections_by_number.get(1, {}).get("lines", [])))

    primary_regime = exec_pairs.get("Primary regime", "Pending classification")
    geo_regime = exec_pairs.get("Geopolitical regime", "Pending classification")
    main_takeaway = exec_pairs.get("Main takeaway", "Pending conclusion")

    intro_cards = (
        f"<div class='mini-card'><div class='mini-label'>Primary regime</div><div class='mini-value'>{esc(primary_regime)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Geopolitical regime</div><div class='mini-value'>{esc(geo_regime)}</div></div>"
        f"<div class='mini-card mini-card-highlight'><div class='mini-label'>Main takeaway</div><div class='mini-value'>{esc(main_takeaway)}</div></div>"
    )

    def maybe_render(number: int, image: str | None = None, extra_class: str = "") -> str:
        section = sections_by_number.get(number)
        if not section:
            return ""
        if number == 1:
            return render_executive_summary(section)
        if number == 2:
            return render_action_snapshot(section)
        if number == 5:
            return render_risks(section)
        return render_standard_panel(section, image_src=image, extra_class=extra_class)

    executive_summary_panel = maybe_render(1)
    action_snapshot_panel = maybe_render(2)
    bottom_line_panel = maybe_render(6, extra_class="panel-bottomline")
    risks_panel = maybe_render(5)
    regime_panel = maybe_render(3)
    radar_panel = maybe_render(4)
    equity_panel = maybe_render(7, image=image_src)

    appendix_order = list(range(8, 18))
    appendix_panels = []
    for number in appendix_order:
        panel_html = maybe_render(number)
        if panel_html:
            appendix_panels.append(panel_html)

    shell_width = "1120px" if mode == "email" else "1480px"
    hero_pad = "30px 32px 24px 32px" if mode == "email" else "26px 30px 22px 30px"
    page_css = "@page { size: A4 landscape; margin: 14mm; }" if mode == "pdf" else ""

    css = f"""
    {page_css}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: {BRAND['paper']};
      color: {BRAND['ink']};
      font-family: Arial, Helvetica, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .report-shell {{
      max-width: {shell_width};
      margin: 0 auto;
      padding: 14px;
    }}
    .hero {{
      background: {BRAND['header']};
      color: {BRAND['header_text']};
      padding: {hero_pad};
      border-radius: 18px 18px 0 0;
      display: flex;
      justify-content: space-between;
      gap: 28px;
      align-items: flex-start;
    }}
    .masthead {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      font-size: 32px;
      letter-spacing: 1.25px;
      margin: 0 0 10px 0;
      text-transform: uppercase;
      line-height: 1.05;
    }}
    .hero-sub {{
      font-size: 15px;
      color: #F2F6F7;
      margin: 0;
      max-width: 760px;
      line-height: 1.45;
    }}
    .hero-meta {{
      min-width: 220px;
      text-align: right;
      padding-top: 4px;
    }}
    .hero-date {{
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 8px 0;
      line-height: 1.1;
    }}
    .hero-edition {{
      font-size: 13px;
      margin: 0 0 8px 0;
      color: #EEF4F6;
      line-height: 1.45;
    }}
    .hero-rule {{
      height: 6px;
      background: {BRAND['champagne']};
      margin: 8px 0 20px 0;
      border-radius: 999px;
    }}
    .notice {{
      background: #F2F0EB;
      border: 1px solid {BRAND['border']};
      color: {BRAND['muted']};
      border-radius: 16px;
      padding: 14px 18px;
      font-size: 14px;
      line-height: 1.45;
      margin: 0 0 18px 0;
    }}
    .summary-strip {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin: 0 0 18px 0;
    }}
    .mini-card {{
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 18px;
      padding: 16px 18px;
      min-height: 112px;
    }}
    .mini-card-highlight {{
      background: #F4EDE1;
      border-color: #E6D7BC;
    }}
    .mini-label {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: {BRAND['muted']};
      margin: 0 0 10px 0;
    }}
    .mini-value {{
      font-family: Georgia, "Times New Roman", serif;
      font-weight: 700;
      font-size: 24px;
      color: {BRAND['ink']};
      line-height: 1.18;
    }}
    .exec-grid, .decision-grid, .context-grid {{
      display: grid;
      gap: 18px;
      margin: 0 0 18px 0;
      align-items: start;
    }}
    .exec-grid {{ grid-template-columns: 1.45fr 1fr; }}
    .decision-grid {{ grid-template-columns: 1fr 1fr; }}
    .context-grid {{ grid-template-columns: 1fr 1fr; }}
    .panel {{
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 20px;
      padding: 24px;
      margin: 0 0 18px 0;
      page-break-inside: avoid;
      break-inside: avoid-page;
    }}
    .panel-title {{
      margin: 0 0 14px 0;
      color: {BRAND['ink']};
      font-size: 21px;
      line-height: 1.24;
      font-weight: 700;
    }}
    .section-kicker {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0 0 14px 0;
    }}
    .section-badge {{
      width: 32px;
      height: 32px;
      line-height: 32px;
      text-align: center;
      border-radius: 999px;
      background: #2A5384;
      color: #ffffff;
      font-weight: 700;
      font-size: 14px;
      flex: 0 0 auto;
    }}
    .section-label {{
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: {BRAND['muted']};
    }}
    .chip-row {{ margin: 0 0 14px 0; }}
    .chip {{
      display: inline-block;
      padding: 7px 12px;
      border-radius: 10px;
      border: 1px solid rgba(43,55,66,.10);
      font-size: 12px;
      font-weight: 700;
      margin: 0 8px 8px 0;
      line-height: 1.15;
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
      font-size: 15px;
      line-height: 1.58;
    }}
    .takeaway {{
      margin: 18px 0 0 0;
      padding: 16px 18px;
      border-radius: 14px;
      background: #F1EADF;
      border: 1px solid #E6D8C0;
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
      font-size: 18px;
      font-weight: 700;
      line-height: 1.38;
    }}
    .snapshot-group {{ margin: 0 0 16px 0; }}
    .snapshot-group ul {{ margin: 10px 0 0 20px; padding: 0; }}
    .snapshot-group li {{ margin: 0 0 6px 0; line-height: 1.45; font-size: 14px; }}
    .panel p, .panel li {{ font-size: 14px; line-height: 1.58; margin-top: 0; }}
    .panel ul, .panel ol {{ margin-top: 0; padding-left: 22px; }}
    .panel h3 {{ color: {BRAND['ink']}; font-size: 15px; margin: 16px 0 8px 0; }}
    .panel h4 {{ color: {BRAND['muted']}; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; margin: 16px 0 8px 0; }}
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
      table-layout: auto;
      margin: 14px 0 12px 0;
      border: 1px solid {BRAND['border']};
      font-size: 12px;
    }}
    .panel th {{
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid {BRAND['border']};
      background: #F2EBDD;
      color: {BRAND['ink']};
      vertical-align: middle;
      line-height: 1.35;
    }}
    .panel td {{
      padding: 9px 10px;
      border-bottom: 1px solid #ECE6DE;
      vertical-align: top;
      overflow-wrap: anywhere;
      line-height: 1.42;
    }}
    .panel tr:nth-child(even) td {{ background: #FEFCF9; }}
    .panel img {{
      max-width: 100%;
      height: auto;
      border: 1px solid {BRAND['border']};
      border-radius: 10px;
      margin: 10px 0 4px 0;
      display: block;
    }}
    .appendix-wrap {{ margin-top: 12px; }}
    .appendix-head {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 27px;
      font-weight: 700;
      color: {BRAND['ink']};
      margin: 0 0 8px 0;
    }}
    .appendix-intro {{
      color: {BRAND['muted']};
      font-size: 14px;
      line-height: 1.55;
      margin: 0 0 18px 0;
    }}
    .appendix-stack {{ margin-top: 0; }}
    a {{ color: #315F8B; text-decoration: underline; }}
    @media screen and (max-width: 1100px) {{
      .hero {{ display: block; }}
      .hero-meta {{ text-align: left; margin-top: 18px; }}
      .summary-strip, .exec-grid, .decision-grid, .context-grid {{ display: block; }}
      .mini-card, .panel {{ margin-bottom: 16px; }}
    }}
    """

    executive_blocks = []
    if executive_summary_panel or action_snapshot_panel:
        executive_blocks.append(f"<div class='exec-grid'>{executive_summary_panel}{action_snapshot_panel}</div>")
    if bottom_line_panel or risks_panel:
        executive_blocks.append(f"<div class='decision-grid'>{bottom_line_panel}{risks_panel}</div>")
    if regime_panel or radar_panel:
        executive_blocks.append(f"<div class='context-grid'>{regime_panel}{radar_panel}</div>")
    if equity_panel:
        executive_blocks.append(equity_panel)

    appendix_html = ""
    if appendix_panels:
        appendix_html = (
            "<div class='appendix-wrap'>"
            "<div class='appendix-head'>Analyst appendix</div>"
            "<div class='appendix-intro'>The sections below preserve the full analytical record, but the executive reading experience above should stand on its own.</div>"
            f"<div class='appendix-stack'>{''.join(appendix_panels)}</div>"
            "</div>"
        )

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>{css}</style>
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
            </div>
          </div>
          <div class="hero-rule"></div>
          <div class="notice">{esc(DISCLAIMER_LINE)}</div>
          <div class="summary-strip">{intro_cards}</div>
          {''.join(executive_blocks)}
          {appendix_html}
        </div>
      </body>
    </html>
    """
    return html.strip()


def create_pdf_from_html(html: str, output_path: Path) -> None:
    HTML(string=html, base_url=str(output_path.parent)).write_pdf(str(output_path))


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

    html_email = build_delivery_html(md_text_clean, report_date_str, image_src=image_src_email, mode="email")
    html_pdf = build_delivery_html(md_text_clean, report_date_str, image_src=image_src_pdf, mode="pdf")

    validate_email_body(html_email, md_text_clean)

    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_pdf, encoding="utf-8")

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

    if assets["equity_curve_png"].exists():
        png_bytes = assets["equity_curve_png"].read_bytes()
        inline_png = MIMEImage(png_bytes, _subtype="png")
        inline_png.add_header("Content-ID", "<equitycurve>")
        inline_png.add_header("Content-Disposition", "inline", filename=assets["equity_curve_png"].name)
        related.attach(inline_png)

    root.attach(related)

    attachments = [assets["pdf_path"].name]
    with open(assets["pdf_path"], "rb") as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
        pdf_attachment.add_header("Content-Disposition", "attachment", filename=assets["pdf_path"].name)
        root.attach(pdf_attachment)

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

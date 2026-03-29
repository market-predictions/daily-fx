#!/usr/bin/env python3
"""
send_fxreport.py

Self-contained FX delivery/rendering script.

Responsibilities:
- discover latest Weekly FX Review markdown in output/
- validate minimum report structure and freshness against live state files
- render premium HTML email + PDF
- keep links underlined but not bold
- embed the equity chart in email as CID inline image
- send HTML body + PDF/HTML/MD attachments
- write a delivery manifest

This restores the legacy module contract expected by the split-delivery workflow:
- latest_report_file(output_dir)
- generate_delivery_assets(output_dir, report_path)
"""

from __future__ import annotations

import argparse
import csv
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

import json
import markdown as mdlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weasyprint import HTML


TITLE = "Weekly FX Review"
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

SECTION16_SENTENCE = (
    "**This section is the canonical default input for the next run unless the user explicitly overrides it.**"
)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable missing: {name}")
    return value


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
    return text.strip()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


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


def validate_required_report(md_text: str) -> None:
    for heading in REQUIRED_SECTION_HEADINGS:
        if heading not in md_text:
            raise RuntimeError(f"Report is missing mandatory section heading: {heading}")
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


def plain_text_from_markdown(md_text: str) -> str:
    html = mdlib.markdown(strip_citations(md_text), extensions=["tables"])
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


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

    plt.figure(figsize=(8.8, 3.6))
    plt.plot(dates, navs, marker="o", linewidth=2.0)
    plt.title("Model portfolio development")
    plt.xlabel("Date")
    plt.ylabel("Portfolio value (USD)")
    plt.grid(True, alpha=0.28)
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180)
    plt.close()
    return chart_path if chart_path.exists() else None


def inject_chart_block(md_text: str, image_src: Optional[str]) -> str:
    if not image_src:
        fallback = (
            "\n<div class=\"chart-wrap\"><div class=\"chart-label\">Model portfolio development</div>"
            "<div class=\"chart-missing\">Chart unavailable for this delivery.</div></div>\n"
        )
        return re.sub(r"(^##\s+7\.\s+.*$)", r"\1" + fallback, md_text, count=1, flags=re.MULTILINE)

    image_block = (
        "\n<div class=\"chart-wrap\">"
        "<div class=\"chart-label\">Model portfolio development</div>"
        f"<img src=\"{image_src}\" alt=\"Model portfolio development chart\">"
        "</div>\n"
    )
    return re.sub(r"(^##\s+7\.\s+.*$)", r"\1" + image_block, md_text, count=1, flags=re.MULTILINE)


def build_report_html(
    md_text: str,
    report_date_str: str,
    output_dir: Optional[Path] = None,
    render_mode: str = "email",
    image_src: Optional[str] = None,
) -> str:
    display_date = format_full_date(report_date_str)
    body_md = strip_citations(md_text)
    body_md = inject_chart_block(body_md, image_src=image_src)
    body_html = mdlib.markdown(body_md, extensions=["tables", "sane_lists"])

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
      max-width: 1080px;
      margin: 0 auto;
      padding: 0 0 20px 0;
    }}
    .hero {{
      background: {BRAND['header']};
      color: {BRAND['header_text']};
      padding: 22px 24px 18px 24px;
      border-radius: 14px 14px 0 0;
    }}
    .hero-table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .hero-table td {{
      vertical-align: middle;
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
    .panel {{
      background: {BRAND['surface']};
      border: 1px solid {BRAND['border']};
      border-radius: 18px;
      padding: 18px 20px;
    }}
    .panel h1 {{
      display: none;
    }}
    .panel h2 {{
      color: {BRAND['muted']};
      font-size: 15px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      margin: 24px 0 12px 0;
      line-height: 1.15;
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
    .panel p, .panel li {{
      font-size: 14px;
      line-height: 1.58;
      margin-top: 0;
    }}
    .panel ul, .panel ol {{
      margin-top: 0;
      padding-left: 22px;
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
      border-radius: 12px;
      background: #fff;
      display: block;
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

    if render_mode == "pdf":
        mode_css = """
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
        .panel, .chart-wrap {
          page-break-inside: avoid;
          break-inside: avoid-page;
        }
        """
    else:
        mode_css = """
        @media screen and (max-width: 980px) {
          .hero-table, .hero-table tbody, .hero-table tr, .hero-table td {
            display: block;
            width: 100%;
          }
          .hero-right {
            text-align: left;
            padding-left: 0;
            padding-top: 10px;
          }
          .panel table {
            table-layout: auto;
          }
        }
        """

    return f"""
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <style>{css_common}{mode_css}</style>
      </head>
      <body>
        <div class=\"report-shell\">
          <div class=\"hero\">
            <table class=\"hero-table\" role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\">
              <tr>
                <td>
                  <div class=\"masthead\">WEEKLY FX REVIEW</div>
                  <p class=\"hero-sub\">{display_date}</p>
                </td>
                <td class=\"hero-right\">
                  <div class=\"hero-side-label\">Investor Report</div>
                </td>
              </tr>
            </table>
          </div>
          <div class=\"hero-rule\"></div>
          <div class=\"notice\">This report is for informational and educational purposes only; please see the disclaimer at the end.</div>
          <div class=\"panel\">
            {body_html}
          </div>
        </div>
      </body>
    </html>
    """.strip()


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
    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    html_pdf = build_report_html(
        md_text_clean,
        report_date_str,
        output_dir=output_dir,
        render_mode="pdf",
        image_src=chart_path.resolve().as_uri() if chart_exists else None,
    )
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

#!/usr/bin/env python3
"""
send_fxreport_v2.py

Incremental delivery-layer patch over send_fxreport.py.

What changes versus send_fxreport.py:
- keeps TradingView links non-bold in the rendered email/PDF HTML
- replaces the email-mode embedded base64 equity chart with a CID inline image
  for better email-client compatibility
- keeps PDF rendering on the original data-URI path
- preserves the existing report discovery, freshness guard, validation,
  attachment handling, and manifest flow from send_fxreport.py
"""

from __future__ import annotations

import argparse
import base64
import re
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import send_fxreport as base


CHART_DATA_URI_RE = re.compile(r"""src=['"]data:image/png;base64,([^'"]+)['"]""", re.IGNORECASE)

LINK_CSS_NEEDLE = """    a {{
      color: #315F8B;
      text-decoration: underline;
    }}"""

LINK_CSS_PATCH = """    a {{
      color: #315F8B;
      text-decoration: underline;
    }}
    a.tv-link, a.tv-link:visited {{
      font-weight: 400;
    }}
    strong a.tv-link, strong a.tv-link:visited,
    b a.tv-link, b a.tv-link:visited {{
      font-weight: 400;
    }}"""


def patch_email_html(html_email: str) -> tuple[str, bytes]:
    """
    Convert the first embedded base64 chart image in the email HTML into a CID
    reference and return the extracted PNG bytes for inline attachment.
    Also ensures TradingView links do not inherit bold styling.
    """
    match = CHART_DATA_URI_RE.search(html_email)
    if not match:
        raise RuntimeError(
            "Could not find embedded chart data URI in the email HTML. "
            "Refusing to build send_fxreport_v2 assets."
        )

    try:
        chart_png_bytes = base64.b64decode(match.group(1))
    except Exception as exc:
        raise RuntimeError("Failed to decode embedded equity chart image data.") from exc

    html_email = CHART_DATA_URI_RE.sub("src='cid:fx_equity_chart'", html_email, count=1)

    if "a.tv-link" not in html_email and LINK_CSS_NEEDLE in html_email:
        html_email = html_email.replace(LINK_CSS_NEEDLE, LINK_CSS_PATCH, 1)

    return html_email, chart_png_bytes


def generate_delivery_assets(output_dir: Path, report_path: Path) -> dict:
    """
    Reuses the same validation/freshness flow as send_fxreport.py, but patches the
    email HTML so the chart is sent as CID inline image.
    """
    original_md_text = base.normalize_whitespace(report_path.read_text(encoding="utf-8"))
    md_text_clean = base.strip_citations(original_md_text)
    base.validate_required_report(md_text_clean)

    portfolio_state = base.load_json(output_dir / "fx_portfolio_state.json")
    base.validate_report_freshness(md_text_clean, portfolio_state)

    report_date_str = base.parse_report_date(md_text_clean, report_path)
    safe_stem = report_path.stem

    clean_md_path = report_path.with_name(f"{safe_stem}_clean.md")
    clean_md_path.write_text(md_text_clean, encoding="utf-8")

    html_email_raw = base.build_report_html(md_text_clean, report_date_str, output_dir, render_mode="email")
    html_email, chart_png_bytes = patch_email_html(html_email_raw)

    html_path = report_path.with_name(f"{safe_stem}_delivery.html")
    html_path.write_text(html_email, encoding="utf-8")

    pdf_path = report_path.with_name(f"{safe_stem}.pdf")
    html_pdf = base.build_report_html(md_text_clean, report_date_str, output_dir, render_mode="pdf")
    base.create_pdf_from_html(html_pdf, pdf_path)

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
        "chart_png_bytes": chart_png_bytes,
        "chart_png_name": f"{safe_stem}_equity_chart.png",
    }


def send_email_with_attachments(assets: dict) -> tuple[list[str], Path, str]:
    """
    Same delivery semantics as send_fxreport.py, but with a multipart/related HTML
    section that includes the equity chart as an inline CID image.
    """
    subject = f"{base.TITLE} {assets['report_date_str']}"

    smtp_host = base.require_env("MRKT_RPRTS_SMTP_HOST")
    smtp_port = int(base.os.environ.get("MRKT_RPRTS_SMTP_PORT") or "587")
    smtp_user = base.require_env("MRKT_RPRTS_SMTP_USER")
    smtp_pass = base.require_env("MRKT_RPRTS_SMTP_PASS")
    mail_from = base.require_env("MRKT_RPRTS_MAIL_FROM")

    mail_to_env = base.os.environ.get("MRKT_RPRTS_MAIL_TO", base.REQUIRED_MAIL_TO).strip()
    if mail_to_env != base.REQUIRED_MAIL_TO:
        raise RuntimeError(f"Recipient mismatch: expected {base.REQUIRED_MAIL_TO}, got {mail_to_env}")
    mail_to = base.REQUIRED_MAIL_TO

    root = MIMEMultipart("mixed")
    root["Subject"] = subject
    root["From"] = mail_from
    root["To"] = mail_to

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(base.plain_text_from_markdown(assets["md_text_clean"]), "plain", "utf-8"))

    related = MIMEMultipart("related")
    related.attach(MIMEText(assets["html_email"], "html", "utf-8"))

    chart_img = MIMEImage(assets["chart_png_bytes"], _subtype="png")
    chart_img.add_header("Content-ID", "<fx_equity_chart>")
    chart_img.add_header("Content-Disposition", "inline", filename=assets["chart_png_name"])
    related.attach(chart_img)

    alternative.attach(related)
    root.attach(alternative)

    attachments = [
        assets["pdf_path"].name,
        assets["clean_md_path"].name,
        assets["html_path"].name,
    ]
    for path in [assets["pdf_path"], assets["clean_md_path"], assets["html_path"]]:
        subtype = "pdf" if path.suffix == ".pdf" else ("markdown" if path.suffix == ".md" else "html")
        with open(path, "rb") as handle:
            attachment = base.MIMEApplication(handle.read(), _subtype=subtype)
        attachment.add_header("Content-Disposition", "attachment", filename=path.name)
        root.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], root.as_string())

    manifest_path = assets["pdf_path"].with_name(f"{assets['safe_stem']}_delivery_manifest.txt")
    base.write_delivery_manifest(
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
    latest_report = base.latest_report_file(output_dir)
    assets = generate_delivery_assets(output_dir, latest_report)

    if args.validate_only:
        print(
            "REPORT_FRESHNESS_OK | "
            f"report={latest_report.name} | "
            f"cash={base.extract_labeled_value(base.section_body(assets['md_text_clean'], 15), 'Cash (USD):')} | "
            f"nav={base.extract_labeled_value(base.section_body(assets['md_text_clean'], 15), 'Total portfolio value (USD):')}"
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

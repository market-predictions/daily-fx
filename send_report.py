import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from docx import Document


def build_docx_from_markdown(md_text: str, output_path: Path) -> None:
    """
    Simple markdown-to-docx converter.
    Keeps it basic but much prettier than plain text email.
    """
    doc = Document()

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            doc.add_paragraph("")
            continue

        # Headings
        if line.startswith("# "):
            doc.add_heading(line[2:].strip(), level=1)
            continue
        if line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=3)
            continue

        # Bullet points
        if line.startswith("- "):
            doc.add_paragraph(line[2:].strip(), style="List Bullet")
            continue

        # Numbered list items like "1. text"
        stripped = line.lstrip()
        if len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] == ". ":
            doc.add_paragraph(stripped[3:].strip(), style="List Number")
            continue

        # Otherwise normal paragraph
        doc.add_paragraph(line)

    doc.save(output_path)


def extract_summary(md_text: str, max_lines: int = 24) -> str:
    """
    Build a short email body from the report.
    Focus on the Executive Summary and Bottom Line if present.
    """
    lines = md_text.splitlines()

    body_lines = []
    in_exec = False
    in_bottom = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## 1."):
            in_exec = True
            in_bottom = False
            body_lines.append("WEEKLY ETF PORTFOLIO REVIEW\n")
            continue

        if stripped.startswith("## 11."):
            in_exec = False
            in_bottom = True
            body_lines.append("\nBOTTOM LINE\n")
            continue

        if stripped.startswith("## ") and not stripped.startswith("## 1.") and not stripped.startswith("## 11."):
            in_exec = False
            in_bottom = False

        if in_exec or in_bottom:
            if stripped:
                # Remove markdown emphasis markers for cleaner email text
                cleaned = stripped.replace("**", "").replace("`", "")
                body_lines.append(cleaned)

    if not body_lines:
        # Fallback: take first non-empty lines
        fallback = [ln.strip().replace("**", "").replace("`", "") for ln in lines if ln.strip()]
        body_lines = fallback[:max_lines]

    summary = "\n".join(body_lines).strip()

    summary += "\n\nFull formatted report is attached as a Word document."
    return summary


def main() -> None:
    # Find newest weekly report
    output_dir = Path("output")
    reports = sorted(output_dir.glob("weekly_analysis_*.md"))

    if not reports:
        raise FileNotFoundError("No weekly_analysis_*.md file found in output/")

    latest_report = reports[-1]
    md_text = latest_report.read_text(encoding="utf-8")

    # Build docx next to report
    docx_path = latest_report.with_suffix(".docx")
    build_docx_from_markdown(md_text, docx_path)

    subject = f"Weekly ETF Portfolio Review - {latest_report.stem.replace('weekly_analysis_', '')}"
    body = extract_summary(md_text)

    # Read SMTP settings
    smtp_host = os.environ["MRKT_RPRTS_SMTP_HOST"]
    smtp_port = int(os.environ.get("MRKT_RPRTS_SMTP_PORT") or "587")
    smtp_user = os.environ["MRKT_RPRTS_SMTP_USER"]
    smtp_pass = os.environ["MRKT_RPRTS_SMTP_PASS"]
    mail_from = os.environ["MRKT_RPRTS_MAIL_FROM"]
    mail_to = os.environ["MRKT_RPRTS_MAIL_TO"]

    # Build email
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(docx_path, "rb") as f:
        attachment = MIMEApplication(
            f.read(),
            _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=docx_path.name,
        )
        msg.attach(attachment)

    # Send email
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(mail_from, [mail_to], msg.as_string())

    print(f"Sent email for {latest_report.name} with attachment {docx_path.name}")


if __name__ == "__main__":
    main()

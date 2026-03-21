import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText

# Find the newest weekly report in output/
output_dir = Path("output")
reports = sorted(output_dir.glob("weekly_analysis_*.md"))

if not reports:
    raise FileNotFoundError("No weekly_analysis_*.md file found in output/")

latest_report = reports[-1]
body = latest_report.read_text(encoding="utf-8")

subject = f"Weekly ETF Portfolio Review - {latest_report.stem.replace('weekly_analysis_', '')}"

smtp_host = os.environ["MRKT_RPRTS_SMTP_HOST"]
smtp_port = int(os.environ.get("MRKT_RPRTS_SMTP_PORT"))
smtp_user = os.environ["MRKT_RPRTS_SMTP_USER"]
smtp_pass = os.environ["MRKT_RPRTS_SMTP_PASS"]
mail_from = os.environ["MRKT_RPRTS_MAIL_FROM"]
mail_to = os.environ["MRKT_RPRTS_MAIL_TO"]

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = subject
msg["From"] = mail_from
msg["To"] = mail_to

with smtplib.SMTP(smtp_host, smtp_port) as server:
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.sendmail(mail_from, [mail_to], msg.as_string())

print(f"Sent email for {latest_report.name}")

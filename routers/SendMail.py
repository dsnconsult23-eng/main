import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from routers    import Connection



def get_smtp_settings():
    """Fetch SMTP settings from the database using Connection.OSISinit()"""
    sql = "SELECT key, value FROM adm_appsettings WHERE key LIKE 'smtp.%'"

    results, OK = Connection.OSISinit()
    if not OK:
        print("Error - no connection to the database")
        return {}

    results.execute(sql)

    settings = {}
    while True:
        row = results.fetchone()
        if not row:
            break
        settings[row[0]] = row[1]  # key-value from DB

    results.close()
    return settings


def send_html_email_with_attachments(recipient_email, subject, html_body, pdf_paths):
    """Send HTML email with one or more attachments using SMTP settings from DB"""

    # Load SMTP config from DB
    settings = get_smtp_settings()
    sender_email = settings.get("smtp.fromaddress")
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")
    smtp_host = settings.get("smtp.host")
    smtp_port = int(settings.get("smtp.port", 25))
    smtp_auth = settings.get("smtp.auth", "").lower() == "true"

    if not sender_email or not smtp_host:
        print("❌ Missing SMTP settings.")
        return

    # Compose email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    # Attach HTML body
    msg.attach(MIMEText(html_body, "html"))

    # Attach PDFs
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(pdf_path)}"
                )
                msg.attach(part)
        else:
            print(f"⚠️ PDF not found: {pdf_path}")

    # Send
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
            if smtp_auth:
                server.login(sender_username, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"✅ Email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

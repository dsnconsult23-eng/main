import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from routers import Connection
from email.mime.image import MIMEImage


def get_smtp_settings():
    """Fetch SMTP settings from the database using Connection.OSISinit()"""
    sql = "SELECT key, value FROM adm_appsettings WHERE key LIKE 'smtp.%'"

    results, OK = Connection.OSISinit()
    if not OK:
        print("❌ Error - no connection to the database")
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


def send_html_email_with_attachments_image_bck(recipient_email, subject, html_body,client_id, pdf_paths=None):
    """Send HTML email with embedded logo + attachments using SMTP settings from DB"""

    # Load SMTP config from DB
    settings = get_smtp_settings()
    sender_email = settings.get("smtp.fromaddress")
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")
    smtp_host = settings.get("smtp.host")
    smtp_port = int(settings.get("smtp.port", 25))
    smtp_auth = settings.get("smtp.auth", "").lower() == "true"

    smtp_host = "smtp.office365.com"
    smtp_port = 587
    smtp_auth= True

    if not sender_email or not smtp_host:
        print("❌ Missing SMTP settings.")
        return

    # Root container (related: html + images + attachments)
    msg = MIMEMultipart("related")
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    # Alternative container (for HTML/text)
    alternative = MIMEMultipart("alternative")
    msg.attach(alternative)

    # Attach HTML body
    alternative.attach(MIMEText(html_body, "html", "utf-8"))

    # 🔹 Embed logo
    logo_path = "/opt/siglife-reporting/Image/image002.jpg"
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo = MIMEImage(f.read())
                logo.add_header("Content-ID", "<uniqa_logo>")  # must match cid in HTML
                logo.add_header("Content-Disposition", "inline", filename="logo.jpg")
                msg.attach(logo)
        except Exception as e:
            print(f"⚠️ Could not attach logo: {e}")
    else:
        print(f"⚠️ Logo not found at {logo_path}")

    # 🔹 Attach PDFs
    for pdf_path in pdf_paths or []:
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
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
        use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()

            if use_starttls:
                server.starttls()
                server.ehlo()

            if smtp_auth:
                server.login(sender_username, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"✅ Email sent to {recipient_email}")
            print ("Saving mail log to database...")
        # Save to DB
        if pdf_paths:
            file_path = pdf_paths[0]
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                file_content = f.read()
        else:

            file_path = file_name = file_content = None
            file_size = 0
        
        conn, OK = Connection.OSISinit()
        if not OK:
            print("❌ Error - no connection to the database")
            return {}
    
        save_mail_to_db(conn, client_id, recipient_email, file_path, file_name, file_content, file_size, status_id=1)
        print("✅ Mail log saved to database")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def send_html_email_with_attachments(recipient_email, subject, html_body, pdf_paths, conn, client_id):
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
    msg.attach(MIMEText(html_body, "html"))

    # Attach PDFs
    for pdf_path in pdf_paths or []:
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
        use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()

            if use_starttls:
                server.starttls()
                server.ehlo()

            if smtp_auth:
                server.login(sender_username, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"✅ Email sent to {recipient_email}")
        print ("Saving mail log to database...")
        # Save to DB
        if pdf_paths:
            file_path = pdf_paths[0]
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                file_content = f.read()
        else:
            file_path = file_name = file_content = None
            file_size = 0
        
        conn, OK = Connection.OSISinit()
        if not OK:
            print("❌ Error - no connection to the database")
            return {}
    
        save_mail_to_db(conn, client_id, recipient_email, file_path, file_name, file_content, file_size, status_id=1)
        print("✅ Mail log saved to database")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def save_mail_to_db(conn, client_id, recipient_email, file_path, file_name, file_content, file_size, status_id=1):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print ("Saving mail log to database...")
    sql = """
        INSERT INTO send_mail_dolzna_premija
        (send_mail_dolzna_premijaid, datecreated, usercreated, version,
         par_clientid, mail, path, filename, content, file_size, par_statusid)
        VALUES (sq_send_mail_dolzna_premija.nextval, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
    """
    
    conn.execute(sql, (now, 'admin', client_id, recipient_email, file_path, file_name, file_content, file_size, status_id))

    print("✅ Mail log saved to database")

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from email.utils import encode_rfc2231


def send_html_email_with_attachments_image(recipient_email, subject, html_body, client_id, pdf_paths=None):
    """Send HTML email with embedded logo + PDF attachments (robust for Office365/mobile clients)."""

    # Load SMTP config from DB
    settings = get_smtp_settings()
    sender_email = settings.get("smtp.fromaddress")
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")
    smtp_host = settings.get("smtp.host")
    smtp_port = int(settings.get("smtp.port", 25))
    smtp_auth = (settings.get("smtp.auth", "") or "").lower() == "true"

    # Force Office365 (as in your code)
    smtp_host = "smtp.office365.com"
    smtp_port = 587
    smtp_auth = True

    if not sender_email or not smtp_host:
        print("❌ Missing SMTP settings.")
        return

    pdf_paths = pdf_paths or []

    # Root container (related: html + inline images + attachments)
    msg = MIMEMultipart("related")
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject

    # Alternative container (for HTML/text)
    alternative = MIMEMultipart("alternative")
    msg.attach(alternative)

    # Attach HTML body
    alternative.attach(MIMEText(html_body, "html", "utf-8"))

    # 🔹 Embed logo
    logo_path = "/opt/siglife-reporting/Image/image002.jpg"
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<uniqa_logo>")  # must match cid in HTML
            logo.add_header("Content-Disposition", "inline", filename="logo.jpg")
            msg.attach(logo)
        except Exception as e:
            print(f"⚠️ Could not attach logo: {e}")
    else:
        print(f"⚠️ Logo not found at {logo_path}")

    # 🔹 Attach PDFs (use application/pdf + RFC2231-safe filename)
    for pdf_path in pdf_paths:
        try:
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) <= 0:
                print(f"⚠️ PDF not found or empty: {pdf_path}")
                continue

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # quick sanity check that attachment starts like PDF
            if not pdf_bytes.startswith(b"%PDF"):
                print(f"⚠️ Not a PDF (missing %PDF header): {pdf_path}")
                # still attach, but warn
                # continue

            part = MIMEBase("application", "pdf")  # better than octet-stream for many clients
            part.set_payload(pdf_bytes)

            encoders.encode_base64(part)
            part["Content-Transfer-Encoding"] = "base64"

            filename = os.path.basename(pdf_path)

            # Content-Disposition with filename
            part.add_header("Content-Disposition", "attachment", filename=filename)

            # Content-Type with RFC2231 encoded name (helps with non-ascii filenames)
            part.add_header("Content-Type", "application/pdf", name=encode_rfc2231(filename, "utf-8"))

            msg.attach(part)

        except Exception as e:
            print(f"⚠️ Could not attach PDF {pdf_path}: {e}")

    # Optional: save EML for debugging (uncomment if needed)
    # try:
    #     with open("/tmp/outgoing.eml", "wb") as f:
    #         f.write(msg.as_bytes())
    # except Exception:
    #     pass

    # Send + log to DB
    try:
        use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()

            if use_starttls:
                server.starttls()
                server.ehlo()

            if smtp_auth:
                server.login(sender_username, sender_password)

            # IMPORTANT: send bytes, not string (avoids attachment corruption in some cases)
            server.sendmail(sender_email, recipient_email, msg.as_bytes())

        print(f"✅ Email sent to {recipient_email}")
        print("Saving mail log to database...")

        # Save to DB (store first attachment content if present)
        if pdf_paths:
            file_path = pdf_paths[0]
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                file_content = f.read()
        else:
            file_path = file_name = file_content = None
            file_size = 0

        conn, OK = Connection.OSISinit()
        if not OK:
            print("❌ Error - no connection to the database")
            return {}

        save_mail_to_db(conn, client_id, recipient_email, file_path, file_name, file_content, file_size, status_id=1)
        print("✅ Mail log saved to database")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        # optionally log failure too
        try:
            conn, OK = Connection.OSISinit()
            if OK:
                save_mail_to_db(conn, client_id, recipient_email, None, None, None, 0, status_id=2)
        except Exception:
            pass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from email.utils import make_msgid, formatdate, encode_rfc2231
from routers import Connection
import os
from typing import Optional, List
import smtplib
import datetime
import time


def send_many_emails_with_logo_and_db_log(
    recipients: List[dict],
    subject: str,
    html_body: str,
    smtp_cfg: dict,
    job_id: Optional[str] = None,
    max_retries_per_email: int = 3,
    reconnect_backoff_sec: float = 2.0,
):
    sent = 0
    failed = 0

    host = smtp_cfg.get("smtp_host")
    port = smtp_cfg.get("smtp_port")
    username = smtp_cfg.get("sender_username")
    password = smtp_cfg.get("sender_password")
    from_email = smtp_cfg.get("sender_email")

    logo_path = "/opt/siglife-reporting/Image/image002.jpg"

    def connect_smtp() -> smtplib.SMTP:
        srv = smtplib.SMTP(host, port, timeout=60)
        srv.ehlo()
        srv.starttls()
        srv.ehlo()
        srv.login(username, password)
        return srv

    def build_msg(to_email: str, pdf_paths: Optional[List[str]] = None):
        pdf_paths = pdf_paths or []

        msg = MIMEMultipart("related")
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid()
        msg["Date"] = formatdate(localtime=True)

        alternative = MIMEMultipart("alternative")
        msg.attach(alternative)

        alternative.attach(MIMEText("This email contains HTML content.", "plain", "utf-8"))
        alternative.attach(MIMEText(html_body or "", "html", "utf-8"))

        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f:
                    logo = MIMEImage(f.read())
                logo.add_header("Content-ID", "<uniqa_logo>")
                logo.add_header("Content-Disposition", "inline", filename="logo.jpg")
                msg.attach(logo)
            except Exception as e:
                print(f"⚠️ Could not attach logo: {e}")
        else:
            print(f"⚠️ Logo not found at {logo_path}")

        attached_count = 0
        first_attachment_content = None
        first_attachment_name = None
        first_attachment_size = 0
        first_attachment_path = None

        for idx, pdf_path in enumerate(pdf_paths, start=1):
            try:
                if not pdf_path or not os.path.exists(pdf_path) or os.path.getsize(pdf_path) <= 0:
                    print(f"⚠️ PDF not found or empty: {pdf_path}")
                    continue

                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                if not pdf_bytes.startswith(b"%PDF"):
                    print(f"⚠️ Not a PDF (missing %PDF header): {pdf_path}")

                part = MIMEBase("application", "pdf")
                part.set_payload(pdf_bytes)
                encoders.encode_base64(part)
                part["Content-Transfer-Encoding"] = "base64"

                filename = os.path.basename(pdf_path)
                part.add_header("Content-Disposition", "attachment", filename=filename)
                part.add_header("Content-Type", "application/pdf", name=encode_rfc2231(filename, "utf-8"))

                msg.attach(part)
                attached_count += 1

                if first_attachment_content is None:
                    first_attachment_content = pdf_bytes
                    first_attachment_name = filename
                    first_attachment_size = len(pdf_bytes)
                    first_attachment_path = pdf_path

            except Exception as e:
                print(f"⚠️ Could not attach PDF {pdf_path}: {e}")

        return (
            msg,
            attached_count,
            first_attachment_path,
            first_attachment_name,
            first_attachment_content,
            first_attachment_size
        )

    server = None
    try:
        server = connect_smtp()

        for rec in recipients:
            email = (rec.get("email") or "").strip()
            client_id = rec.get("client_id")
            policy_no = rec.get("policy_no")
            client_name = rec.get("client_name")
            address = rec.get("address")
            city = rec.get("city")
            pdf_paths = rec.get("pdf_paths") or []
            print(client_id)
            print("Cl")
            if not email:
                failed += 1
                continue

            last_err = None

            for attempt in range(1, max_retries_per_email + 1):
                try:
                    if server is None:
                        server = connect_smtp()

                    (
                        msg,
                        attached_count,
                        file_path,
                        file_name,
                        file_content,
                        file_size
                    ) = build_msg(email, pdf_paths)

                    server.sendmail(from_email, email, msg.as_bytes())
                    sent += 1

                    try:
                        _audit_email_to_db(
                            job_id=job_id,
                            recipient=email,
                            subject=subject,
                            message_id=str(msg["Message-ID"]),
                            status="SENT",
                            error_message=None,
                            attachments_cnt=attached_count,
                            client_id=str(client_id) if client_id is not None else None,
                            policy_no=policy_no,
                            client_name=client_name,
                            address=address,
                            city=city,
                            attachment_path=file_path,
                            attachment_filename=file_name,
                            attachment_position=1 if file_name else None,
                        )
                    except Exception as e:
                        print(f"⚠️ Audit SENT failed for {email}: {e}")

                    try:
                        conn, OK = Connection.OSISinit()
                        if OK:
                            save_mail_to_db(
                                conn,
                                client_id,
                                email,
                                file_path,
                                file_name,
                                file_content,
                                file_size,
                                status_id=1
                            )
                    except Exception as e:
                        print(f"⚠️ save_mail_to_db SENT failed for {email}: {e}")

                    last_err = None
                    break

                except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError) as e:
                    last_err = repr(e)

                    try:
                        if server is not None:
                            server.quit()
                    except Exception:
                        pass

                    server = None
                    time.sleep(reconnect_backoff_sec * attempt)
                    continue

                except smtplib.SMTPResponseException as e:
                    last_err = f"{e.smtp_code} {e.smtp_error!r}"
                    if 400 <= e.smtp_code < 500:
                        time.sleep(reconnect_backoff_sec * attempt)
                        continue
                    break

                except Exception as e:
                    last_err = repr(e)
                    break

            if last_err:
                failed += 1
                err_msg = f"{email}: {last_err}"

                try:
                    _audit_email_to_db(
                        job_id=job_id,
                        recipient=email,
                        subject=subject,
                        message_id=None,
                        status="FAILED",
                        error_message=last_err,
                        attachments_cnt=len(pdf_paths),
                        client_id=str(client_id) if client_id is not None else None,
                        policy_no=policy_no,
                        client_name=client_name,
                        address=address,
                        city=city,
                        attachment_path=pdf_paths[0] if pdf_paths else None,
                        attachment_filename=os.path.basename(pdf_paths[0]) if pdf_paths else None,
                        attachment_position=1 if pdf_paths else None,
                    )
                except Exception as e:
                    print(f"⚠️ Audit FAILED failed for {email}: {e}")

                try:
                    conn, OK = Connection.OSISinit()
                    if OK:
                        save_mail_to_db(conn, client_id, email, None, None, None, 0, status_id=2)
                except Exception as e:
                    print(f"⚠️ save_mail_to_db FAILED failed for {email}: {e}")

                if job_id:
                    try:
                        _set_job(job_id, last_error=err_msg)
                    except Exception:
                        pass

    finally:
        try:
            if server is not None:
                server.quit()
        except Exception:
            pass

    return sent, failed

# ===========================
# Audit log
# ===========================
def _audit_email_to_db(
    *,
    job_id: Optional[str],
    recipient: str,
    subject: str,
    message_id: Optional[str],
    status: str,
    error_message: Optional[str],
    attachments_cnt: int,
    client_id: Optional[str] = None,
    policy_no: Optional[str] = None,
    client_name: Optional[str] = None,
    address: Optional[str] = None,
    city: Optional[str] = None,
    attachment_path: Optional[str] = None,
    attachment_filename: Optional[str] = None,
    attachment_position: Optional[int] = None,
):
    results, OK = Connection.OSISinit()
    if not OK:
        print("[AUDIT][DB] ❌ No DB connection")
        return

    cur = results  # кај тебе најчесто ова е cursor
    try:
        sql = """
            INSERT INTO email_audit_log
            (
                job_id,
                recipient,
                subject,
                message_id,
                status,
                error_message,
                attachments_cnt,
                client_id,
                policy_no,
                client_name,
                address,
                city,
                attachment_path,
                attachment_filename,
                attachment_position,
                created_at,tip
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT YEAR TO SECOND,'O'
            )
        """

        cur.execute(sql, (
            job_id,
            recipient,
            subject,
            message_id,
            status,
            error_message,
            int(attachments_cnt),
            client_id,
            policy_no,
            client_name,
            address,
            city,
            attachment_path,
            attachment_filename,
            attachment_position,
        ))

        try:
            cur.connection.commit()
        except Exception:
            pass

    except Exception as e:
        print("[AUDIT][DB] ❌ Insert failed:", repr(e))

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

# ===========================
# Simple in-memory jobs store (shared for Izvestuvanja + Opomeni)
# ===========================
JOBS = {}  # job_id -> dict(...)
def _set_job(job_id: str, **kwargs):
    job = JOBS.get(job_id, {})
    job.update(kwargs)
    JOBS[job_id] = job
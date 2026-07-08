import os
import pandas as pd
import tempfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from routers.Connection import OSISinitConn
from routers.SendMail import get_smtp_settings
import datetime
import xlsxwriter  # ✅ new library for encryption
import msoffcrypto
import xlwt
import io
import pyzipper
from fastapi import APIRouter
from typing import Optional
from Utils.excel_formatter import format_provision_excel, format_provision_excel_in_memory,process_broker_excel,format_broker_excel_in_memory


router = APIRouter()

def fetch_query(sql):
    conn, cursor, ok = OSISinitConn()
    if not ok or conn is None:
        return None, False
    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows, True
    finally:
        cursor.close()
        conn.close()



def create_encrypted_xls(df: pd.DataFrame, edb: str):
    """Create a temporary .xls file from df and encrypt it with edb password."""
    edb = str(edb).strip() if edb else "SigLife@2025"

    # Create temporary XLS
    tmp_plain = tempfile.NamedTemporaryFile(delete=False, suffix=".xls")
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Sheet1")

    # Write headers
    for col_idx, col_name in enumerate(df.columns):
        ws.write(0, col_idx, col_name)

    # Write data rows
    for row_idx, row in enumerate(df.itertuples(index=False), start=1):
        for col_idx, value in enumerate(row):
            ws.write(row_idx, col_idx, value)

    wb.save(tmp_plain.name)
    print(f"🧾 Plain Excel created: {tmp_plain.name}")

    # Encrypt XLS
    tmp_enc = tempfile.NamedTemporaryFile(delete=False, suffix="_protected.xls")
    with open(tmp_plain.name, "rb") as f_in, open(tmp_enc.name, "wb") as f_out:
        file = msoffcrypto.OfficeFile(f_in)
        file.load_key(password=edb)
        file.encrypt(f_out)
    print(f"🔒 Encrypted file created: {tmp_enc.name}")

    os.remove(tmp_plain.name)
    return tmp_enc.name

def create_encrypted_zip(df: pd.DataFrame, password: str, mesec: int, godina: int, filename: str = "report.xlsx"):


    """
    Create an in-memory encrypted ZIP containing the Excel report
    """
    # 1️⃣ Create Excel in memory
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False)
    excel_io.seek(0)

    # 2️⃣ Create ZIP in memory
    zip_io = io.BytesIO()
    with pyzipper.AESZipFile(zip_io, 'w', compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode())
        zf.writestr(filename, excel_io.getvalue())
    zip_io.seek(0)

    return zip_io
def vrati_kurs(mesec: int, godina: int) -> float:
    rows, ok = fetch_query(
        f"select vrati_kurs(last_day(MDY({mesec}, 1, {godina})), 'EUR')"
    )
    if not ok or not rows:
        raise RuntimeError(f"vrati_kurs failed / no rows for {mesec}/{godina}")

    # rows is like: [(37.11,)]  -> take first row, first column
    value = rows[0][0]
    return float(value)



def send_mail_broker(month: int, year: int):
    """Prepare Excel, encrypt it with broker EDB, and send mail for each broker."""
    conn, cursor, ok = OSISinitConn()

    sql_brokers = f"""
        SELECT DISTINCT broker, broker_name, vrati_client_edb(broker) AS edb
        FROM provizija_client
        WHERE YEAR(pap_datumod) = {year}
          AND MONTH(pap_datumod) = {month}
        and broker<>5288
    """
    brokers, ok = fetch_query(sql_brokers)
    if not ok or not brokers:
        return {"success": False, "message": "❌ No brokers found or DB error."}

    for broker, broker_name, edb in brokers:
        print(f"📦 Preparing report for {broker_name} (broker={broker}, EDB={edb})")

        if broker == 17374:
            sql = f"""
                SELECT *
                FROM appuser.provizija_client_sms
                WHERE YEAR(pap_datumod) = {year}
                  AND MONTH(pap_datumod) = {month}
                  AND broker = {broker}
            """
        else:
            sql = f"""
                SELECT *
                FROM vesna.provizija_client
                WHERE YEAR(pap_datumod) = {year}
                  AND MONTH(pap_datumod) = {month}
                  AND broker = {broker}
            """

        df = pd.read_sql(sql, conn)

        if df.empty:
            print(f"⚠️ No data for broker {broker}")
            continue

        # 3️⃣ Create encrypted Excel (replaces msoffcrypto-tool)
        print(f"🔒 Encrypting Excel for {broker_name} with EDB: {edb}")
        print(f"🔒 Creating encrypted ZIP for {broker_name}")
        zip_io = create_encrypted_zip(df, password=str(edb),mesec=month,godina=year)
        send_email_with_zip(broker_name, zip_io, filename=f"provizija_{month}_{year}.zip")

    cursor.close()
    conn.close()
    return {"success": True, "message": "📧 Мејловите се успешно испратени!"}


def send_email_with_zip(broker_name, zip_io, filename="report.zip"):
    """Send an email with encrypted Excel attachment to broker."""
    settings = get_smtp_settings()
    sender_email = settings.get("smtp.fromaddress") or "noreply@siglife.mk"
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")
    smtp_host = settings.get("smtp.host", "mail.siglife.mk")
    smtp_port = int(settings.get("smtp.port", 25))
    smtp_auth = settings.get("smtp.auth", "").lower() == "true"

    smtp_host = "smtp.office365.com"
    smtp_port = 587
    smtp_auth= True

    recipient_email = 'snakevska@gmail.com'
    subject = "Извештај за провизија"
    html_body = f"""
        <p>Почитувани {broker_name},</p>
        <p>Во прилог е доставен извештајот за провизијата за избраниот месец.</p>
        <p>Лозинката за документот е вашиот ЕДБ број.</p>
        <p>Поздрав,<br>СИГАЛ Лајф</p>
    """

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    part = MIMEBase("application", "zip")
    part.set_payload(zip_io.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={filename}")
    msg.attach(part)

    try:
        use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()

            if use_starttls:
                server.starttls()
                server.ehlo()

            if smtp_auth:
                server.login(sender_username, sender_password)

            server.sendmail(sender_email, [recipient_email], msg.as_string())
            print(f"✅ Email sent to {recipient_email}")

    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {type(e).__name__}: {e}")

    # try:
    #     with smtplib.SMTP(smtp_host, smtp_port) as server:
    #         server.ehlo()
    #         if smtp_port == 587:
    #             server.starttls()
    #         if smtp_auth:
    #             server.login(sender_username, sender_password)
    #         server.sendmail(sender_email, recipient_email, msg.as_string())
    #         print(f"✅ Email sent to {recipient_email}")
    # except Exception as e:
    #     print(f"❌ Failed to send email to {recipient_email}: {e}")

import os
import io
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from routers.Connection import OSISinitConn
from routers.SendMail import get_smtp_settings
import pyzipper


def fetch_query(sql):
    """Helper to run SQL and return rows."""
    conn, cursor, ok = OSISinitConn()
    if not ok or conn is None:
        return None, False
    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows, True
    finally:
        cursor.close()
        conn.close()


def create_encrypted_zip(df: pd.DataFrame, password: str, mesec: int, godina: int, filename: str = "report.xlsx"):

    """
    Create an in-memory encrypted ZIP containing an Excel file.
    Works cross-platform (Windows/Linux).
    """
    # 1️⃣ Create Excel in memory
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False, engine="openpyxl")
    excel_io.seek(0)

        # Try formatting the Excel
    excel_io = format_provision_excel_in_memory(excel_io, sheet_name="Sheet1", 
                    
                    prov_col="T",
                    label_col="S",
                    kurs=vrati_kurs(mesec, godina),              # курс од vrati_kurs()
                    kurs_cell="X1"         # скриена ќелија
                    )
 

    # 2️⃣ Create encrypted ZIP in memory
    zip_io = io.BytesIO()
    with pyzipper.AESZipFile(zip_io, 'w', compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode())
        zf.writestr(filename, excel_io.getvalue())
    zip_io.seek(0)
    return zip_io

# def send_email_with_zip(broker_name, zip_io, filename, recipient_email, mesec, godina):
#     """Send an email with encrypted ZIP attachment."""
#     settings = get_smtp_settings()
#     sender_email = settings.get("smtp.fromaddress", "noreply@siglife.mk")
#     sender_username = settings.get("smtp.username")
#     sender_password = settings.get("smtp.password")
#     smtp_host = settings.get("smtp.host", "mail.siglife.mk")
#     smtp_port = int(settings.get("smtp.port", 25))
#     smtp_auth = settings.get("smtp.auth", "").lower() == "true"

#     smtp_host = "smtp.office365.com"
#     smtp_port = "587"
#     smtp_auth= "true"

#     subject = "Извештај за провизија"
#     html_body = f"""
#         <p>Почитувани {broker_name},</p>
#         <p>Во прилог е доставен извештајот за провизијата за  месец {mesec}/{godina}.</p>
#         <p>Лозинката за документот е вашиот ЕДБ број.</p>
#         <p>Поздрав,<br>Уника Лајф</p>
#     """

#     msg = MIMEMultipart()
#     msg["From"] = sender_email
#     msg["To"] = recipient_email
#     msg["Subject"] = subject
#     msg.attach(MIMEText(html_body, "html"))

#     # Attach ZIP file
#     part = MIMEBase("application", "zip")
#     part.set_payload(zip_io.read())
#     encoders.encode_base64(part)
#     part.add_header("Content-Disposition", f"attachment; filename={filename}")
#     msg.attach(part)

#     # try:
#     #     with smtplib.SMTP(smtp_host, smtp_port) as server:
#     #         server.ehlo()
#     #         if smtp_port == 587:
#     #             server.starttls()
#     #         if smtp_auth:
#     #             server.login(sender_username, sender_password)
#     #         server.sendmail(sender_email, recipient_email, msg.as_string())
#     #         print(f"✅ Email sent to {recipient_email}")
#     # except Exception as e:
#     #     print(f"❌ Failed to send email to {recipient_email}: {e}")

#     try:
#         use_starttls = (smtp_host or "").strip().lower() == "smtp.office365.com"

#         with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
#             server.ehlo()

#             if use_starttls:
#                 server.starttls()
#                 server.ehlo()

#             if smtp_auth:
#                 server.login(sender_username, sender_password)

#             server.sendmail(sender_email, [recipient_email], msg.as_string())
#             print(f"✅ Email sent to {recipient_email}")

#     except Exception as e:
#         print(f"❌ Failed to send email to {recipient_email}: {type(e).__name__}: {e}")

def send_email_with_zip(broker_name, zip_io, filename, recipient_email, mesec, godina):
    """Send an email with encrypted ZIP attachment via Office365 (587 + STARTTLS + AUTH)."""
    settings = get_smtp_settings()
    sender_email = settings.get("smtp.fromaddress") or "noreply@siglife.mk"
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")

    # ✅ Force Office365 (stable)
    smtp_host = "smtp.office365.com"
    smtp_port = 587          # ✅ int
    smtp_auth = True         # ✅ bool

    subject = "Извештај за провизија"
    html_body = f"""
        <p>Почитувани {broker_name},</p>
        <p>Во прилог е доставен извештајот за провизијата за месец {mesec}/{godina}.</p>
        <p>Лозинката за документот е вашиот ЕДБ број.</p>
        <p>Поздрав,<br>Сигал Лајф</p>
    """

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    # ✅ ensure attachment is readable from start
    zip_io.seek(0)

    part = MIMEBase("application", "zip")
    part.set_payload(zip_io.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={filename}")
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            if smtp_auth:
                server.login(sender_username, sender_password)

            server.sendmail(sender_email, [recipient_email], msg.as_string())
            print(f"✅ Email sent to {recipient_email}")

    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {type(e).__name__}: {e}")


def send_mail_broker(month: int, year: int, brokercode: Optional[str] = None):

    """Prepare Excel, encrypt it with broker EDB, and send mail for each broker."""
    conn, cursor, ok = OSISinitConn()
    if not ok:
        print("❌ DB connection failed")
        return {"success": False}

    sql_brokers = f"""
        SELECT DISTINCT broker, broker_name, vrati_client_edb(broker) AS edb
        FROM provizija_client
        WHERE YEAR(pap_datumod) = {year}
          AND MONTH(pap_datumod) = {month}
        and broker<>5288
    """
        # --- OPTIONAL FILTER BY BROKER ---
    if brokercode:
        sql_brokers += f" AND broker = '{brokercode}'"
    brokers, ok = fetch_query(sql_brokers)
    if not ok or not brokers:
        return {"success": False, "message": "❌ No brokers found or DB error."}

    for broker, broker_name, edb in brokers:
        print(f"📦 Preparing report for {broker_name} (broker={broker}, EDB={edb})")
        if broker == 17374:
            sql = f"""
                SELECT  ponuda_broj, polisabroj, TO_CHAR(skadenca_datum_od, '%d/%m/%Y') as skadenca_datum_od ,period_osig,vkupna_premija,dogovoruvac, 
                dogovoruvac_edb,osigurenik,
                klasa,br_rati, tip_plati, iznos, br_dosp_rati,iznos,naplata,rata, TO_CHAR(datum_valuta, '%d/%m/%Y') as datum_valuta,
                proc_prov_cela,provizija_proc,iznos_provizija,TO_CHAR(datum_zadol, '%d/%m/%Y') as  datum_zadol, 
                TO_CHAR(datum_valuta, '%d/%m/%Y') datum_valuta,vk_prov,'' as vrakanje,''  as datum_storniranje, ''  as datum_kraj,
                ''  as razlog_kraj,TO_CHAR(datum_ponuda, '%d/%m/%Y') datum_ponuda, TO_CHAR(skadenca_datum_do, '%d/%m/%Y') skadenca_datum_do,
                dogovoruvac_id,osigurenik_id,status,broker_id,broker_name
                FROM appuser.provizija_client_sms
                WHERE YEAR(pap_datumod) = {year}
                  AND MONTH(pap_datumod) = {month}
                  AND broker = {broker}
            """
            df = pd.read_sql(sql, conn)
            if df.empty:
                print(f"⚠️ No data for broker {broker}")
                continue
            headers = [
            "Broj ponude", "BrojPolise", "Datum pocetka", "Doba osiguranja", "Godisnja premija",
            "Ugovarac", "mat broj", "Osiguranik", "Šifra produkta", "Dinamika placanja",
            "Način uplate", "iznos Rate", "Broj dospelih rata", "Dospelo za naplatu", "Placeno",
            "broj rate", "Premija placena do", "Ukupna % provizije", "Presmetana % provizije",
            "provizija", "period od", "period do", "isplaćena provizija Ukupno", "za vraćanje",
            "datum storniranja", "Datum kraja", "Razlog kraja", "DatumUgovaranja", "Datum isteka",
            "SifraUgovaraca", "SifraOsiguranika", "Status", "SifraSaradnika", "SaradnikProdukcija"
            ]
            # Make sure the number of headers matches the number of columns
            if len(headers) == df.shape[1]:
                df.columns = headers
            else:
                print(f"⚠️ Warning: Number of headers ({len(headers)}) does not match number of columns in df ({df.shape[1]})")

            # Now df has the correct headers
            print(df.head())
            print(f"🔒 Creating encrypted ZIP for {broker_name}")
            broker_name_clean = broker_name.replace(" ", "_").replace("/", "_").strip()
            edb_str = str(edb).strip()
            zip_io = create_encrypted_zip_broker(df, password=edb_str, filename=f"provizija_{month}_{year}_{broker}.xlsx")

        else:
            sql = f"""
            SELECT broker_name, polisabroj, ponuda_broj,dogovoruvac,dogovoruvac_edb,dogovoruvac_adresa,
            dogovoruvac_grad,osigurenik, klasa,br_rati,rata,
            TO_CHAR(datum_napl, '%d/%m/%Y') as datum_napl,
            TO_CHAR(datum_zadol, '%d/%m/%Y') as datum_zadol,TO_CHAR(datum_valuta, '%d/%m/%Y') as datum_valuta,koja_godina,osig_suma,premija_zivot,vkupna_premija,provizija_proc,prov_rata,
            premija_nezgoda, prov_rata_nezgoda,naplata,naplata_den,aneks, TO_CHAR(skadenca_datum_od, '%d/%m/%Y') as skadenca_datum_od
            , period_osig, TO_CHAR(skadenca_datum_do, '%d/%m/%Y') as skadenca_datum_do
                FROM vesna.provizija_client
                WHERE YEAR(pap_datumod) = {year}
                AND MONTH(pap_datumod) = {month}
                AND broker = {broker}
            """
            df = pd.read_sql(sql, conn)
            if df.empty:
                print(f"⚠️ No data for broker {broker}")
                continue
            headers = [
            "Брокер","Полиса бр.", "Понуда број", "Договорувач", "Договорувач ЕДБ",
            "Договорувач Адреса", "Договорувач Град", "Осигуреник", "Класа",
            "Број на рати", "Рата",  "Дат.наплата",
            "Дат.задолжување", "Датум валута", "Која година", "Осигурена сума",
            "Премија живот", "Вкупна премија", "Провизија процент", "Провизија рата",
            "Премија дополнително",  "Провизија рата",
            "Наплата", "Наплата ден.", "Анекс",  "Скаденца од",
            "период", "Скаденца до"
            ]

            # Make sure the number of headers matches the number of columns
            if len(headers) == df.shape[1]:
                df.columns = headers
            else:
                print(f"⚠️ Warning: Number of headers ({len(headers)}) does not match number of columns in df ({df.shape[1]})")

            # Now df has the correct headers
            print(df.head())
            
            print(f"🔒 Creating encrypted ZIP for {broker_name}")
            broker_name_clean = broker_name.replace(" ", "_").replace("/", "_").strip()
            edb_str = str(edb).strip()
            zip_io = create_encrypted_zip(df, password=edb_str,mesec=month, godina=year, filename=f"provizija_{month}_{year}_{broker}.xlsx")

        send_email_with_zip(broker_name, zip_io, filename=f"provizija_{month}_{year}_{broker}.zip",recipient_email="mirjana.mihajlovska@sigal.com.mk", mesec=month,godina=year)
        #send_email_with_zip(broker_name, zip_io, filename=f"provizija_{month}_{year}_{broker}.zip",recipient_email="snakevska@gmail.com", mesec=month,godina=year)
    
    cursor.close()
    conn.close()
    return {"success": True, "message": "📧 Мејловите се успешно испратени!"}

import os
import pandas as pd

def generate_excels_broker(month: int, year: int, broker: Optional[str] = None):

    """Generate Excel files for all brokers WITHOUT sending emails."""
    
    # Create base directory
    base_dir = f"/opt/siglife-reporting/broker_excels/{year}/{month}"
    os.makedirs(base_dir, exist_ok=True)

    conn, cursor, ok = OSISinitConn()
    if not ok:
        print("❌ DB connection failed")
        return {"success": False}

    sql_brokers = f"""
        SELECT DISTINCT broker, broker_name, vrati_client_edb(broker) AS edb
        FROM provizija_client
        WHERE YEAR(pap_datumod) = {year}
          AND MONTH(pap_datumod) = {month}
        and broker<>5288
    """
    if broker:
        sql_brokers += f" AND broker = '{broker}'"
    brokers, ok = fetch_query(sql_brokers)
    if not ok or not brokers:
        return {"success": False, "message": "❌ No brokers found or DB error."}

    for broker, broker_name, edb in brokers:
        print(f"📦 Creating Excel for {broker_name} (broker={broker}, EDB={edb})")

        # ---- SELECTS PER BROKER ----
        if broker == 17374:
            sql = f"""
                SELECT ponuda_broj, polisabroj, TO_CHAR(skadenca_datum_od, '%d/%m/%Y') as skadenca_datum_od,
                period_osig, vkupna_premija, dogovoruvac, dogovoruvac_edb, osigurenik,
                klasa, br_rati, tip_plati, iznos, br_dosp_rati, iznos, naplata, rata,
                TO_CHAR(datum_valuta, '%d/%m/%Y') as datum_valuta,
                proc_prov_cela, provizija_proc, iznos_provizija,
                TO_CHAR(datum_zadol, '%d/%m/%Y') as datum_zadol,
                TO_CHAR(datum_valuta, '%d/%m/%Y') datum_valuta,
                vk_prov, '' as vrakanje, '' as datum_storniranje, '' as datum_kraj,
                '' as razlog_kraj, TO_CHAR(datum_ponuda, '%d/%m/%Y') datum_ponuda,
                TO_CHAR(skadenca_datum_do, '%d/%m/%Y') skadenca_datum_do,
                dogovoruvac_id, osigurenik_id, status, broker_id, broker_name
                FROM appuser.provizija_client_sms
                WHERE YEAR(pap_datumod) = {year}
                  AND MONTH(pap_datumod) = {month}
                  AND broker = {broker}
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])

            headers = [
                "Broj ponude", "BrojPolise", "Datum pocetka", "Doba osiguranja",
                "Godisnja premija", "Ugovarac", "mat broj", "Osiguranik", "Šifra produkta",
                "Dinamika placanja", "Način uplate", "iznos Rate", "Broj dospelih rata",
                "Dospelo за наплата", "Placeno", "broj rate", "Premija placena do",
                "Ukupna % provizije", "Presmetana % provizije", "provizija",
                "period od", "period do", "isplaćена provizија Ukupно", "za vraćanje",
                "datum storniranja", "Datum kraja", "Razlog kraja", "DatumUgovaranja",
                "Datum isteka", "SifraUgovaraca", "SifraOsiguranika", "Status",
                "SifraSaradnika", "SaradnikProdukcija"
            ]
            if len(headers) == df.shape[1]:
                df.columns = headers
            else:
                print(f"⚠️ Header mismatch for broker {broker}")

            # Save Excel to disk
            file_path = f"{base_dir}/broker_{broker}.xlsx"
            df.to_excel(file_path, index=False)

            # Try formatting the Excel
            try:
                process_broker_excel(file_path)
                print(f"Excel processed successfully for broker {broker}")

            except Exception as e:
                print(f"Excel processing error for broker {broker}: {e}")

            print(f"Excel saved: {file_path}")


        else:
            sql = f"""
                SELECT broker_name, polisabroj, ponuda_broj,trim(dogovoruvac)dogovoruvac ,dogovoruvac_edb,
                trim(dogovoruvac_adresa) dogovoruvac_adresa,
            trim(dogovoruvac_grad)dogovoruvac_grad ,trim(osigurenik)osigurenik , klasa,br_rati,rata,
            TO_CHAR(datum_napl, '%d/%m/%Y') as datum_napl,
            TO_CHAR(datum_zadol, '%d/%m/%Y') as datum_zadol,TO_CHAR(datum_valuta, '%d/%m/%Y') as datum_valuta,
            koja_godina,osig_suma,premija_zivot,vkupna_premija,provizija_proc,prov_rata,
            premija_nezgoda, 0 prov_rata_nezgoda,naplata,naplata_den,aneks, TO_CHAR(skadenca_datum_od, '%d/%m/%Y') as skadenca_datum_od
            , period_osig, TO_CHAR(skadenca_datum_do, '%d/%m/%Y') as skadenca_datum_do
                FROM vesna.provizija_client
                WHERE YEAR(pap_datumod) = {year}
                AND MONTH(pap_datumod) = {month}
                AND broker = {broker}
                and prov_rata<>0
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])

            headers = [
                "Брокер","Полиса бр.", "Понуда број", "Договорувач", "Договорувач ЕДБ",
                "Адреса", "Град", "Осигуреник", "Класа", "Број на рати", "Рата",
                 "Датум наплата", "Датум задолжување",
                "Датум валута", "Година", "Осигурена сума", "Премија живот",
                "Вкупна премија", "Провизија %", "Провизија рата", "Дополнителна премија",
                "Пров. рата дополн.", "Наплата", "Наплата ден", "Анекс", "Скаденца од",
                "Период осиг", "Скаденца до"
            ]

        # Assign headers
            if len(headers) == df.shape[1]:
                df.columns = headers
            else:
                print(f"⚠️ Header mismatch for broker {broker}")

            # Save Excel to disk
            file_path = f"{base_dir}/broker_{broker}.xlsx"
            df.to_excel(file_path, index=False)

            # Try formatting the Excel
            try:
                format_provision_excel(
                    file_path=file_path,
                    sheet_name="Sheet1",   # или името на твојот sheet
                    prov_col="T",
                    label_col="S",
                    kurs=vrati_kurs(mesec=month, godina=year),              # курс од vrati_kurs()
                    kurs_cell="X1"         # скриена ќелија
                )
                print(f"Excel formatted successfully for broker {broker}")
            except Exception as e:
                print(f"Excel formatting error for broker {broker}: {e}")

            print(f"Excel saved: {file_path}")

    cursor.close()
    conn.close()

    return {
        "success": True,
        "message": f"✔ Excel files generated in {base_dir}"
    }


def create_encrypted_zip_broker(df: pd.DataFrame, password: str, filename="report.xlsx"):
    """
    Create encrypted ZIP in memory using the new format_broker_excel_in_memory().
    Returns BytesIO with encrypted ZIP.
    """

    # 1️⃣ Generate raw Excel in memory
    excel_stream = io.BytesIO()
    df.to_excel(excel_stream, index=False, engine="openpyxl")
    excel_stream.seek(0)

    # 2️⃣ Apply full broker formatting
    try:
        excel_stream = format_broker_excel_in_memory(excel_stream)
    except Exception as e:
        print("⚠️ Excel formatting failed:", e)

    # 3️⃣ Create encrypted ZIP file in memory
    zip_stream = io.BytesIO()

    with pyzipper.AESZipFile(
        zip_stream,
        'w',
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(password.encode("utf-8"))
        zf.writestr(filename, excel_stream.getvalue())

    zip_stream.seek(0)
    return zip_stream





import requests
import socket
import platform
import jaydebeapi
import platform,sys
import math
import os 
from os.path import basename
import locale
import routers.Connection  as Connection # absolute import
import re
from datetime import datetime
from typing import Optional


# Function to get local machine's IP address
def get_ip_address():
    try:
        return requests.get("https://api64.ipify.org?format=json").json()["ip"]
    except Exception as e:
        print("Could not get IP address:", e)
        return None

# Get the current IP address

current_ip = get_ip_address()
print("Current IP Address:", current_ip)

# Define user credentials based on IP (Example mapping)
ip_credentials = {
    "192.168.1.100": {"username": "User1", "password": "Pass1"},
    "192.168.1.101": {"username": "User2", "password": "Pass2"},
    "62.162.114.68": {"username": "CFjLdHb1", "password": "mf4Kb1tp"}  # Replace with actual external IP
}

credentials = ip_credentials.get(current_ip, {"username": "default_user", "password": "default_pass"})
url = "https://web2sms.akton.net/rest/send_sms"

import re
from datetime import datetime
import requests

def prebSMS(selected_option):
    # Set default credentials if IP is not mapped
    sql = f"""
    select  first 1  client_id, trim(client_naziv) client_naziv, 
    vrati_client_telefon(par_clientid), vrati_valutaid_polisa(os_polisaid) valutaid, 
    sum(iznos) - sum(naplata) dolg 
    from report_fakturi 
    where data_faktura < today 
    and dogovoruvac_prav_fiz = 'F'
    group by 1, 2, 3, 4
    having sum(iznos) - sum(naplata) > 1
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Грешка - нема врска со база")
        return OK, 0.0, "Грешка - нема врска со база"

    # Execute SQL query and fetch results
    results.execute(sql)
    podatoci = []

    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    if not podatoci:
        return True, [], "Нема податоци за испраќање"

    sent_count = 0

    for row in podatoci:
        client_id, client_naziv, phone_number, valutaid, dolg = row

        # Test phone number for debugging
        phone_number = "071-297860"
        #print(f"Testing with phone number: {phone_number}")

        # Skip if the phone number is empty or None
        if not phone_number:
            continue
        
        # Clean and format phone number
        cleaned_number = re.sub(r'\D', '', phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]

        # Create a personalized message
        if valutaid == 1:
            valuta = "EUR"
            if dolg < 2:
                continue
        else:
            valuta = "ден"
            if dolg < 100:
                continue

        today_date = datetime.today().strftime("%d.%m.%Y")
        message = (
            f"Почитуван/а {client_naziv}, вашиот доспеан долг кон Sigal Life со состојба на {today_date} изнесува {dolg} {valuta}. Ве молиме да ја подмирите премијата."
        )

        # SMS API parameters
        params = {
            "from": "SigalLife",
            "to": cleaned_number.strip(),
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"]
        }

        # Send GET request
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                sent_count += 1  # Increase counter only on successful response
            print(f"Sent to {cleaned_number}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Failed to send to {cleaned_number}: {e}")

    # Return message with SMS count
    return True, podatoci, f"Испратени се {sent_count} СМС пораки"

def scheduled_prebSMSPromenaIme():
    return prebSMSPromenaIme(None)
def scheduled_prebSMSRodenden():
    # ако твојата функција за роденден има параметар, стави None
    return prebSMSRodenden(None)



def log_sms_audit(
    *,
    job_id: str,
    recipient: str,
    sender: str,
    message: str,
    http_status: Optional[int],
    provider_resp: Optional[str],
    status: str,
    error_message: Optional[str],
):
    results, OK = Connection.OSISinit()
    if not OK:
        print("[AUDIT][DB] ❌ No DB connection")
        return

    cur = results
    try:
        sql = """
            INSERT INTO sms_audit_log
                (job_id, recipient, sender, message, http_status, provider_resp, status, error_message, created_at)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, CURRENT YEAR TO SECOND)
        """

        cur.execute(sql, (
            job_id,
            recipient,
            sender,
            message,
            http_status,
            (provider_resp or "")[:3500],
            status,
            (error_message or "")[:1900],
        ))

        try:
            cur.connection.commit()
        except Exception:
            pass

    except Exception as e:
        print("[AUDIT][DB] ❌ Insert failed:", repr(e))



def prebSMSPromenaIme(selected_option):
    sql = """
    SELECT first 1 LOWER(TRIM(telefon)) AS telefon
   -- SELECT DISTINCT LOWER(TRIM(telefon)) AS telefon
    FROM (
        SELECT c.telefon AS telefon
        FROM os_polisa a
        JOIN os_ponuda b ON a.os_ponudaid = b.os_ponudaid
        JOIN par_client c ON b.dogovoruvac_par_client = c.par_clientid
        WHERE b.par_statusid IN (17,18)
          AND a.polisa_pod_broj = vratipodbrojpolisa(a.polisa_broj, b.os_produktid)
          AND c.client_tip_pf = 'F'
          AND NVL(edb,'') <> ''
          AND NVL(telefon,'') <> ''

        UNION

        SELECT c.telefon AS telefon
        FROM os_polisa a
        JOIN os_ponuda b ON a.os_ponudaid = b.os_ponudaid
        JOIN par_client c ON b.osigurenik_par_client = c.par_clientid
        WHERE b.par_statusid IN (17,18)
          AND a.polisa_pod_broj = vratipodbrojpolisa(a.polisa_broj, b.os_produktid)
          AND c.client_tip_pf = 'F'
          AND NVL(edb,'') <> ''
          AND NVL(telefon,'') <> ''
    ) t
    WHERE LOWER(TRIM(telefon)) NOT IN (SELECT recipient FROM sms_audit_log)
    ORDER BY 1
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Грешка - нема врска со база")
        return OK, 0.0, "Грешка - нема врска со база"

    results.execute(sql)
    podatoci = []
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    if not podatoci:
        return True, [], "Нема податоци за испраќање"

    sent_count = 0

    # ако имаш job_id однадвор - стави го тој; ако не, направи еден
    job_id = f"SMS_PROMENA_IME_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    message = (
        "Pocituvani, Ve informirame deka Drustvoto za osiguruvanje UNIQA LIFE izvrsi promena na naziv "
        "i vo idnina ke prodolzi da raboti pod imeto SIGAL LIFE INSURANCE GROUP. Vi blagodarime na doverbata."
    )

    for row in podatoci:
        phone_number = row[0]  # ✅ само 1 колона

        # ⚠️ ТЕСТ: тргни го ова во продукција
        phone_number = "071-297860"

        if not phone_number:
            continue

        cleaned_number = re.sub(r"\D", "", phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]

        params = {
            "from": "SigalLife",
            "to": cleaned_number.strip(),
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"]
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            ok = (response.status_code == 200)
            if ok:
                sent_count += 1

            print(f"Sent to {cleaned_number}: {response.status_code} - {response.text}")

            # ✅ log to DB (success or fail)
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number.strip(),
                sender=params["from"],
                message=message,
                http_status=response.status_code,
                provider_resp=response.text,
                status="SENT" if ok else "FAILED",
                error_message=None if ok else f"HTTP {response.status_code}"
            )

        except Exception as e:
            print(f"Failed to send to {cleaned_number}: {e}")

            # ✅ log exception to DB
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number.strip(),
                sender=params["from"],
                message=message,
                http_status=None,
                provider_resp=None,
                status="FAILED",
                error_message=str(e),
            )

    return True, podatoci, f"Испратени се {sent_count} СМС пораки"

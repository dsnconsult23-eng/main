import requests
import socket
import platform
import jaydebeapi
import platform,sys
import math
import os 
import json
import tempfile
import uuid
from os.path import basename
import locale
import routers.Connection  as Connection # absolute import
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse, JSONResponse
from auth.role_utils import has_any_role
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)


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

# --- "Dospeana premija" SMS (Tip A) — pilot vo test rezim ---
# Dodeka e True, realnata SMS se prakja do SMS_DOSPEANA_TEST_PHONE (ne do klienta),
# no vo sms_audit_log se zapisuva REALNIOT telefon na klienta (recipient) za da
# moze da se provери koj ЌE dobie poraka koga ke se prejde vo live rezim.
SMS_DOSPEANA_TEST_MODE = os.environ.get("SMS_DOSPEANA_TEST_MODE", "true").strip().lower() in ("1", "true", "yes")
SMS_DOSPEANA_TEST_PHONE = os.environ.get("SMS_DOSPEANA_TEST_PHONE", "38971297860").strip()
SMS_DOSPEANA_MIN_EUR = 5.0
SMS_DOSPEANA_MIN_MKD = 300.0


def _is_eur_currency(valutaid) -> bool:
    """Support both the legacy currency code (1) and par_valuta EUR id (363)."""
    return str(valutaid or "").strip().upper() in {"1", "363", "EUR"}


def _dpp_meets_sms_limit(valutaid, dolg) -> bool:
    try:
        amount = float(dolg or 0)
    except (TypeError, ValueError):
        return False
    minimum = SMS_DOSPEANA_MIN_EUR if _is_eur_currency(valutaid) else SMS_DOSPEANA_MIN_MKD
    return amount >= minimum

# --- "Riziko kredit" SMS (Tip B) - banka klienti so dolg, na denot na dospevanje ---
# Ist paten kako Tip A: dodeka e True, realnata SMS se prakja do SMS_RIZIKO_TEST_PHONE,
# no vo sms_audit_log se zapisuva REALNIOT telefon na klientot.
SMS_RIZIKO_TEST_MODE = os.environ.get("SMS_RIZIKO_TEST_MODE", "true").strip().lower() in ("1", "true", "yes")
SMS_RIZIKO_TEST_PHONE = os.environ.get("SMS_RIZIKO_TEST_PHONE", "38971297860").strip()

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
        if _is_eur_currency(valutaid):
            valuta = "EUR"
        else:
            valuta = "ден"
        if not _dpp_meets_sms_limit(valutaid, dolg):
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


def prebSMSRodenden(selected_option):
    sql = """
    SELECT
        c.par_clientid,
        TRIM(c.desc) AS client_naziv,
        TRIM(c.telefon) AS telefon
    FROM par_client c
    where c.par_statusid in (1,3)
      AND c.client_tip_pf = 'F'
      AND c.datumraganje IS NOT NULL
      AND NVL(c.telefon, '') <> ''
      AND DAY(c.datumraganje) = DAY(TODAY)
      AND MONTH(c.datumraganje) = MONTH(TODAY)

    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    results.execute(sql)
    podatoci = []
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    if not podatoci:
        return True, [], "Nema podatoci za isprakjanje"

    sent_count = 0
    seen_numbers = set()
    job_id = f"SMS_RODENDEN_{datetime.now().strftime('%Y%m%d')}"

    for row in podatoci:
        _client_id, client_naziv, phone_number = row

        if not phone_number:
            continue

        cleaned_number = re.sub(r"\D", "", phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]

        cleaned_number = cleaned_number.strip()
        if not cleaned_number or cleaned_number in seen_numbers:
            continue
        seen_numbers.add(cleaned_number)

        name = (client_naziv or "").strip()
        message = (
            f"Pocituvan/a, SIGAL LIFE Vi posakuva srekjen rodenden, dobro zdravje, "
            "srekja i mnogu uspesi. Vi blagodarime za doverbata."
        )

        params = {
            "from": "SigalLife",
            "to": cleaned_number,
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"]
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            ok = response.status_code == 200
            if ok:
                sent_count += 1

            print(f"Birthday SMS to {cleaned_number}: {response.status_code} - {response.text}")
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number,
                sender=params["from"],
                message=message,
                http_status=response.status_code,
                provider_resp=response.text,
                status="SENT" if ok else "FAILED",
                error_message=None if ok else f"HTTP {response.status_code}",
            )

        except Exception as e:
            print(f"Birthday SMS failed to {cleaned_number}: {e}")
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number,
                sender=params["from"],
                message=message,
                http_status=None,
                provider_resp=None,
                status="FAILED",
                error_message=str(e),
            )

    return True, podatoci, f"Isprateni se {sent_count} SMS poraki za rodenden"


def scheduled_prebSMSRodenden():
    # ако твојата функција за роденден има параметар, стави None
    return prebSMSRodenden(None)


# ------------------------------------------------------------------
# "Dospeana premija" SMS — Tip A (site klienti osven banka i Iute 40/).
# Se prakja na 17-ti vo mesecot; ako 17-ti padne vo sabota/nedela,
# se pomestuva na najbliskiot raboten den (ponedelnik).
# ------------------------------------------------------------------
def _dospeana_premija_target_day(year: int, month: int) -> "datetime":
    from calendar import monthrange
    from datetime import timedelta
    day17 = datetime(year, month, 17)
    if day17.weekday() == 5:      # sabota
        day17 += timedelta(days=2)
    elif day17.weekday() == 6:    # nedela
        day17 += timedelta(days=1)
    return day17


# ------------------------------------------------------------------
# Sindzir na "polisa zamena" (originalna <-> zamenska polisa, moze 3+ vo sindzir).
# Ista logika kako _resolve_polisa_group vo report_fakturi.py — se koristi za
# da se sobere dolgot na EDNA polisa preku site nejzini istoriski zameni, i za
# da se opredeli POSLEDNATA (tekovna) polisa vo sindzirot, koja se koristi za
# SMS porakata i za dedup, namesto stara/zamenata polisa.
# ------------------------------------------------------------------
def _resolve_polisa_zamena_group(cursor, polisa_broj: str) -> list:
    found = {polisa_broj.strip()}
    queue = list(found)
    while queue:
        pb = queue.pop(0)
        cursor.execute(
            "SELECT TRIM(polisa_zamena) FROM viki.os_polisa "
            "WHERE TRIM(polisa_broj_cel) = ? AND polisa_zamena IS NOT NULL",
            [pb]
        )
        for row in cursor.fetchall():
            v = (row[0] or "").strip()
            if v and v not in found:
                found.add(v)
                queue.append(v)
        cursor.execute(
            "SELECT TRIM(polisa_broj_cel) FROM viki.os_polisa "
            "WHERE TRIM(polisa_zamena) = ?",
            [pb]
        )
        for row in cursor.fetchall():
            v = (row[0] or "").strip()
            if v and v not in found:
                found.add(v)
                queue.append(v)
    return sorted(found)


def _current_polisa_in_group(cursor, group: list) -> str:
    """
    Poslednata (tekovna) polisa vo sindzirot e onaa koja NIKOJ drug clen od
    sindzirot ne ja sочituva kako svoja polisa_zamena (t.e. nikoj ne ja
    "zamenil" so ponatamosna polisa — таа е krajniot/najnov clen).
    """
    if len(group) == 1:
        return group[0]
    ph = ", ".join(["?" for _ in group])
    cursor.execute(
        f"SELECT DISTINCT TRIM(polisa_broj_cel), polisa_zamena FROM viki.os_polisa "
        f"WHERE TRIM(polisa_broj_cel) IN ({ph})",
        group
    )
    has_forward = set()
    for pb, zamena in cursor.fetchall():
        z = (zamena or "").strip() if zamena else ""
        if z:
            has_forward.add((pb or "").strip())
    candidates = [g for g in group if g not in has_forward]
    return sorted(candidates)[-1] if candidates else sorted(group)[-1]


def _merge_dolg_po_polisa_zamena(cursor, podatoci: list, has_valuta: bool) -> list:
    """
    Gi zdruzuva redovite po sindzir na polisa_zamena — dolgot na site polisi
    vo ist sindzir se sobira pod POSLEDNATA (tekovna) polisa vo sindzirot.

    podatoci: lista od (polisa_broj, telefon, [valutaid,] dolg) — valutaid samo
              ako has_valuta=True (Tip A); Tip B (Riziko kredit) nema valuta.
    Vrakja lista vo istиот format, но zdruzena po tekovna polisa.
    """
    # Load the complete replacement graph in batches. The old implementation
    # executed 2-3 queries PER policy (N+1), which took close to an hour for a
    # large Tip A list.
    initial_policies = {
        str(row[0]).strip() for row in podatoci if row and row[0]
    }
    adjacency = {policy: set() for policy in initial_policies}
    has_forward = set()
    pending = set(initial_policies)
    queried = set()
    batch_size = 200

    while pending:
        frontier = list(pending - queried)
        if not frontier:
            break
        pending.clear()
        for offset in range(0, len(frontier), batch_size):
            batch = frontier[offset:offset + batch_size]
            placeholders = ",".join(["?"] * len(batch))
            cursor.execute(
                f"SELECT DISTINCT TRIM(polisa_broj_cel), TRIM(polisa_zamena) "
                f"FROM viki.os_polisa "
                f"WHERE polisa_broj_cel IN ({placeholders}) "
                f"OR polisa_zamena IN ({placeholders})",
                batch + batch,
            )
            for policy, replacement in cursor.fetchall():
                policy = (policy or "").strip()
                replacement = (replacement or "").strip()
                if not policy:
                    continue
                adjacency.setdefault(policy, set())
                if replacement:
                    adjacency.setdefault(replacement, set())
                    adjacency[policy].add(replacement)
                    adjacency[replacement].add(policy)
                    has_forward.add(policy)
                    if replacement not in queried:
                        pending.add(replacement)
                if policy not in queried:
                    pending.add(policy)
        queried.update(frontier)

    current_cache = {}
    for policy in initial_policies:
        if policy in current_cache:
            continue
        component = set()
        stack = [policy]
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(adjacency.get(node, ()))
        candidates = sorted(node for node in component if node not in has_forward)
        current = candidates[-1] if candidates else sorted(component)[-1]
        for node in component:
            current_cache[node] = current

    merged = {}
    for row in podatoci:
        if has_valuta:
            polisa_broj, phone_number, valutaid, dolg = row
        else:
            polisa_broj, phone_number, dolg = row
            valutaid = None
        if not polisa_broj:
            continue
        polisa_broj = polisa_broj.strip()

        current = current_cache.get(polisa_broj, polisa_broj)

        entry = merged.setdefault(current, {"telefon": None, "valutaid": valutaid, "dolg": 0.0})
        entry["dolg"] += float(dolg or 0)
        if not entry["telefon"] and phone_number:
            entry["telefon"] = phone_number
        if entry["valutaid"] is None:
            entry["valutaid"] = valutaid

    if has_valuta:
        return [(pb, e["telefon"], e["valutaid"], e["dolg"]) for pb, e in merged.items()]
    return [(pb, e["telefon"], e["dolg"]) for pb, e in merged.items()]


# ------------------------------------------------------------------
# Statusi na polisa (kako vo vw_pregled2: polisa status, valuta, tip
# na produkt, datum status, polisa sostojba), no preku direktni
# join-ovi/UDF-ovi namesto celiot (bavniot) view — status se zema od
# POSLEDNATA ponuda (maxpodbroj_datum), ist paттern kako vo
# kontrola_polisi.py.
# ------------------------------------------------------------------
def _fetch_polisa_statusi_za_izvoz(cur, polisa_brojevi: list) -> dict:
    polisa_brojevi = list(dict.fromkeys(p.strip() for p in polisa_brojevi if p))
    if not polisa_brojevi:
        return {}

    statusi = {}
    # Smaller IN lists give Informix a substantially cheaper plan and avoid
    # driver/database parameter limits on large Tip A exports.
    for offset in range(0, len(polisa_brojevi), 200):
        batch = polisa_brojevi[offset:offset + 200]
        placeholders = ",".join(["?"] * len(batch))
        sql = f"""
        SELECT
            p.polisa_broj_cel,
            CASE WHEN o.par_polisa_statusid IS NULL THEN appuser.vrati_status(o.par_statusid)
                 ELSE appuser.vrati_polisa_status_desc(o.par_polisa_statusid) END AS polisa_status_desc,
            appuser.vrati_valuta(NVL(o.par_valutaid, pr.par_valutaid)) AS valuta,
            vesna.vrati_tipprodukt(pr.os_tipproduktid) AS tip_produkt,
            CASE WHEN p.status_polisa = 'K' THEN 'Активна' ELSE 'Неактивна' END AS polisa_status,
            CASE WHEN o.datum_prekin IS NOT NULL AND o.par_statusid = 20 THEN o.datum_prekin
                 ELSE DATE(p.datum_polisa) END AS datum_status,
            appuser.vrati_status(o.par_statusid) AS polisa_sosotojba
        FROM os_polisa p
        JOIN os_ponuda o  ON o.os_ponudaid  = p.os_ponudaid
        JOIN os_produkt pr ON pr.os_produktid = o.os_produktid
        WHERE p.polisa_broj_cel IN ({placeholders})
          AND o.ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, p.polisa_broj, o.os_produktid, TODAY)
        """
        cur.execute(sql, batch)
        for r in cur.fetchall():
            polisa_broj = (r[0] or "").strip()
            statusi[polisa_broj] = {
                "polisa_status_desc": r[1],
                "valuta_desc": r[2],
                "tip_produkt": r[3],
                "polisa_status": r[4],
                "datum_status": str(r[5]) if r[5] is not None else "",
                "polisa_sosotojba": r[6],
            }
    return statusi


_PRAZEN_STATUS = {
    "polisa_status_desc": "", "valuta_desc": "", "tip_produkt": "",
    "polisa_status": "", "datum_status": "", "polisa_sosotojba": "",
}


_TIP_A_TERMINAL_STATUS_WORDS = (
    "ОТКУП", "ДОЖИВЕАН", "ИСПЛАТЕН", "ПРЕКИН", "СТОРНО", "РАСКИН", "ПОНИШТ",
)


def _tip_a_has_eligible_final_status(status: dict) -> bool:
    """Tip A is allowed only for a currently active, non-terminal policy."""
    if str(status.get("polisa_status") or "").strip().upper() != "АКТИВНА":
        return False
    descriptions = " ".join([
        str(status.get("polisa_status_desc") or ""),
        str(status.get("polisa_sosotojba") or ""),
    ]).upper()
    return not any(word in descriptions for word in _TIP_A_TERMINAL_STATUS_WORDS)


# ------------------------------------------------------------------
# Read-only "pregled" funkcii za Excel izvoz (ne praka SMS, ne pisuva
# vo sms_audit_log) — istite SELECT-i kako prebSMSDospeanaPremija /
# prebSMSRizikoKredit, samo za да se vidi listata na polisi koi bi
# dobile SMS.
# ------------------------------------------------------------------
def _query_dospeana_premija_za_izvoz():
    sql = """
    WITH base AS (
        SELECT
            x0.os_aneks_fakturaid,
            TRIM(x2.polisa_broj_cel) AS polisa_broj,
            x2.os_polisaid     AS os_polisaid,
            NVL(x0.iznos, 0)   AS iznos,
            x1.par_clientid,
            TRIM(pc.telefon)   AS telefon
        FROM viki.os_aneks_faktura x0
        JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
        JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
        JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
        JOIN par_client pc      ON pc.par_clientid = x1.par_clientid
        WHERE NVL(x0.f_rs, 'R') <> 'N'
          AND x1.os_zbiren_aneksid IS NULL
          AND x0.data_faktura <= TODAY
          AND pc.client_tip_pf = 'F'
          AND NVL(pc.telefon, '') <> ''
          AND NVL(x3.par_prod_kanalid, 0) <> 62
          AND x2.polisa_broj_cel NOT LIKE '40/%'
          AND EXISTS (
              SELECT 1 FROM viki.fin_stavka fg
              WHERE fg.os_aneks_fakturaid = x0.os_aneks_fakturaid
                AND fg.iznos_d IS NOT NULL
          )
    ),
    naplata AS (
        SELECT fs.os_aneks_fakturaid, SUM(NVL(fs.iznos_p, 0)) AS naplata
        FROM fin_stavka fs
        JOIN base b ON b.os_aneks_fakturaid = fs.os_aneks_fakturaid
        WHERE fs.sifra_zatvaranje IS NOT NULL
          AND fs.f_rs <> 'N'
        GROUP BY fs.os_aneks_fakturaid
    )
    SELECT
        b.polisa_broj,
        MAX(b.telefon) AS telefon,
        MAX(vrati_valutaid_polisa(b.os_polisaid)) AS valutaid,
        SUM(b.iznos - NVL(n.naplata, 0)) AS dolg
    FROM base b
    LEFT JOIN naplata n ON n.os_aneks_fakturaid = b.os_aneks_fakturaid
    GROUP BY b.polisa_broj
    HAVING SUM(b.iznos - NVL(n.naplata, 0)) > 0
    """

    cur, ok = Connection.OSISinit()
    if not ok:
        return [], "Нема конекција кон базата."

    cur.execute(sql)
    podatoci = []
    while True:
        row = cur.fetchone()
        if not row:
            break
        podatoci.append(row)
    cur.close()

    if not podatoci:
        return [], None

    try:
        merge_cur, merge_ok = Connection.OSISinit()
        if merge_ok:
            try:
                podatoci = _merge_dolg_po_polisa_zamena(merge_cur, podatoci, has_valuta=True)
            finally:
                merge_cur.close()
    except Exception as e:
        print(f"[DPP-izvoz] Polisa-zamena merge failed, continuing bez merge: {e}")

    # Tip A prikazuva/praka samo dolg od najmalku 5 EUR ili 300 MKD.
    podatoci = [r for r in podatoci if _dpp_meets_sms_limit(r[2], r[3])]

    statusi = {}
    try:
        status_cur, status_ok = Connection.OSISinit()
        if status_ok:
            try:
                statusi = _fetch_polisa_statusi_za_izvoz(status_cur, [r[0] for r in podatoci])
            finally:
                status_cur.close()
    except Exception as e:
        return [], f"Не може да се провери конечниот статус на полисите: {e}"

    rows = []
    for polisa_broj, telefon, valutaid, dolg in podatoci:
        st = statusi.get((polisa_broj or "").strip(), _PRAZEN_STATUS)
        if not _tip_a_has_eligible_final_status(st):
            continue
        rows.append({
            "polisa_broj": polisa_broj,
            "telefon": telefon,
            "valuta": "EUR" if _is_eur_currency(valutaid) else "den",
            "dolg": float(dolg or 0),
            **st,
        })
    return rows, None


def _query_riziko_kredit_za_izvoz():
    sql = """
    WITH trigger_faktura AS (
        SELECT DISTINCT TRIM(x2.polisa_broj_cel) AS polisa_broj
        FROM viki.os_aneks_faktura x0
        JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
        JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
        JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
        JOIN par_client pc      ON pc.par_clientid = x1.par_clientid
        WHERE NVL(x0.f_rs, 'R') <> 'N'
          AND x1.os_zbiren_aneksid IS NULL
          AND x0.data_faktura = TODAY
          AND pc.client_tip_pf = 'F'
          AND NVL(pc.telefon, '') <> ''
          AND NVL(x3.par_prod_kanalid, 0) = 62
          AND (x2.polisa_broj_cel LIKE '27/%' OR x2.polisa_broj_cel LIKE '25/%')
    ),
    base AS (
        SELECT
            x0.os_aneks_fakturaid,
            TRIM(x2.polisa_broj_cel) AS polisa_broj,
            NVL(x0.iznos, 0)   AS iznos,
            x1.par_clientid,
            TRIM(pc.telefon)   AS telefon
        FROM viki.os_aneks_faktura x0
        JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
        JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
        JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
        JOIN par_client pc      ON pc.par_clientid = x1.par_clientid
        JOIN trigger_faktura tf ON tf.polisa_broj  = TRIM(x2.polisa_broj_cel)
        WHERE NVL(x0.f_rs, 'R') <> 'N'
          AND x1.os_zbiren_aneksid IS NULL
          AND x0.data_faktura <= TODAY
          AND pc.client_tip_pf = 'F'
          AND NVL(pc.telefon, '') <> ''
          AND NVL(x3.par_prod_kanalid, 0) = 62
          AND EXISTS (
              SELECT 1 FROM viki.fin_stavka fg
              WHERE fg.os_aneks_fakturaid = x0.os_aneks_fakturaid
                AND fg.iznos_d IS NOT NULL
          )
    ),
    naplata AS (
        SELECT fs.os_aneks_fakturaid, SUM(NVL(fs.iznos_p, 0)) AS naplata
        FROM fin_stavka fs
        JOIN base b ON b.os_aneks_fakturaid = fs.os_aneks_fakturaid
        WHERE fs.sifra_zatvaranje IS NOT NULL
          AND fs.f_rs <> 'N'
        GROUP BY fs.os_aneks_fakturaid
    )
    SELECT
        b.polisa_broj,
        MAX(b.telefon) AS telefon,
        SUM(b.iznos - NVL(n.naplata, 0)) AS dolg
    FROM base b
    LEFT JOIN naplata n ON n.os_aneks_fakturaid = b.os_aneks_fakturaid
    GROUP BY b.polisa_broj
    HAVING SUM(b.iznos - NVL(n.naplata, 0)) > 0
    """

    cur, ok = Connection.OSISinit()
    if not ok:
        return [], "Нема конекција кон базата."

    cur.execute(sql)
    podatoci = []
    while True:
        row = cur.fetchone()
        if not row:
            break
        podatoci.append(row)
    cur.close()

    if not podatoci:
        return [], None

    try:
        merge_cur, merge_ok = Connection.OSISinit()
        if merge_ok:
            try:
                podatoci = _merge_dolg_po_polisa_zamena(merge_cur, podatoci, has_valuta=False)
            finally:
                merge_cur.close()
    except Exception as e:
        print(f"[RK-izvoz] Polisa-zamena merge failed, continuing bez merge: {e}")

    statusi = {}
    try:
        status_cur, status_ok = Connection.OSISinit()
        if status_ok:
            try:
                statusi = _fetch_polisa_statusi_za_izvoz(status_cur, [r[0] for r in podatoci])
            finally:
                status_cur.close()
    except Exception as e:
        print(f"[RK-izvoz] Fetch na statusi failed, continuing bez statusi: {e}")

    rows = []
    for polisa_broj, telefon, dolg in podatoci:
        st = statusi.get((polisa_broj or "").strip(), _PRAZEN_STATUS)
        rows.append({
            "polisa_broj": polisa_broj,
            "telefon": telefon,
            "dolg": float(dolg or 0),
            **st,
        })
    return rows, None


def prebSMSDospeanaPremija(selected_option=None):
    """
    Edna SMS po polisa za site polisi so dospeana (nenaplatena) premija,
    isklucuvajki: kanal banka (par_prod_kanalid=62) i polisi so prefiks '40/' (Iute).

    Dedup: eden pat po polisa/mesec preku job_id vo sms_audit_log
    (job_id = DPP_{polisa_broj}_{YYYYMM}), ne preku telefonskiot broj —
    bidejki eden klient moze da ima poveke dospeani polisi vo istiot mesec
    i za sekoja treba posebna poraka.

    NAPOMENA (pretpostavki koi treba da se potvrdat pred da se pushti live):
      - samo fizicki lica (client_tip_pf='F'), isto kako i drugite SMS funkcii
      - valuta (EUR/den) se opredeluva po polisa preku vrati_valutaid_polisa(os_polisaid),
        isto kako vo prebSMS()
    """
    # Vo test rezim dedup-ot e DNEVEN (ne mesecen), za istata polisa da moze da
    # dobie SMS sekoj den dodeka se testira; vo produkcija ostanuva mesecen.
    dedup_tag = datetime.today().strftime("%Y%m%d") if SMS_DOSPEANA_TEST_MODE else datetime.today().strftime("%Y%m")

    sql = """
    WITH base AS (
        SELECT
            x0.os_aneks_fakturaid,
            TRIM(x2.polisa_broj_cel) AS polisa_broj,
            x2.os_polisaid     AS os_polisaid,
            NVL(x0.iznos, 0)   AS iznos,
            x1.par_clientid,
            TRIM(pc.telefon)   AS telefon
        FROM viki.os_aneks_faktura x0
        JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
        JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
        JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
        JOIN par_client pc      ON pc.par_clientid = x1.par_clientid
        WHERE NVL(x0.f_rs, 'R') <> 'N'
          AND x1.os_zbiren_aneksid IS NULL
          AND x0.data_faktura <= TODAY
          AND pc.client_tip_pf = 'F'
          AND NVL(pc.telefon, '') <> ''
          AND NVL(x3.par_prod_kanalid, 0) <> 62
          AND x2.polisa_broj_cel NOT LIKE '40/%'
          AND EXISTS (
              SELECT 1 FROM viki.fin_stavka fg
              WHERE fg.os_aneks_fakturaid = x0.os_aneks_fakturaid
                AND fg.iznos_d IS NOT NULL
          )
    ),
    naplata AS (
        SELECT fs.os_aneks_fakturaid, SUM(NVL(fs.iznos_p, 0)) AS naplata
        FROM fin_stavka fs
        JOIN base b ON b.os_aneks_fakturaid = fs.os_aneks_fakturaid
        WHERE fs.sifra_zatvaranje IS NOT NULL
          AND fs.f_rs <> 'N'
        GROUP BY fs.os_aneks_fakturaid
    )
    SELECT
        b.polisa_broj,
        MAX(b.telefon) AS telefon,
        MAX(vrati_valutaid_polisa(b.os_polisaid)) AS valutaid,
        SUM(b.iznos - NVL(n.naplata, 0)) AS dolg
    FROM base b
    LEFT JOIN naplata n ON n.os_aneks_fakturaid = b.os_aneks_fakturaid
    GROUP BY b.polisa_broj
    HAVING SUM(b.iznos - NVL(n.naplata, 0)) > 0
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    results.execute(sql)
    podatoci = []
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)
    results.close()

    if not podatoci:
        return True, [], "Nema polisi so dospeana premija"

    # Zdruzuvanje na dolg po sindzir na "polisa zamena" — SMS se prakja pod
    # POSLEDNATA (tekovna) polisa vo sindzirot, so sobran dolg od site nejzini
    # istoriski zameni.
    try:
        merge_cur, merge_ok = Connection.OSISinit()
        if merge_ok:
            try:
                podatoci = _merge_dolg_po_polisa_zamena(merge_cur, podatoci, has_valuta=True)
            finally:
                merge_cur.close()
    except Exception as e:
        print(f"[DPP] Polisa-zamena merge failed, continuing bez merge: {e}")

    # Po spojuvanjeto na zamenskite polisi, proveri ja KONECNATA polisa.
    # Fail-closed: bez potvrden aktiven status ne smee da se prati Tip A SMS.
    try:
        status_cur, status_ok = Connection.OSISinit()
        if not status_ok:
            return False, [], "Ne moze da se proveri konecniot status na polisite"
        try:
            final_statusi = _fetch_polisa_statusi_za_izvoz(
                status_cur, [row[0] for row in podatoci]
            )
        finally:
            status_cur.close()
        podatoci = [
            row for row in podatoci
            if _tip_a_has_eligible_final_status(
                final_statusi.get((row[0] or "").strip(), _PRAZEN_STATUS)
            )
        ]
    except Exception as e:
        print(f"[DPP] Final status check failed; SMS is not sent: {e}")
        return False, [], f"Ne moze da se proveri konecniot status na polisite: {e}"

    if not podatoci:
        return True, [], "Nema aktivni polisi so dospeana premija"

    # Dedup: site job_id-ovi za koi VEKE e isprateno ovoj mesec (eden query, ne po red).
    already_sent_job_ids = set()
    try:
        dedup_cur, dedup_ok = Connection.OSISinit()
        if dedup_ok:
            dedup_cur.execute(
                "SELECT job_id FROM sms_audit_log WHERE job_id LIKE ? AND status = 'SENT'",
                (f"DPP_%_{dedup_tag}",),
            )
            already_sent_job_ids = {r[0] for r in dedup_cur.fetchall()}
            dedup_cur.close()
    except Exception as e:
        print(f"[DPP] Dedup lookup failed, continuing without dedup: {e}")

    sent_count = 0

    for row in podatoci:
        polisa_broj, phone_number, valutaid, dolg = row
        if not phone_number or not polisa_broj:
            continue

        job_id = f"DPP_{polisa_broj}_{dedup_tag}"
        if job_id in already_sent_job_ids:
            continue

        if _is_eur_currency(valutaid):
            valuta = "EUR"
        else:
            valuta = "den"
        if not _dpp_meets_sms_limit(valutaid, dolg):
            continue

        cleaned_number = re.sub(r"\D", "", phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]
        cleaned_number = cleaned_number.strip()
        if not cleaned_number:
            continue

        iznos_str = f"{float(dolg):.2f}"
        message = (
            f"Pocituvani, Ve izvestuvame deka premijata za polisa {polisa_broj} "
            f"vo iznos od {iznos_str} {valuta} e dospeana. Uplata moze da izvrsite "
            f"I preku nasata web strana. Vi blagodarime"
        )

        send_to = SMS_DOSPEANA_TEST_PHONE #if SMS_DOSPEANA_TEST_MODE else cleaned_number

        params = {
            "from": "SigalLife",
            "to": send_to,
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"],
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            ok = response.status_code == 200
            if ok:
                sent_count += 1
            print(
                f"[DPP]{' [TEST MODE, klient=' + cleaned_number + ']' if SMS_DOSPEANA_TEST_MODE else ''} "
                f"polisa={polisa_broj} -> {send_to}: {response.status_code} - {response.text}"
            )
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number,  # realniot klient, za audit, i vo test rezim
                sender=params["from"],
                message=message,
                http_status=response.status_code,
                provider_resp=response.text,
                status="SENT" if ok else "FAILED",
                error_message=None if ok else f"HTTP {response.status_code}",
            )
        except Exception as e:
            print(f"[DPP] Failed to send for polisa {polisa_broj}: {e}")
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number,
                sender=params["from"],
                message=message,
                http_status=None,
                provider_resp=None,
                status="FAILED",
                error_message=str(e),
            )

    mode_note = " (TEST REZIM - site poraki isprateni na test broj)" if SMS_DOSPEANA_TEST_MODE else ""
    return True, podatoci, f"Isprateni se {sent_count} SMS poraki za dospeana premija{mode_note}"


def scheduled_prebSMSDospeanaPremija():
    if SMS_DOSPEANA_TEST_MODE:
        # Dodeka e vo test rezim - pushta sekoj den, bez ogranicuvanje na ciljniot den,
        # za polesno testiranje (site poraki i taka odat na SMS_DOSPEANA_TEST_PHONE).
        print("[DPP] TEST REZIM - preskoknuvam provera na ciljniot den, pushtam denes")
        return prebSMSDospeanaPremija(None)

    today = datetime.today()
    target_day = _dospeana_premija_target_day(today.year, today.month)
    if today.date() != target_day.date():
        print(f"[DPP] Skip - denes ({today.date()}) ne e ciljniot den ({target_day.date()})")
        return True, [], "Skip - ne e ciljniot den vo mesecot"
    return prebSMSDospeanaPremija(None)


# ------------------------------------------------------------------
# "Riziko kredit" SMS - Tip B (banka klienti so dolg, na denot na dospevanje).
# Identifikacija na "Riziko kredit" polisi: kanal banka (par_prod_kanalid=62)
# I polisa_broj_cel so prefiks '27/' ili '25/'.
# ------------------------------------------------------------------
def prebSMSRizikoKredit(selected_option=None):
    """
    Edna SMS po polisa za banka polisi "Riziko kredit" (kanal=62, prefiks 27/ ili 25/)
    cija fakura dospeva DENES i imaat nenaplaten dolg.

    Dedup: eden pat po polisa/den preku job_id vo sms_audit_log
    (job_id = RK_{polisa_broj}_{YYYYMMDD}).
    """
    day_tag = datetime.today().strftime("%Y%m%d")

    sql = """
    WITH trigger_faktura AS (
        -- Koi polisi imaat faktura shto dospeva DENES (ova samo go opredeluva
        -- KOJ polisi treba da dobijat SMS denes, ne go smeta dolgot).
        SELECT DISTINCT TRIM(x2.polisa_broj_cel) AS polisa_broj
        FROM viki.os_aneks_faktura x0
        JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
        JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
        JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
        JOIN par_client pc      ON pc.par_clientid = x1.par_clientid
        WHERE NVL(x0.f_rs, 'R') <> 'N'
          AND x1.os_zbiren_aneksid IS NULL
          AND x0.data_faktura = TODAY
          AND pc.client_tip_pf = 'F'
          AND NVL(pc.telefon, '') <> ''
          AND NVL(x3.par_prod_kanalid, 0) = 62
          AND (x2.polisa_broj_cel LIKE '27/%' OR x2.polisa_broj_cel LIKE '25/%')
    ),
    base AS (
        -- Za tie polisi, CELIOT nenaplaten dolg (site fakturi so data_faktura <= TODAY),
        -- ne samo denesnata faktura.
        SELECT
            x0.os_aneks_fakturaid,
            TRIM(x2.polisa_broj_cel) AS polisa_broj,
            NVL(x0.iznos, 0)   AS iznos,
            x1.par_clientid,
            TRIM(pc.telefon)   AS telefon
        FROM viki.os_aneks_faktura x0
        JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
        JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
        JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
        JOIN par_client pc      ON pc.par_clientid = x1.par_clientid
        JOIN trigger_faktura tf ON tf.polisa_broj  = TRIM(x2.polisa_broj_cel)
        WHERE NVL(x0.f_rs, 'R') <> 'N'
          AND x1.os_zbiren_aneksid IS NULL
          AND x0.data_faktura <= TODAY
          AND pc.client_tip_pf = 'F'
          AND NVL(pc.telefon, '') <> ''
          AND NVL(x3.par_prod_kanalid, 0) = 62
          AND EXISTS (
              SELECT 1 FROM viki.fin_stavka fg
              WHERE fg.os_aneks_fakturaid = x0.os_aneks_fakturaid
                AND fg.iznos_d IS NOT NULL
          )
    ),
    naplata AS (
        SELECT fs.os_aneks_fakturaid, SUM(NVL(fs.iznos_p, 0)) AS naplata
        FROM fin_stavka fs
        JOIN base b ON b.os_aneks_fakturaid = fs.os_aneks_fakturaid
        WHERE fs.sifra_zatvaranje IS NOT NULL
          AND fs.f_rs <> 'N'
        GROUP BY fs.os_aneks_fakturaid
    )
    SELECT
        b.polisa_broj,
        MAX(b.telefon) AS telefon,
        SUM(b.iznos - NVL(n.naplata, 0)) AS dolg
    FROM base b
    LEFT JOIN naplata n ON n.os_aneks_fakturaid = b.os_aneks_fakturaid
    GROUP BY b.polisa_broj
    HAVING SUM(b.iznos - NVL(n.naplata, 0)) > 0
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Greska - nema vrska so baza")
        return OK, 0.0, "Greska - nema vrska so baza"

    results.execute(sql)
    podatoci = []
    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)
    results.close()

    if not podatoci:
        return True, [], "Nema Riziko kredit polisi so dospevanje denes"

    # Zdruzuvanje na dolg po sindzir na "polisa zamena" — SMS se prakja pod
    # POSLEDNATA (tekovna) polisa vo sindzirot.
    try:
        merge_cur, merge_ok = Connection.OSISinit()
        if merge_ok:
            try:
                podatoci = _merge_dolg_po_polisa_zamena(merge_cur, podatoci, has_valuta=False)
            finally:
                merge_cur.close()
    except Exception as e:
        print(f"[RK] Polisa-zamena merge failed, continuing bez merge: {e}")

    already_sent_job_ids = set()
    try:
        dedup_cur, dedup_ok = Connection.OSISinit()
        if dedup_ok:
            dedup_cur.execute(
                "SELECT job_id FROM sms_audit_log WHERE job_id LIKE ? AND status = 'SENT'",
                (f"RK_%_{day_tag}",),
            )
            already_sent_job_ids = {r[0] for r in dedup_cur.fetchall()}
            dedup_cur.close()
    except Exception as e:
        print(f"[RK] Dedup lookup failed, continuing without dedup: {e}")

    sent_count = 0
    message = (
        "Pocituvani, Ve potsetuvame deka imate dospeani obvrski po polisa Riziko kredit, "
        "i potrebno e istite da gi podmirite vo tekot na denot. Vi blagodarime"
    )

    for row in podatoci:
        polisa_broj, phone_number, dolg = row
        if not phone_number or not polisa_broj:
            continue

        job_id = f"RK_{polisa_broj}_{day_tag}"
        if job_id in already_sent_job_ids:
            continue

        cleaned_number = re.sub(r"\D", "", phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]
        cleaned_number = cleaned_number.strip()
        if not cleaned_number:
            continue

        send_to = SMS_RIZIKO_TEST_PHONE #if SMS_RIZIKO_TEST_MODE else cleaned_number

        params = {
            "from": "SigalLife",
            "to": send_to,
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"],
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            ok = response.status_code == 200
            if ok:
                sent_count += 1
            print(
                f"[RK]{' [TEST MODE, klient=' + cleaned_number + ']' if SMS_RIZIKO_TEST_MODE else ''} "
                f"polisa={polisa_broj} -> {send_to}: {response.status_code} - {response.text}"
            )
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number,
                sender=params["from"],
                message=message,
                http_status=response.status_code,
                provider_resp=response.text,
                status="SENT" if ok else "FAILED",
                error_message=None if ok else f"HTTP {response.status_code}",
            )
        except Exception as e:
            print(f"[RK] Failed to send for polisa {polisa_broj}: {e}")
            log_sms_audit(
                job_id=job_id,
                recipient=cleaned_number,
                sender=params["from"],
                message=message,
                http_status=None,
                provider_resp=None,
                status="FAILED",
                error_message=str(e),
            )

    mode_note = " (TEST REZIM - site poraki isprateni na test broj)" if SMS_RIZIKO_TEST_MODE else ""
    return True, podatoci, f"Isprateni se {sent_count} SMS poraki za Riziko kredit{mode_note}"


def scheduled_prebSMSRizikoKredit():
    return prebSMSRizikoKredit(None)


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


# ------------------------------------------------------------------
# Strana za pregled na isprateni SMS poraki (sms_audit_log).
# ------------------------------------------------------------------
def _require_sms_log_role(request: Request):
    user = request.session.get("user")
    if not user:
        return None, RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, "admin", "sms_log"):
        raise HTTPException(status_code=403, detail="Немате пристап.")
    return user, None


@router.get("/sms-log")
def sms_log_page(
    request: Request,
    status: Optional[str] = None,
    job_id: Optional[str] = None,
    recipient: Optional[str] = None,
    limit: int = 200,
):
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect

    rows, error, safe_limit = _fetch_sms_log_rows(status, job_id, recipient, limit)

    return templates.TemplateResponse("sms_log.html", {
        "request": request,
        "user": user,
        "active": "sms_log",
        "rows": rows,
        "error": error,
        "filters": {
            "status": status or "",
            "job_id": job_id or "",
            "recipient": recipient or "",
            "limit": safe_limit,
        },
    })


def _fetch_sms_log_rows(status, job_id, recipient, limit):
    where = []
    params = []
    if status:
        where.append("status = ?")
        params.append(status)
    if job_id:
        where.append("job_id LIKE ?")
        params.append(f"%{job_id}%")
    if recipient:
        where.append("recipient LIKE ?")
        params.append(f"%{recipient}%")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    safe_limit = max(1, min(int(limit or 200), 1000))
    sql = f"""
        SELECT FIRST {safe_limit}
            job_id, recipient, sender, message, http_status, status, error_message, created_at
        FROM sms_audit_log
        {where_sql}
        ORDER BY created_at DESC
    """

    rows = []
    error = None
    try:
        cur, ok = Connection.OSISinit()
        if not ok:
            error = "Нема конекција кон базата."
        else:
            cur.execute(sql, params)
            for r in cur.fetchall():
                rows.append({
                    "job_id": r[0], "recipient": r[1], "sender": r[2], "message": r[3],
                    "http_status": r[4], "status": r[5], "error_message": r[6],
                    "created_at": str(r[7]) if r[7] is not None else "",
                })
            cur.close()
    except Exception as e:
        error = str(e)

    return rows, error, safe_limit


@router.get("/sms-log/excel")
def sms_log_excel(
    request: Request,
    status: Optional[str] = None,
    job_id: Optional[str] = None,
    recipient: Optional[str] = None,
    limit: int = 200,
):
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect

    rows, error, _ = _fetch_sms_log_rows(status, job_id, recipient, limit)
    if error:
        raise HTTPException(status_code=500, detail=error)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SMS log"

    headers = ["Датум/време", "Job ID", "Примач", "Испраќач", "Статус", "HTTP", "Порака", "Грешка"]
    ws.append(headers)
    hdr_fill = PatternFill("solid", fgColor="1A3A5C")
    hdr_font = Font(color="FFFFFF", bold=True, name="Calibri", size=10)
    for ci in range(1, len(headers) + 1):
        c = ws.cell(1, ci)
        c.fill = hdr_fill
        c.font = hdr_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    for r in rows:
        ws.append([
            r["created_at"], r["job_id"], r["recipient"], r["sender"],
            r["status"], r["http_status"], r["message"], r["error_message"],
        ])

    widths = [18, 26, 16, 14, 10, 8, 45, 30]
    for ci, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sms_log.xlsx"'},
    )


def _build_xlsx(sheet_title, headers, data_rows, col_widths=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title

    ws.append(headers)
    hdr_fill = PatternFill("solid", fgColor="1A3A5C")
    hdr_font = Font(color="FFFFFF", bold=True, name="Calibri", size=10)
    for ci in range(1, len(headers) + 1):
        c = ws.cell(1, ci)
        c.fill = hdr_fill
        c.font = hdr_font
        c.alignment = Alignment(horizontal="center", vertical="center")

    for row in data_rows:
        ws.append(row)

    if col_widths:
        for ci, w in enumerate(col_widths, start=1):
            ws.column_dimensions[chr(64 + ci)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _tip_a_job_paths(job_id: str):
    base = os.path.join(tempfile.gettempdir(), f"sms_tip_a_{job_id}")
    return base + ".json", base + ".xlsx"


def _validate_tip_a_job_id(job_id: str):
    if not re.fullmatch(r"[0-9a-f]{32}", job_id or ""):
        raise HTTPException(status_code=404, detail="Job-от не е пронајден.")


def _write_tip_a_job(job_id: str, status: str, message: str):
    status_path, _ = _tip_a_job_paths(job_id)
    temp_path = status_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump({"status": status, "message": message}, handle, ensure_ascii=False)
    os.replace(temp_path, status_path)


def _build_tip_a_export():
    rows, error = _query_dospeana_premija_za_izvoz()
    if error:
        raise RuntimeError(error)
    data_rows = [
        [
            r["polisa_broj"], r["telefon"], r["valuta"], r["dolg"],
            r.get("polisa_status_desc", ""), r.get("valuta_desc", ""), r.get("tip_produkt", ""),
            r.get("polisa_status", ""), r.get("datum_status", ""), r.get("polisa_sosotojba", ""),
        ]
        for r in rows
    ]
    return _build_xlsx(
        "Dospeana premija Tip A",
        [
            "Полиса број", "Телефон", "Валута", "Долг",
            "Полиса статус", "Валута", "Тип на продукт",
            "Полиса статус", "Датум статус", "Полиса состојба",
        ],
        data_rows,
        col_widths=[18, 16, 10, 14, 16, 10, 16, 16, 14, 16],
    )


def _run_tip_a_export_job(job_id: str):
    _, output_path = _tip_a_job_paths(job_id)
    try:
        _write_tip_a_job(job_id, "running", "Се подготвуваат полисите и Excel датотеката...")
        buf = _build_tip_a_export()
        with open(output_path, "wb") as handle:
            handle.write(buf.getvalue())
        _write_tip_a_job(job_id, "ready", "Excel датотеката е подготвена.")
    except Exception as exc:
        _write_tip_a_job(job_id, "error", str(exc))


@router.post("/sms-log/excel-tip-a/start")
def sms_log_excel_tip_a_start(request: Request, background_tasks: BackgroundTasks):
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect
    job_id = uuid.uuid4().hex
    _write_tip_a_job(job_id, "pending", "Excel извештајот е ставен во редица...")
    background_tasks.add_task(_run_tip_a_export_job, job_id)
    return {"success": True, "job_id": job_id}


@router.get("/sms-log/excel-tip-a/status/{job_id}")
def sms_log_excel_tip_a_status(job_id: str, request: Request):
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect
    _validate_tip_a_job_id(job_id)
    status_path, _ = _tip_a_job_paths(job_id)
    if not os.path.exists(status_path):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Job-от не е пронајден."})
    try:
        with open(status_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})


@router.get("/sms-log/excel-tip-a/download/{job_id}")
def sms_log_excel_tip_a_download(job_id: str, request: Request):
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect
    _validate_tip_a_job_id(job_id)
    _, output_path = _tip_a_job_paths(job_id)
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Excel датотеката сè уште не е подготвена.")
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="dospeana_premija_tip_a.xlsx",
    )


@router.get("/sms-log/excel-tip-a")
def sms_log_excel_tip_a(request: Request):
    """Izvoz vo Excel na polinjata za praka na Tip A (dospeana premija) SMS."""
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect

    try:
        buf = _build_tip_a_export()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="dospeana_premija_tip_a.xlsx"'},
    )


@router.get("/sms-log/excel-tip-b")
def sms_log_excel_tip_b(request: Request):
    """Izvoz vo Excel na polinjata za praka na Tip B (Riziko kredit) SMS."""
    user, redirect = _require_sms_log_role(request)
    if redirect:
        return redirect

    try:
        rows, error = _query_riziko_kredit_za_izvoz()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if error:
        raise HTTPException(status_code=500, detail=error)

    data_rows = [
        [
            r["polisa_broj"], r["telefon"], r["dolg"],
            r.get("polisa_status_desc", ""), r.get("valuta_desc", ""), r.get("tip_produkt", ""),
            r.get("polisa_status", ""), r.get("datum_status", ""), r.get("polisa_sosotojba", ""),
        ]
        for r in rows
    ]
    buf = _build_xlsx(
        "Riziko kredit Tip B",
        [
            "Полиса број", "Телефон", "Долг",
            "Полиса статус", "Валута", "Тип на продукт",
            "Полиса статус", "Датум статус", "Полиса состојба",
        ],
        data_rows,
        col_widths=[18, 16, 14, 16, 10, 16, 16, 14, 16],
    )

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="riziko_kredit_tip_b.xlsx"'},
    )

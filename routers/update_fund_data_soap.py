# routers/update_fund_data_rest.py

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
import traceback
import threading

import routers.Connection as Connection  # your Informix module


# =========================================================
# CONFIG
# =========================================================
TOKEN = "4a8ac71c-c340-4c38-9532-87bce8b9396a"
BASE_URL = f"https://feeds.mse.mk/service/FreeMSEFeeds.svc/fundunitvalue/XML/{TOKEN}"
TIMEOUT_SECONDS = 60

# APScheduler overlap protection
_fund_lock = threading.Lock()

_session = requests.Session()
_session.headers.update({"Accept": "text/xml"})


# =========================================================
# REST FETCH (NOT SOAP)
# =========================================================
def fetch_fundunitvalue_xml(formatted_date: str) -> str:
    """
    Fetch fund unit value XML via REST endpoint.
    Tries:
      A) {BASE_URL}/{YYYYMMDD}
      B) {BASE_URL}?date={YYYYMMDD}
    Returns raw XML (string).
    Raises Exception with detailed diagnostics.
    """
    # Try A: date in path
    url_a = f"{BASE_URL}/{formatted_date}"
    r = _session.get(url_a, timeout=TIMEOUT_SECONDS)
    ct = (r.headers.get("Content-Type") or "").lower()

    if r.status_code == 200 and ("xml" in ct or r.text.strip().startswith("<?xml")):
        return r.text

    # Try B: date as query param
    url_b = BASE_URL
    r2 = _session.get(url_b, params={"date": formatted_date}, timeout=TIMEOUT_SECONDS)
    ct2 = (r2.headers.get("Content-Type") or "").lower()

    if r2.status_code == 200 and ("xml" in ct2 or r2.text.strip().startswith("<?xml")):
        return r2.text

    raise Exception(
        "Failed to fetch fundunitvalue XML.\n"
        f"TryA URL={url_a}\n"
        f"  HTTP={r.status_code} CT={r.headers.get('Content-Type')} BODY={r.text[:300]}\n"
        f"TryB URL={url_b}?date={formatted_date}\n"
        f"  HTTP={r2.status_code} CT={r2.headers.get('Content-Type')} BODY={r2.text[:300]}"
    )


# =========================================================
# XML PARSE
# =========================================================
def parse_fundunitvalue_xml(xml_data: str):
    """
    Parses XML and returns list[dict].
    Namespace expected for entities:
      http://schemas.datacontract.org/2004/07/Entities
    """
    root = ET.fromstring(xml_data)

    ns = {
        "a": "http://schemas.datacontract.org/2004/07/Entities",
    }

    def safe_text(parent, tag):
        el = parent.find(f"a:{tag}", ns)
        return el.text.strip() if el is not None and el.text else None

    def safe_float(x):
        try:
            return float(x) if x not in (None, "") else 0.0
        except Exception:
            return 0.0

    funds = root.findall(".//a:FundUnitValue", ns)
    rows = []

    for fund in funds:
        rows.append({
            "calculation_date": safe_text(fund, "CalculationDate"),
            "daily_avg_sale_price": safe_float(safe_text(fund, "DailyAverageSalePrice")),
            "daily_buying_price": safe_float(safe_text(fund, "DailyBuyingPrice")),
            "description_en": safe_text(fund, "DescriptionEN"),
            "description_mk": safe_text(fund, "DescriptionMK"),
            "last_daily_sale_price": safe_float(safe_text(fund, "LastDailySalePrice")),
            "value_date": safe_text(fund, "ValueDate"),
        })

    return rows


# =========================================================
# INFORMIX INSERT
# =========================================================
def insert_rows_to_informix(rows):
    if not rows:
        print("[fund_update] No rows parsed -> nothing to insert")
        return

    sql = """
    INSERT INTO appuser.os_udel_upload
    (os_udel_uploadid, datecreated, usercreated, version, invrest_fond, cena_udel_mkd,
     cena_udel_eur, datum, par_statusid, os_udel_uploadfileid)
    VALUES (sq_os_udel_upload.nextval, CURRENT, 'admin', 0, ?, ?,
            ? / vrati_kurs(MDY(?, ?, ?), 'EUR'), MDY(?, ?, ?), 1, 1)
    """

    cur, ok = Connection.OSISinit()

    for r in rows:
        try:
            v = r.get("value_date")
            if not v:
                continue

            raw = v.split("T")[0]  # "YYYY-MM-DD"
            vdate = datetime.strptime(raw, "%Y-%m-%d").date()
            d, m, y = vdate.day, vdate.month, vdate.year

            name = r.get("description_mk") or r.get("description_en") or "UNKNOWN"
            mkd_price = float(r.get("daily_buying_price") or 0.0)

            cur.execute(sql, (name, mkd_price, mkd_price, m, d, y, m, d, y))
            print(f"[fund_update] Inserted: {vdate} ({name}) mkd={mkd_price}")

        except Exception as e:
            print(f"[fund_update] Insert error: {e}")


# =========================================================
# MAIN UPDATE LOOP (from last DB date to today)
# =========================================================
def update_fund_data_rest():
    """
    Reads last inserted date from os_udel_upload,
    then fetches + inserts for each day up to today.
    """
    cur, ok = Connection.OSISinit()
    cur.execute("SELECT MAX(datum) FROM os_udel_upload")
    rez = cur.fetchone()

    if rez and rez[0]:
        last = rez[0]
        start_date = last if isinstance(last, date) else datetime.strptime(str(last), "%Y-%m-%d").date()
    else:
        start_date = datetime.now().date() - timedelta(days=1)

    end_date = datetime.now().date()
    current = start_date + timedelta(days=1)

    while current <= end_date:
        formatted = current.strftime("%Y%m%d")
        print(f"[fund_update] Processing fund date: {formatted}")

        xml = fetch_fundunitvalue_xml(formatted)
        rows = parse_fundunitvalue_xml(xml)
        insert_rows_to_informix(rows)

        current += timedelta(days=1)

    print("[fund_update] Fund unit value REST update completed.")


# =========================================================
# APSCHEDULER JOB WRAPPER (safe)
# =========================================================
def scheduled_fund_update():
    """
    Safe job wrapper:
    - prevents overlapping runs
    - catches exceptions (won't crash scheduler)
    """
    if not _fund_lock.acquire(blocking=False):
        print("[fund_update] Previous run still running -> skip")
        return

    start_ts = datetime.now()
    print(f"[fund_update] START {start_ts}")

    try:
        update_fund_data_rest()
    except Exception as e:
        print("[fund_update] ERROR")
        print(str(e))
        traceback.print_exc()
    finally:
        _fund_lock.release()
        end_ts = datetime.now()
        print(f"[fund_update] END {end_ts} duration={end_ts - start_ts}")


# =========================================================
# CLI TEST (optional)
# =========================================================
if __name__ == "__main__":
    # manual run:
    scheduled_fund_update()

from datetime import datetime
from dateutil.relativedelta import relativedelta
import routers.Connection as Connection

from datetime import date, timedelta

def get_first_day_next_month():
    today = date.today()
    next_month = today.month % 12 + 1
    next_year = today.year + (today.month // 12)
    return date(next_year, next_month, 1)

def get_vfin_stavkaids(filter_column):
    """
    Fetch fin_stavkaid values depending on filter_column:
      - 'f_popust' for PO
      - 'f_ko' for KO
    Returns a semicolon-separated string of IDs (e.g., "1;13;14").
    """
    tdatum_faktura = get_first_day_next_month()
    day = tdatum_faktura.day
    month = tdatum_faktura.month
    year = tdatum_faktura.year

    print(f"Fetching fin_stavkaid for {filter_column} with datum_faktura={tdatum_faktura}")

    sql = f"""
        SELECT first 100 fin_stavkaid
        FROM vesna.knizenje_po
        WHERE {filter_column} = 't'
          AND datum_faktura = MDY({month}, {day}, {year})
    """

    cursor, OK = Connection.OSISinit()
    if not OK or cursor is None:
        print("Грешка - нема врска со база")
        return ""

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        ids = [str(row[0]) for row in rows]
        result = ";".join(ids)
        print(f"Fetched stavkaids: {result}")
        return result
    except Exception as e:
        print(f"SQL Error while fetching fin_stavkaid: {e}")
        return ""
    finally:
        cursor.close()



def knizi_PO_KO(vfin_stavkaid, tip_knizenje):
    tod_datum = get_first_day_next_month()
    tdo_datum = tod_datum
    tdatum_nalog = tod_datum
    tuser_id = 6   # fixed user id

    # Convert to string before sending to Informix
    tod_datum_str = tod_datum.strftime("%d/%m/%Y")
    tdo_datum_str = tdo_datum.strftime("%d/%m/%Y")
    tdatum_nalog_str = tdatum_nalog.strftime("%d/%m/%Y")

    sql = """
        call knizi_ko_po(?, ?, ?, ?, ?, ?)
    """

    cursor, OK = Connection.OSISinit()
    if not OK or cursor is None:
        print("Грешка - нема врска со база")
        return False, None, "Грешка - нема врска со база"

    try:
        params = (
            vfin_stavkaid,         # string like "1;13;14"
            tod_datum_str,
            tdo_datum_str,
            tdatum_nalog_str,
            tip_knizenje,
            tuser_id,
        )
        cursor.execute(sql, params)
        row = cursor.fetchone()
    except Exception as e:
        print(f"SQL Error: {e}")
        return False, None, str(e)
    finally:
        cursor.close()

    if not row:
        return True, None, "Функцијата не врати резултат"

    result_int, result_msg = row
    return True, result_int, result_msg



# === Scheduler Wrappers ===

import time

# knizi_ko_po contract (see the database function):
#   0 = KO (knizhno odobrenie)
#   1 = PO (popust)
TIP_KNIZENJE_KO = 0
TIP_KNIZENJE_PO = 1

def scheduled_knizi(filter_column, tip_knizenje, label, wait_seconds=30, max_retries=5):
    print(f"Scheduled: Sending knizi_ko_po for {label} (tip={tip_knizenje})")

    stavkaids = ""
    attempt = 0
    while not stavkaids and attempt < max_retries:
        stavkaids = get_vfin_stavkaids(filter_column)
        if not stavkaids:
            attempt += 1
            print(f"No stavkaids found for {label}. Attempt {attempt}/{max_retries}. Retrying in {wait_seconds} seconds...")
            if attempt < max_retries:
                time.sleep(wait_seconds)

    if not stavkaids:
        print(f"[{label}] No stavkaids found after {max_retries} attempts. Aborting.")
        return

    print(f"Found stavkaids for {label}: {stavkaids}")

    ok, code, msg = knizi_PO_KO(vfin_stavkaid=stavkaids, tip_knizenje=tip_knizenje)
    print(f"[{label}] stavkaids={stavkaids} -> ok={ok}, code={code}, msg={msg}")


def scheduled_knizi_PO():
    scheduled_knizi("f_popust", TIP_KNIZENJE_PO, "PO")


def scheduled_knizi_KO():
    scheduled_knizi("f_ko", TIP_KNIZENJE_KO, "KO")


def scheduled_fin_izvod_insert():
    """
    Дневно 21:00 — за секој FIN_IZVOD_FILE со par_statusid <> 10
    повикува ја функцијата fin_izvod_file_insert(fin_izvod_fileid, 6).
    """
    print("[FIN_IZVOD] Scheduler started")

    cursor, OK = Connection.OSISinit()
    if not OK or cursor is None:
        print("[FIN_IZVOD] ERROR - no DB connection")
        return

    try:
        cursor.execute("SELECT fin_izvod_fileid FROM FIN_IZVOD_FILE WHERE f_avtomatski=1")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"[FIN_IZVOD] SELECT error: {e}")
        cursor.close()
        return

    cursor.close()

    if not rows:
        print("[FIN_IZVOD] No rows found (par_statusid <> 10)")
        return

    print(f"[FIN_IZVOD] Found {len(rows)} records to process")

    for row in rows:
        fin_izvod_fileid = row[0]
        cur2, OK2 = Connection.OSISinit()
        if not OK2 or cur2 is None:
            print(f"[FIN_IZVOD] ERROR - no DB connection for id={fin_izvod_fileid}")
            continue
        try:
            cur2.execute(
                "EXECUTE FUNCTION appuser.fin_izvod_file_insert(?, 6)",
                [fin_izvod_fileid]
            )
            result = cur2.fetchone()
            print(f"[FIN_IZVOD] id={fin_izvod_fileid} -> result={result}")
        except Exception as e:
            print(f"[FIN_IZVOD] ERROR id={fin_izvod_fileid}: {e}")
        finally:
            cur2.close()

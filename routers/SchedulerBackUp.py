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
        SELECT fin_stavkaid
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

def scheduled_knizi_KO():
    print("Scheduled: Sending knizi_ko_po for KO (tip=1)")
    stavkaids = get_vfin_stavkaids("f_ko")  # returns "1;13;14"
    
    if not stavkaids:
        print("No stavkaids found for KO.")
        return

    print(f"Found stavkaids for KO: {stavkaids}")

    # Send all IDs as a single string to the procedure
    ok, code, msg = knizi_PO_KO(vfin_stavkaid=stavkaids, tip_knizenje=1)
    print(f"[KO] stavkaids={stavkaids} -> code={code}, msg={msg}")

def scheduled_knizi_PO():
    print("Scheduled: Sending knizi_ko_po for KO (tip=0)")
    stavkaids = get_vfin_stavkaids("f_popust")  # returns "1;13;14"
    
    if not stavkaids:
        print("No stavkaids found for KO.")
        return

    print(f"Found stavkaids for KO: {stavkaids}")

    # Send all IDs as a single string to the procedure
    ok, code, msg = knizi_PO_KO(vfin_stavkaid=stavkaids, tip_knizenje=0)
    print(f"[KO] stavkaids={stavkaids} -> code={code}, msg={msg}")



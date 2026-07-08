from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from routers import aso_reports
import os
from datetime import datetime
from fastapi import UploadFile, File, Form, Request
from io import BytesIO
import pandas as pd
import calendar
from routers import Connection
from datetime import date
import numpy as np

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        # Proper redirect that stops execution
        raise HTTPException(
            status_code=303,
            headers={"Location": "/siglife-report/login"}
        )
    return user


@router.get("/aso", response_class=HTMLResponse)
async def aso_page(request: Request):
    user = get_current_user(request)

    now = datetime.now()
    selected_month = now.strftime("%B")  # "January", "February", ...
    selected_year = now.year             # int

    return templates.TemplateResponse(
        "aso_reports.html",
        {
            "request": request,
            "user": user,
            "selected_month": selected_month,
            "selected_year": selected_year
        }
    )


@router.post("/aso/import-si", response_class=HTMLResponse)
async def import_si(request: Request, month: str = Form(...), year: str = Form(...)):
    user = get_current_user(request)

    ok, result = aso_reports.prebSI(month, year)
    message = f"Грешка: {result}" if not ok else f"Успешно! Резултат: {result}"

    return templates.TemplateResponse(
        "aso_reports.html",
        {
            "request": request,
            "result": message,
            "selected_month": month,
            "selected_year": int(year),
            "user": user
        }
    )


@router.post("/aso/gen-excel", response_class=HTMLResponse)
async def gen_excel(request: Request, month: str = Form(...), year: str = Form(...)):
    user = get_current_user(request)

    ok, result = aso_reports.genSI(month, year)
    message = f"Грешка: {result}" if not ok else "Excel генериран успешно!"

    return templates.TemplateResponse(
        "aso_reports.html",
        {
            "request": request,
            "result": message,
            "selected_month": month,
            "selected_year": int(year),
            "user": user
        }
    )


@router.post("/aso/sp1-analitika", response_class=HTMLResponse)
async def sp1_analitika(request: Request, month: str = Form(...), year: str = Form(...)):
    user = get_current_user(request)

    ok, result = aso_reports.Sp1analitika_a(month, year)
    message = f"Грешка: {result}" if not ok else "СП-1 Аналитика генерирана успешно!"

    return templates.TemplateResponse(
        "aso_reports.html",
        {
            "request": request,
            "result": message,
            "selected_month": month,
            "selected_year": int(year),
            "user": user
        }
    )


@router.post("/aso/sp2-analitika", response_class=HTMLResponse)
async def sp2_analitika(request: Request, month: str = Form(...), year: str = Form(...)):
    user = get_current_user(request)

    ok, result = aso_reports.Sp2analitika_a(month, year)
    message = f"Грешка: {result}" if not ok else "СП-2 Аналитика генерирана успешно!"

    return templates.TemplateResponse(
        "aso_reports.html",
        {
            "request": request,
            "result": message,
            "selected_month": month,
            "selected_year": int(year),
            "user": user
        }
    )



@router.post("/aso/import-excel-all", response_class=HTMLResponse)
async def import_excel_all(
    request: Request,
    month: str = Form(...),
    year: int = Form(...),
    excel_file: UploadFile = File(...)
):
    user = get_current_user(request)
    excel_bytes = await excel_file.read()

    results = []

    # ✅ list of import functions to execute
    IMPORT_FUNCTIONS = [
    ("SP-1 ZO",     aso_reports.Import_SP1_ZO),
    ("SP-2 ZO",     aso_reports.Import_SP2_ZO),
    ("SP-4 ZO",     aso_reports.Import_SP4_ZO),
    ("SP-4 RS ZO",  aso_reports.Import_SP4_RS_ZO),
    ("SP-4 MR",     aso_reports.Import_SP4_MR),   # ✅ uses BOTH MR sheets
    ("SP-7 ZO",     aso_reports.Import_SP7_ZO),
    ("SP-6 ZO",     aso_reports.Import_SP6_ZO),
    ("SP-3 ZO",     aso_reports.Import_SP3_ZO),
    ("SP-5 ZO",     aso_reports.Import_SP5_ZO),
    ("SP-8 ZO",     aso_reports.Import_SP8_ZO),
]



    ok_del, msg_del = aso_reports.delete_all_stat_izvestai_for_month(month, year)
    if not ok_del:
        final_message = f"❌ DELETE: {msg_del}"
        # return TemplateResponse...
    else:
        results.append(f"✅ DELETE: {msg_del}")


    for label, func in IMPORT_FUNCTIONS:
        try:
            ok, msg = func(excel_bytes, month, year)
            prefix = "✅" if ok else "❌"
            results.append(f"{prefix} {label}: {msg}")
        except Exception as e:
            results.append(f"❌ {label}: {str(e)}")

    final_message = "<br>".join(results)

    return templates.TemplateResponse(
        "aso_reports.html",
        {
            "request": request,
            "result": final_message,
            "selected_month": month,
            "selected_year": year,
            "user": user
        }
    )

# -----------------------------
# Transfer to reporting (DF)
# -----------------------------
STAT_IZVESTAI_COLUMNS = [
    "stat_izvestaiid",
    "datechanged",
    "datecreated",
    "userchanged",
    "usercreated",
    "version",
    "datum",
    "stat_izvestaj",
    "vid_stavka",

    "kol100",
    "kol101",
    "kol102",
    "kol103",
    "kol104",
    "kol105",
    "kol106",
    "kol107",

    "kol200",
    "kol200a",
    "kol201",
    "kol201_1",
    "kol202",
    "kol203",
    "kol204",
    "kol205",
    "kol205a",
    "kol206",
    "kol207",

    "kol300",
    "kol301",
    "kol302",
    "kol303",
    "kol304",
    "kol305",
    "kol306",

    "kol101_1",
    "kol101_2",
    "kol101_3",
    "kol101a",

    "par_statusid",
    "client_name",
    "maticen_broj",
]

def _pick_conn_and_cursor(ret):
    """
    OSISinit може да враќа (conn, ok) или (cursor, conn, ok) или (conn, cursor, ok) итн.
    - connection: има .cursor()
    - cursor: има .execute()
    """
    if not isinstance(ret, (list, tuple)):
        raise ValueError(f"OSISinit returned non-tuple: {type(ret)}")

    ok = bool(ret[-1])  # последно е OK кај тебе

    conn = next((x for x in ret if hasattr(x, "cursor") and callable(getattr(x, "cursor", None))), None)
    cur  = next((x for x in ret if hasattr(x, "execute") and callable(getattr(x, "execute", None))), None)

    if conn is None:
        raise ValueError("Не најдов connection (објект со .cursor()) во OSISinit return")
    if cur is None:
        # ако нема cursor, направи го од conn
        cur = conn.cursor()

    return conn, cur, ok

import pandas as pd

def cursor_to_df(cur, sql: str, params=None) -> pd.DataFrame:
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]  # имиња на колони
    return pd.DataFrame(rows, columns=cols)

def commit_from_cursor(cur):
    conn = getattr(cur, "_connection", None) or getattr(cur, "connection", None)
    if conn is None:
        raise ValueError("Не можам да најдам connection за commit (нема _connection/connection на cursor)")
    conn.commit()

from datetime import date, datetime
import numpy as np
import pandas as pd
import calendar
from fastapi import Form, Request
from fastapi.responses import HTMLResponse

def _to_dt_or_none(v):
    """Parse 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD' to datetime/date if needed."""
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # try datetime first
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        # try date
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            pass
    return v  # leave as-is if unknown type



@router.post("/aso/transfer-to-reporting", response_class=HTMLResponse)
async def transfer_to_reporting_page(
    request: Request,
    month: str = Form(...),
    year: str = Form(...)
):
    user = get_current_user(request)

    print("=== START transfer_to_reporting ===")
    print("Input month:", month, "year:", year)

    try:
        # -------------------------------------------------
        # MDY params (Informix)
        # -------------------------------------------------
        y = int(year)
        m = list(calendar.month_name).index(month)
        last_day = calendar.monthrange(y, m)[1]
        print(f"MDY params -> month={m}, day={last_day}, year={y}")

        # -------------------------------------------------
        # CONNECTIONS
        # -------------------------------------------------
        print("Calling OSISinit()")
        src_ret = Connection.OSISinit()
        print("OSISinit return:", src_ret)

        print("Calling OSISinitReporting()")
        rep_ret = Connection.OSISinitReporting()
        print("OSISinitReporting return:", rep_ret)

        # -------------------------------------------------
        # CURSORS
        # -------------------------------------------------
        src_cur = next(x for x in src_ret if hasattr(x, "execute"))
        rep_cur = next(x for x in rep_ret if hasattr(x, "execute"))

        ok_src = bool(src_ret[-1])
        ok_rep = bool(rep_ret[-1])

        print("SRC cursor:", src_cur)
        print("REP cursor:", rep_cur)
        print("Connection OK -> SRC:", ok_src, "REP:", ok_rep)

        if not ok_src or not ok_rep:
            msg = "❌ Проблем со конекција (SOURCE / REPORTING)"
            print(msg)
        else:
            # -------------------------------------------------
            # SELECT columns (full set)
            # -------------------------------------------------
            cols_select = ", ".join(STAT_IZVESTAI_COLUMNS)

            # -------------------------------------------------
            # INSERT setup:
            # - omit datecreated/datechanged
            # - datum inserted as MDY(?, ?, ?)
            # - datecreated set as CURRENT
            # -------------------------------------------------
            SKIP_COLS = {"datecreated", "datechanged"}
            base_insert_cols = [c for c in STAT_IZVESTAI_COLUMNS if c not in SKIP_COLS]
            PARAM_COLS = [c for c in base_insert_cols if c != "datum"]

            print("Columns count (select):", len(STAT_IZVESTAI_COLUMNS))
            print("Columns count (param cols w/o datum):", len(PARAM_COLS))

            # -------------------------------------------------
            # SELECT (MDY)
            # -------------------------------------------------
            select_sql = f"""
                SELECT {cols_select}
                FROM appuser.stat_izvestai
                WHERE datum = MDY(?, ?, ?)
            """

            print("Executing SELECT with MDY")
            df = cursor_to_df(src_cur, select_sql, (m, last_day, y))
            print("DF shape:", df.shape)

            if df.empty:
                msg = f"❌ Нема податоци за {month} {year}"
                print(msg)
            else:
                print("DF preview:")
                print(df.head(3))

                # -------------------------------------------------
                # Clean NaN -> None
                # -------------------------------------------------
                df = df.replace({np.nan: None})

                # -------------------------------------------------
                # DELETE on reporting (MDY)
                # -------------------------------------------------
                print("Deleting from REPORTING with MDY")
                rep_cur.execute(
                    "DELETE FROM appuser.stat_izvestai WHERE datum = MDY(?, ?, ?)",
                    (m, last_day, y)
                )
                print("DELETE done")

                # -------------------------------------------------
                # INSERT SQL (datum as MDY, datecreated as CURRENT)
                # -------------------------------------------------
                cols_sql = ", ".join([*PARAM_COLS, "datum", "datecreated"])
                vals_sql = ", ".join(["?"] * len(PARAM_COLS) + ["MDY(?, ?, ?)", "CURRENT"])

                insert_sql = f"""
                    INSERT INTO appuser.stat_izvestai ({cols_sql})
                    VALUES ({vals_sql})
                """

                print("Insert SQL:")
                print(insert_sql)

                base_rows = list(df[PARAM_COLS].itertuples(index=False, name=None))
                rows = [r + (m, last_day, y) for r in base_rows]

                print("Rows to insert:", len(rows))
                print("Sample row (params + MDY):", rows[0] if rows else None)

                print("Executing executemany()")
                rep_cur.executemany(insert_sql, rows)

                # ✅ NO COMMIT (autocommit ON)
                msg = f"✅ Пренесени {len(rows)} редови за {month} {year} на REPORTING"
                print(msg)

        print("=== END transfer_to_reporting ===")

        return templates.TemplateResponse(
            "aso_reports.html",
            {
                "request": request,
                "result": msg,
                "selected_month": month,
                "selected_year": y,
                "user": user
            }
        )

    except StopIteration:
        print("❌ Cursor not found in OSISinit return")
        return templates.TemplateResponse(
            "aso_reports.html",
            {
                "request": request,
                "result": "❌ Не најдов cursor (објект со .execute) во OSISinit return",
                "selected_month": month,
                "selected_year": int(year),
                "user": user
            }
        )

    except Exception as e:
        print("❌ EXCEPTION OCCURRED")
        import traceback
        traceback.print_exc()

        return templates.TemplateResponse(
            "aso_reports.html",
            {
                "request": request,
                "result": f"❌ Грешка при пренос: {str(e)}",
                "selected_month": month,
                "selected_year": int(year),
                "user": user
            }
        )

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException
from auth.role_utils import has_any_role
from routers import Connection
from datetime import date
from typing import List
import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)

_ALLOWED_ROLES = ["admin", "finansii", "finance", "kolektivno_uu"]


def _require_role(request: Request):
    user = request.session.get("user")
    if not user:
        return None, RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, *_ALLOWED_ROLES):
        raise HTTPException(status_code=403, detail="Немате пристап до овој модул.")
    return user, None


_SQL_DOSPEANA_BASE = """
SELECT
    x2.polisa_broj_cel                          AS polisa_broj,
    pc.par_client                               AS client_id,
    pc.desc                                     AS ime_prezime,
    COUNT(DISTINCT x0.os_aneks_fakturaid)       AS br_aneksi,
    SUM(NVL(x0.iznos, 0) - NVL(fs.naplata, 0)) AS vk_neplateno,
    0                                           AS dummy
FROM viki.os_aneks_faktura x0
JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
JOIN par_client pc       ON pc.par_clientid = x1.par_clientid
LEFT JOIN (
    SELECT os_aneks_fakturaid, SUM(NVL(iznos_p, 0)) AS naplata
    FROM fin_stavka
    WHERE sifra_zatvaranje IS NOT NULL AND f_rs <> 'N'
    GROUP BY os_aneks_fakturaid
) fs ON fs.os_aneks_fakturaid = x0.os_aneks_fakturaid
WHERE NVL(x0.f_rs, 'R') <> 'N'
  AND x1.os_zbiren_aneksid IS NULL
  AND NVL(x0.iznos, 0) > 0
  {extra_where}
GROUP BY x2.polisa_broj_cel, pc.par_client, pc.desc
HAVING SUM(NVL(x0.iznos, 0) - NVL(fs.naplata, 0)) > 0.005
ORDER BY pc.desc
"""


def _build_dospeana_sql(tip_polisa: str = "", klient: str = "",
                        polisa_broj: str = "", datum_do: str = ""):
    from datetime import date as _date
    conditions = []
    params = []

    if tip_polisa and tip_polisa.strip():
        conditions.append("AND x2.polisa_broj_cel LIKE ?")
        params.append(tip_polisa.strip().rstrip("%") + "%")

    if klient and klient.strip():
        conditions.append("AND UPPER(pc.desc) LIKE ?")
        params.append("%" + klient.strip().upper() + "%")

    if polisa_broj and polisa_broj.strip():
        conditions.append("AND x2.polisa_broj_cel LIKE ?")
        params.append("%" + polisa_broj.strip() + "%")

    cutoff = datum_do.strip() if datum_do and datum_do.strip() else _date.today().isoformat()
    conditions.append("AND x0.data_faktura <= ?")
    params.append(cutoff)

    sql = _SQL_DOSPEANA_BASE.format(extra_where=" ".join(conditions))
    return sql, params


_SQL_ZERO_BALANCE_BASE = """
SELECT
    x2.polisa_broj_cel                                                                      AS polisa_broj,
    pc.par_client                                                                           AS client_id,
    pc.desc                                                                                 AS ime_prezime,
    COUNT(DISTINCT x0.os_aneks_fakturaid)                                                  AS br_aneksi,
    SUM(CASE WHEN NVL(x0.iznos,0) > 0 THEN NVL(x0.iznos,0) - NVL(fs.naplata,0) ELSE 0 END) AS vk_pozitivno,
    SUM(CASE WHEN NVL(x0.iznos,0) < 0 THEN NVL(x0.iznos,0) - NVL(fs.naplata,0) ELSE 0 END) AS vk_negativno
FROM viki.os_aneks_faktura x0
JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
JOIN par_client pc       ON pc.par_clientid = x1.par_clientid
LEFT JOIN (
    SELECT os_aneks_fakturaid, SUM(NVL(iznos_p, 0)) AS naplata
    FROM fin_stavka
    WHERE sifra_zatvaranje IS NOT NULL AND f_rs <> 'N'
    GROUP BY os_aneks_fakturaid
) fs ON fs.os_aneks_fakturaid = x0.os_aneks_fakturaid
WHERE NVL(x0.f_rs, 'R') <> 'N'
  AND x1.os_zbiren_aneksid IS NULL
  {extra_where}
GROUP BY x2.polisa_broj_cel, pc.par_client, pc.desc
HAVING ABS(SUM(NVL(x0.iznos,0) - NVL(fs.naplata,0))) < 0.01
   AND COUNT(DISTINCT x0.os_aneks_fakturaid) > 1
   AND SUM(ABS(NVL(x0.iznos,0) - NVL(fs.naplata,0))) > 0.01
ORDER BY pc.desc
"""


def _build_zero_balance_sql(tip_polisa: str = "", klient: str = "",
                            polisa_broj: str = "", datum_od: str = "", datum_do: str = ""):
    """Build zero-balance SQL with optional filters. Returns (sql, params)."""
    conditions = []
    params = []

    if tip_polisa and tip_polisa.strip():
        conditions.append("AND x2.polisa_broj_cel LIKE ?")
        params.append(tip_polisa.strip().rstrip("%") + "%")

    if klient and klient.strip():
        conditions.append("AND UPPER(pc.desc) LIKE ?")
        params.append("%" + klient.strip().upper() + "%")

    if polisa_broj and polisa_broj.strip():
        conditions.append("AND x2.polisa_broj_cel LIKE ?")
        params.append("%" + polisa_broj.strip() + "%")

    if datum_od and datum_od.strip():
        conditions.append("AND x0.data_faktura >= ?")
        params.append(datum_od.strip())

    if datum_do and datum_do.strip():
        conditions.append("AND x0.data_faktura <= ?")
        params.append(datum_do.strip())

    sql = _SQL_ZERO_BALANCE_BASE.format(extra_where=" ".join(conditions))
    return sql, params

# Individual invoices: zero-balance policies with NO cash payments.
# CTE qualifying_polisi is referenced exactly ONCE in the outer SELECT,
# so JDBC params are supplied exactly once — no "too many host variables" error.
# All candidate open invoice rows — Python groups and filters to faktura-level zero balance
_SQL_INDIVIDUAL_BASE = """
SELECT
    x0.os_aneks_fakturaid,
    x2.polisa_broj_cel                                              AS polisa_broj,
    pc.par_client                                                   AS client_id,
    pc.desc                                                         AS ime_prezime,
    UPPER(x1.os_aneks || '/' || TRIM(vesna.vrati_godina(x1.par_yearid))
          || '-' || x0.rata)                                        AS faktura_broj,
    x0.data_faktura,
    NVL(x0.iznos, 0) - NVL(fs.naplata, 0)                         AS iznos
FROM viki.os_aneks_faktura x0
JOIN viki.os_aneks   x1 ON x1.os_aneksid   = x0.os_aneksid
JOIN viki.os_polisa  x2 ON x2.os_polisaid  = x1.os_polisaid
JOIN viki.os_ponuda  x3 ON x3.os_ponudaid  = x2.os_ponudaid
JOIN par_client pc       ON pc.par_clientid = x1.par_clientid
LEFT JOIN (
    SELECT os_aneks_fakturaid, SUM(NVL(iznos_p, 0)) AS naplata
    FROM fin_stavka
    WHERE sifra_zatvaranje IS NOT NULL AND f_rs <> 'N'
    GROUP BY os_aneks_fakturaid
) fs ON fs.os_aneks_fakturaid = x0.os_aneks_fakturaid
WHERE NVL(x0.f_rs, 'R') <> 'N'
  AND x1.os_zbiren_aneksid IS NULL
  AND ABS(NVL(x0.iznos, 0) - NVL(fs.naplata, 0)) > 0.005
  {extra_where}
ORDER BY x2.polisa_broj_cel,
         UPPER(x1.os_aneks || '/' || TRIM(vesna.vrati_godina(x1.par_yearid)) || '-' || x0.rata),
         x0.data_faktura,
         x0.os_aneks_fakturaid
"""


def _build_individual_sql(tip_polisa: str = "", klient: str = "",
                           polisa_broj: str = "", datum_od: str = "", datum_do: str = ""):
    conditions = []
    params = []

    if tip_polisa and tip_polisa.strip():
        conditions.append("AND x2.polisa_broj_cel LIKE ?")
        params.append(tip_polisa.strip().rstrip("%") + "%")

    if klient and klient.strip():
        conditions.append("AND UPPER(pc.desc) LIKE ?")
        params.append("%" + klient.strip().upper() + "%")

    if polisa_broj and polisa_broj.strip():
        conditions.append("AND x2.polisa_broj_cel LIKE ?")
        params.append("%" + polisa_broj.strip() + "%")

    if datum_od and datum_od.strip():
        conditions.append("AND x0.data_faktura >= ?")
        params.append(datum_od.strip())

    if datum_do and datum_do.strip():
        conditions.append("AND x0.data_faktura <= ?")
        params.append(datum_do.strip())

    sql = _SQL_INDIVIDUAL_BASE.format(extra_where=" ".join(conditions))
    return sql, params


def _split_valid_by_faktura(rows_for_polisa: list, selected_fids: set) -> tuple:
    """Among the selected os_aneks_fakturaid for one policy, keep only those
    whose faktura group (the subset actually selected, not necessarily the
    whole group) nets to zero. Returns (valid_ids, invalid_fakturi)."""
    from collections import defaultdict
    by_faktura = defaultdict(list)
    for r in rows_for_polisa:
        if str(r['os_aneks_fakturaid']) in selected_fids:
            by_faktura[r['faktura_broj']].append(r)

    valid_ids = []
    invalid_fakturi = []
    for faktura, grp in by_faktura.items():
        if abs(sum(r['iznos'] for r in grp)) < 0.01:
            valid_ids.extend(str(r['os_aneks_fakturaid']) for r in grp)
        else:
            invalid_fakturi.append(faktura)
    return valid_ids, invalid_fakturi


def _group_by_faktura(rows: list) -> list:
    """Group invoice rows by (polisa_broj, faktura_broj); keep only groups that net to zero."""
    from itertools import groupby as _gb
    grouped = []
    for (polisa, faktura), grp_iter in _gb(rows, key=lambda r: (r['polisa_broj'], r['faktura_broj'])):
        grp_list = list(grp_iter)
        grp_sum = sum(r['iznos'] for r in grp_list)
        grp_abs = sum(abs(r['iznos']) for r in grp_list)
        if abs(grp_sum) < 0.01 and grp_abs > 0.01:
            grouped.append({
                'polisa_broj':  polisa,
                'faktura_broj': faktura,
                'ime_prezime':  grp_list[0]['ime_prezime'],
                'grp_iznos':    round(grp_sum, 2),
                'stavki':       grp_list,
            })
    return grouped


# Detail view: all open annexes for a specific policy
_SQL_ANEKSI_PER_POLISA = """
SELECT
    UPPER(x1.os_aneks || '/' || TRIM(vesna.vrati_godina(x1.par_yearid))
          || '-' || x0.rata)            AS faktura_broj,
    x0.data_faktura,
    NVL(x0.iznos, 0)                    AS iznos,
    NVL(x0.iznos_denari, 0)             AS iznos_den,
    NVL(fs.naplata, 0)                  AS iznos_naplata
FROM viki.os_aneks_faktura x0
JOIN viki.os_aneks  x1 ON x1.os_aneksid  = x0.os_aneksid
JOIN viki.os_polisa x2 ON x2.os_polisaid = x1.os_polisaid
LEFT JOIN (
    SELECT os_aneks_fakturaid, SUM(NVL(iznos_p, 0)) AS naplata
    FROM fin_stavka
    WHERE sifra_zatvaranje IS NOT NULL AND f_rs <> 'N'
    GROUP BY os_aneks_fakturaid
) fs ON fs.os_aneks_fakturaid = x0.os_aneks_fakturaid
WHERE x2.polisa_broj_cel   = ?
  AND NVL(x0.f_rs, 'R')  <> 'N'
  AND x1.os_zbiren_aneksid IS NULL
ORDER BY x0.data_faktura, x0.os_aneks_fakturaid
"""


def _query(sql, params=None):
    cursor, ok = Connection.OSISinit()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchall()
    finally:
        try:
            cursor.close()
        except Exception:
            pass


def _call_uu(ids: list, datum: date, user_id: int):
    """Step 1: Create fin_izvod_h + fin_izvod_i via fin_uu_kolektivno.

    Uses fin_uu_worklist staging table — Python inserts the selected
    os_aneks_fakturaid values (auto-commit per statement), calls the
    stored function (uses DIRTY READ so sees them immediately), then
    cleans up the staging rows regardless of outcome.

    Returns (code, message, fin_izvod_hid).
    """
    import uuid as _uuid
    session_key = _uuid.uuid4().hex[:20]

    cursor, ok = Connection.OSISinit()
    if not ok or cursor is None:
        return -1, "Нема конекција кон базата", 0
    try:
        for fid in ids:
            cursor.execute(
                "INSERT INTO fin_uu_worklist(session_key, os_aneks_fakturaid) VALUES(?, ?)",
                [session_key, int(fid)]
            )

        cursor.execute(
            "EXECUTE FUNCTION appuser.fin_uu_kolektivno(?, TO_DATE(?, '%Y-%m-%d'), ?)",
            [session_key, datum.isoformat(), user_id]
        )
        row = cursor.fetchone()

        if row:
            code = int(row[0])
            msg  = str(row[1]).strip()
            hid  = int(row[2]) if len(row) > 2 and row[2] else 0
            return code, msg, hid
        return -1, "Нема одговор од функцијата", 0
    except Exception as e:
        return -1, f"Грешка: {e}", 0
    finally:
        try:
            cursor.execute(
                "DELETE FROM fin_uu_worklist WHERE session_key = ?", [session_key]
            )
        except Exception:
            pass
        try:
            cursor.close()
        except Exception:
            pass


def _call_knizi(fin_izvod_hid: int, user_id: int):
    """Step 2: Post the УУ document to financials via knizi_izvod.
    Separate JDBC connection — knizi_izvod's internal ROLLBACK only
    affects its own BEGIN WORK scope, not the already-committed fin_izvod_h/i.
    Returns (code, message).
    """
    cursor, ok = Connection.OSISinit()
    if not ok or cursor is None:
        return -1, "Нема конекција за книжење"
    try:
        cursor.execute(
            "EXECUTE FUNCTION appuser.knizi_izvod(?, ?)",
            [fin_izvod_hid, user_id]
        )
        row = cursor.fetchone()
        if row:
            return int(row[0]), str(row[1]).strip()
        return -1, "Нема одговор од knizi_izvod"
    except Exception as e:
        return -1, f"Грешка при книжење: {e}"
    finally:
        try:
            cursor.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# GET  /kolektivno-uu  — filter form; results only after "Прегледај"
# ------------------------------------------------------------------
@router.get("/kolektivno-uu")
async def kolektivno_uu_list(
    request: Request,
    searched:    str = Query(""),
    klient:      str = Query(""),
    polisa_broj: str = Query(""),
    tip_polisa:  str = Query(""),
    datum_od:    str = Query(""),
    datum_do:    str = Query(""),
    dospeana:    str = Query(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    rows, grouped, error = [], [], None
    if searched:
        try:
            if dospeana:
                sql, params = _build_dospeana_sql(tip_polisa, klient, polisa_broj, datum_do)
                raw = _query(sql, params)
                rows = [
                    {
                        "polisa_broj":  r[0],
                        "client_id":    r[1],
                        "ime_prezime":  r[2],
                        "br_aneksi":    r[3],
                        "vk_pozitivno": float(r[4] or 0),
                        "vk_negativno": float(r[5] or 0),
                    }
                    for r in raw
                ]
            else:
                sql, params = _build_individual_sql(tip_polisa, klient, polisa_broj, datum_od, datum_do)
                raw = _query(sql, params)
                rows = [
                    {
                        "os_aneks_fakturaid": r[0],
                        "polisa_broj":        r[1],
                        "client_id":          r[2],
                        "ime_prezime":        r[3],
                        "faktura_broj":       r[4],
                        "data_faktura":       r[5],
                        "iznos":              float(r[6] or 0),
                    }
                    for r in raw
                ]
                grouped = _group_by_faktura(rows)
        except Exception as e:
            error = str(e)

    return templates.TemplateResponse("kolektivno_uu.html", {
        "request":       request,
        "user":          user,
        "active":        "kolektivno_uu",
        "rows":          rows,
        "grouped":       grouped,
        "detail":        None,
        "detail_polisa": None,
        "error":         error,
        "success":       None,
        "results":       None,
        "today_str":     date.today().isoformat(),
        "searched":      bool(searched),
        "f_klient":      klient,
        "f_polisa_broj": polisa_broj,
        "f_tip_polisa":  tip_polisa,
        "f_datum_od":    datum_od,
        "f_datum_do":    datum_do,
        "f_dospeana":    dospeana,
    })


# ------------------------------------------------------------------
# POST /kolektivno-uu/preview  — show detail annexes for one policy
# ------------------------------------------------------------------
@router.post("/kolektivno-uu/preview")
async def kolektivno_uu_preview(
    request:     Request,
    polisa_broj: str = Form(...),
    tip_polisa:  str = Form(""),
    klient:      str = Form(""),
    f_polisa_broj: str = Form(""),
    datum_od:    str = Form(""),
    datum_do:    str = Form(""),
    dospeana:    str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    list_rows, detail, error = [], [], None
    try:
        if dospeana:
            sql, params = _build_dospeana_sql(tip_polisa, klient, f_polisa_broj, datum_do)
        else:
            sql, params = _build_zero_balance_sql(tip_polisa, klient, f_polisa_broj, datum_od, datum_do)
        list_rows = [
            {
                "polisa_broj":  r[0], "client_id": r[1], "ime_prezime": r[2],
                "br_aneksi":    r[3],
                "vk_pozitivno": float(r[4] or 0),
                "vk_negativno": float(r[5] or 0),
            }
            for r in _query(sql, params)
        ]
        raw_d = _query(_SQL_ANEKSI_PER_POLISA, [polisa_broj])
        detail = [
            {
                "faktura_broj":  r[0],
                "data_faktura":  r[1],
                "iznos":         float(r[2] or 0),
                "iznos_den":     float(r[3] or 0),
                "iznos_naplata": float(r[4] or 0),
            }
            for r in raw_d
        ]
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse("kolektivno_uu.html", {
        "request":       request,
        "user":          user,
        "active":        "kolektivno_uu",
        "rows":          list_rows,
        "detail":        detail,
        "detail_polisa": polisa_broj,
        "error":         error,
        "success":       None,
        "today_str":     date.today().isoformat(),
        "searched":      True,
        "f_klient":      klient,
        "f_polisa_broj": f_polisa_broj,
        "f_tip_polisa":  tip_polisa,
        "f_datum_od":    datum_od,
        "f_datum_do":    datum_do,
        "f_dospeana":    dospeana,
    })


# ------------------------------------------------------------------
# POST /kolektivno-uu/zatvorit  — create УУ document
# ------------------------------------------------------------------
@router.post("/kolektivno-uu/zatvorit")
async def kolektivno_uu_zatvorit(
    request:       Request,
    polisa_broj:   str = Form(...),
    datum_uu:      str = Form(...),
    tip_polisa:    str = Form(""),
    klient:        str = Form(""),
    f_polisa_broj: str = Form(""),
    datum_od:      str = Form(""),
    datum_do:      str = Form(""),
    dospeana:      str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    try:
        datum = date.fromisoformat(datum_uu)
    except ValueError:
        datum = date.today()

    user_id = user.get("id", 6)

    # ── Step 1: Get all open faktura IDs for this polisa ──────────
    try:
        sql_ids, p_ids = _build_individual_sql(polisa_broj=polisa_broj)
        raw_ids = _query(sql_ids, p_ids)
        polisa_faktura_ids = [str(r[0]) for r in raw_ids]
    except Exception as e_ids:
        polisa_faktura_ids = []

    if not polisa_faktura_ids:
        code, msg, hid = -1, "Нема отворени ставки за полисата", 0
    else:
        code, msg, hid = _call_uu(polisa_faktura_ids, datum, user_id)

    knizi_msg = None
    knizi_warn = None

    if code == 1 and hid:
        # ── Step 2: Post to financials (separate connection/transaction) ─
        # knizi_izvod has its own BEGIN/ROLLBACK — calling it here in a
        # fresh JDBC connection means its ROLLBACK cannot undo step 1.
        k_code, k_msg = _call_knizi(hid, user_id)
        if k_code == 1:
            knizi_msg = f"Прокнижено: {k_msg}"
        else:
            # УУ document exists and is committed — only booking failed.
            # Surface it as a warning, not an error.
            knizi_warn = f"УУ е зачуван (hid={hid}), но книжењето не успеало: {k_msg}"

    list_rows = []
    try:
        if dospeana:
            sql, params = _build_dospeana_sql(tip_polisa, klient, f_polisa_broj, datum_do)
        else:
            sql, params = _build_zero_balance_sql(tip_polisa, klient, f_polisa_broj, datum_od, datum_do)
        list_rows = [
            {
                "polisa_broj":  r[0], "client_id": r[1], "ime_prezime": r[2],
                "br_aneksi":    r[3],
                "vk_pozitivno": float(r[4] or 0),
                "vk_negativno": float(r[5] or 0),
            }
            for r in _query(sql, params)
        ]
    except Exception:
        pass

    # Extract the УУ document number from the success message
    # Format: "УУ документот е креиран: УУ-YYYYMMDD-POLISA (N ставки)"
    uu_broj = None
    if code == 1:
        try:
            uu_broj = msg.split(": ", 1)[1].split(" (")[0].strip()
        except Exception:
            pass

    # Build user-facing messages
    success_msg = None
    error_msg   = None
    if code == 1:
        parts = [msg]
        if knizi_msg:
            parts.append(knizi_msg)
        success_msg = " | ".join(parts)
        if knizi_warn:
            error_msg = knizi_warn  # shown as warning below success
    else:
        error_msg = msg

    return templates.TemplateResponse("kolektivno_uu.html", {
        "request":       request,
        "user":          user,
        "active":        "kolektivno_uu",
        "rows":          list_rows,
        "detail":        None,
        "detail_polisa": None,
        "success":       success_msg,
        "error":         error_msg,
        "today_str":     date.today().isoformat(),
        "closed_polisa": polisa_broj if code == 1 else None,
        "uu_broj":       uu_broj,
        "datum_uu":      datum.isoformat() if code == 1 else None,
        "searched":      True,
        "f_klient":      klient,
        "f_polisa_broj": f_polisa_broj,
        "f_tip_polisa":  tip_polisa,
        "f_datum_od":    datum_od,
        "f_datum_do":    datum_do,
        "f_dospeana":    dospeana,
    })


# ------------------------------------------------------------------
# POST /kolektivno-uu/zatvorit-selected  — bulk close selected invoices
# ------------------------------------------------------------------
@router.post("/kolektivno-uu/zatvorit-selected")
async def kolektivno_uu_zatvorit_selected(
    request:       Request,
    datum_uu:      str = Form(...),
    sel_invoices:  List[str] = Form(default=[]),   # "os_aneks_fakturaid|polisa_broj"
    tip_polisa:    str = Form(""),
    klient:        str = Form(""),
    f_polisa_broj: str = Form(""),
    datum_od:      str = Form(""),
    datum_do:      str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    if not sel_invoices:
        error = "Не е избрана ниедна ставка."
        return templates.TemplateResponse("kolektivno_uu.html", {
            "request": request, "user": user, "active": "kolektivno_uu",
            "rows": [], "detail": None, "detail_polisa": None,
            "error": error, "success": None, "results": None,
            "today_str": date.today().isoformat(), "searched": True,
            "f_klient": klient, "f_polisa_broj": f_polisa_broj,
            "f_tip_polisa": tip_polisa, "f_datum_od": datum_od,
            "f_datum_do": datum_do, "f_dospeana": "",
        })

    try:
        datum = date.fromisoformat(datum_uu)
    except ValueError:
        datum = date.today()

    user_id = user.get("id", 6)

    # Group selected os_aneks_fakturaid by polisa_broj
    polisa_ids: dict = {}
    for sel in sel_invoices:
        parts = sel.split("|", 1)
        if len(parts) == 2:
            fid, polisa = parts[0], parts[1]
            polisa_ids.setdefault(polisa, []).append(fid)

    results = []
    for polisa, ids in polisa_ids.items():
        # Faktura-level balance check: reject any selected faktura group
        # whose picked rows don't net to zero, instead of silently
        # forwarding an unbalanced subset to fin_uu_kolektivno.
        try:
            sql_p, params_p = _build_individual_sql(polisa_broj=polisa)
            raw_p = _query(sql_p, params_p)
            rows_p = [
                {"os_aneks_fakturaid": r[0], "faktura_broj": r[4], "iznos": float(r[6] or 0)}
                for r in raw_p
            ]
        except Exception:
            rows_p = []

        valid_ids, invalid_fakturi = _split_valid_by_faktura(rows_p, set(ids))

        if invalid_fakturi:
            results.append({
                "polisa":     polisa,
                "code":       -1,
                "msg":        "Избраните ставки за фактура(и) " + ", ".join(invalid_fakturi)
                              + " не се балансирани на нула и не се затворени.",
                "uu_broj":    None,
                "knizi_msg":  None,
                "knizi_warn": None,
            })
        if not valid_ids:
            continue

        code, msg, hid = _call_uu(valid_ids, datum, user_id)
        entry = {
            "polisa":      polisa,
            "code":        code,
            "msg":         msg,
            "uu_broj":     None,
            "knizi_msg":   None,
            "knizi_warn":  None,
        }
        if code == 1 and hid:
            k_code, k_msg = _call_knizi(hid, user_id)
            try:
                entry["uu_broj"] = msg.split(": ", 1)[1].split(" (")[0].strip()
            except Exception:
                pass
            if k_code == 1:
                entry["knizi_msg"] = k_msg
            else:
                entry["knizi_warn"] = k_msg
        results.append(entry)

    # Re-query the remaining individual invoices
    rows, grouped, error = [], [], None
    try:
        sql, params = _build_individual_sql(tip_polisa, klient, f_polisa_broj, datum_od, datum_do)
        raw = _query(sql, params)
        rows = [
            {
                "os_aneks_fakturaid": r[0],
                "polisa_broj":        r[1],
                "client_id":          r[2],
                "ime_prezime":        r[3],
                "faktura_broj":       r[4],
                "data_faktura":       r[5],
                "iznos":              float(r[6] or 0),
            }
            for r in raw
        ]
        grouped = _group_by_faktura(rows)
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse("kolektivno_uu.html", {
        "request":       request,
        "user":          user,
        "active":        "kolektivno_uu",
        "rows":          rows,
        "grouped":       grouped,
        "detail":        None,
        "detail_polisa": None,
        "error":         error,
        "success":       None,
        "results":       results,
        "today_str":     date.today().isoformat(),
        "searched":      True,
        "f_klient":      klient,
        "f_polisa_broj": f_polisa_broj,
        "f_tip_polisa":  tip_polisa,
        "f_datum_od":    datum_od,
        "f_datum_do":    datum_do,
        "f_dospeana":    "",
    })


# ------------------------------------------------------------------
# GET /kolektivno-uu/excel  — Excel export of a closed УУ document
# ------------------------------------------------------------------
def _build_uu_excel(rows: list, polisa_broj: str, uu_broj: str, datum_str: str) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "УУ Извод"

    # ── Styles ────────────────────────────────────────────────────
    header_fill   = PatternFill("solid", fgColor="1A3A5C")
    header_font   = Font(color="FFFFFF", bold=True, name="Calibri", size=10)
    title_font    = Font(bold=True, size=12, name="Calibri")
    total_font    = Font(bold=True, name="Calibri", size=10)
    normal_font   = Font(name="Calibri", size=10)
    pos_font      = Font(name="Calibri", size=10, color="1E8449")
    neg_font      = Font(name="Calibri", size=10, color="C0392B")
    center_align  = Alignment(horizontal="center", vertical="center")
    right_align   = Alignment(horizontal="right",  vertical="center")
    left_align    = Alignment(horizontal="left",   vertical="center")
    thin          = Side(border_style="thin", color="CCCCCC")
    thin_border   = Border(top=thin, bottom=thin, left=thin, right=thin)

    num_fmt = '#,##0.00'

    # ── Header block ──────────────────────────────────────────────
    ws.merge_cells("A1:D1")
    ws["A1"] = "СИГАЛ ЛАЈФ – УУ Усогласување на уплати"
    ws["A1"].font = title_font

    ws["A2"] = "Извод:"
    ws["B2"] = uu_broj
    ws["B2"].font = Font(bold=True, name="Calibri", size=10)

    ws["A3"] = "Датум:"
    ws["B3"] = datum_str

    ws["A4"] = "Полиса:"
    ws["B4"] = polisa_broj

    ws.append([])

    # ── Column headers ────────────────────────────────────────────
    col_headers = ["Фактура", "Датум на фактура", "Износ (ориг.)", "Износ (МКД)", "Нaплата"]
    ws.append(col_headers)
    hdr_row = ws.max_row
    for col_idx, _ in enumerate(col_headers, 1):
        cell = ws.cell(hdr_row, col_idx)
        cell.fill       = header_fill
        cell.font       = header_font
        cell.alignment  = center_align
        cell.border     = thin_border

    # ── Data rows ─────────────────────────────────────────────────
    sum_iznos      = 0.0
    sum_iznos_den  = 0.0
    sum_naplata    = 0.0

    for r in rows:
        iznos         = float(r["iznos"]         or 0)
        iznos_den     = float(r["iznos_den"]     or 0)
        iznos_naplata = float(r["iznos_naplata"] or 0)
        sum_iznos     += iznos
        sum_iznos_den += iznos_den
        sum_naplata   += iznos_naplata

        dat = r["data_faktura"]
        dat_str = dat.strftime("%d.%m.%Y") if hasattr(dat, "strftime") else str(dat or "")

        ws.append([r["faktura_broj"], dat_str, iznos, iznos_den, iznos_naplata])
        dr = ws.max_row
        num_font = pos_font if iznos >= 0 else neg_font
        for ci in range(1, 6):
            c = ws.cell(dr, ci)
            c.font      = num_font
            c.border    = thin_border
            c.alignment = right_align if ci >= 3 else left_align
            if ci >= 3:
                c.number_format = num_fmt

    # ── Total row ─────────────────────────────────────────────────
    total_fill = PatternFill("solid", fgColor="D5E8D4")
    ws.append(["ВКУПНО", "", sum_iznos, sum_iznos_den, sum_naplata])
    tr = ws.max_row
    for ci in range(1, 6):
        c = ws.cell(tr, ci)
        c.font      = total_font
        c.fill      = total_fill
        c.border    = thin_border
        c.alignment = right_align if ci >= 3 else left_align
        if ci >= 3:
            c.number_format = num_fmt

    # ── Note row ──────────────────────────────────────────────────
    ws.append([])
    note_row = ws.max_row + 1
    ws.cell(note_row, 1, "Нето салдо (треба да биде 0):")
    ws.cell(note_row, 3, round(sum_iznos, 2)).number_format = num_fmt
    ws.cell(note_row, 3).font = Font(bold=True, name="Calibri", size=10,
                                     color="C0392B" if abs(sum_iznos) > 0.01 else "1E8449")

    # ── Column widths ─────────────────────────────────────────────
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@router.get("/kolektivno-uu/excel")
async def kolektivno_uu_excel(
    request: Request,
    polisa_broj: str = Query(...),
    uu_broj:     str = Query(...),
    datum_uu:    str = Query(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    try:
        raw = _query(_SQL_ANEKSI_PER_POLISA, [polisa_broj])
        rows = [
            {
                "faktura_broj":  r[0],
                "data_faktura":  r[1],
                "iznos":         float(r[2] or 0),
                "iznos_den":     float(r[3] or 0),
                "iznos_naplata": float(r[4] or 0),
            }
            for r in raw
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    buf = _build_uu_excel(rows, polisa_broj, uu_broj, datum_uu or date.today().isoformat())
    safe_polisa = polisa_broj.replace("/", "-")
    filename = f"UU_{safe_polisa}_{(datum_uu or date.today().isoformat()).replace('-', '')}.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

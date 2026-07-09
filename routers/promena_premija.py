from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from auth.role_utils import has_any_role
from routers import Connection
import os, datetime

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)

_ALLOWED_ROLES = ["admin", "promena_premija"]

TIPOVI_PROMENA = [
    ("premija_kolektivno", "Промена на премија на Фактура Колективно"),
]

_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "promena_premija_log.txt")

_FAKTURA_EXPR = "(x1.os_aneks || '/' || vesna.vrati_godina(x1.par_yearid) || '-' || x0.rata)"


def _require_role(request: Request):
    user = request.session.get("user")
    if not user:
        return None, RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, *_ALLOWED_ROLES):
        raise HTTPException(status_code=403, detail="Немате пристап.")
    return user, None


def _s(v) -> str:
    return (v or "").strip()


def _fmt_date(v):
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%d.%m.%Y")
    s = str(v)[:10]
    if len(s) == 10 and s[4] == '-':
        return s[8:10] + '.' + s[5:7] + '.' + s[:4]
    return s


def _fetch_fakturi(polisa_broj: str):
    cursor, ok = Connection.OSISinit()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        sql = f"""
            SELECT
                x0.os_aneks_fakturaid,
                {_FAKTURA_EXPR} AS faktura,
                x0.data_faktura, x0.data_valuta,
                vesna.vrati_tip_knizi(x0.par_tip_kniziid) AS tip_knizi,
                NVL(x0.iznos,0)         AS iznos,
                NVL(x0.iznos_denari,0)  AS iznos_denari,
                NVL(vesna.vrati_naplata(x0.os_aneks_fakturaid),0) AS naplata
            FROM viki.os_aneks_faktura x0
            JOIN viki.os_aneks x1  ON x0.os_aneksid = x1.os_aneksid
            JOIN viki.os_polisa x2 ON x2.os_polisaid = x1.os_polisaid
            WHERE UPPER(x2.polisa_broj_cel) = ?
            ORDER BY x0.data_faktura, faktura, x0.rata
        """
        cursor.execute(sql, [polisa_broj.strip().upper()])
        raw = cursor.fetchall()
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    rows = []
    for r in raw:
        rows.append({
            "os_aneks_fakturaid": int(r[0]),
            "faktura":            r[1] or "",
            "data_faktura":       _fmt_date(r[2]),
            "data_valuta":        _fmt_date(r[3]),
            "tip_knizi":          r[4] or "",
            "iznos":              float(r[5] or 0),
            "iznos_denari":       float(r[6] or 0),
            "naplata":            float(r[7] or 0),
        })
    return rows


def _update_premija(os_aneks_fakturaid: int, nov_iznos: float, nov_iznos_denari: float, user_name: str):
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        cursor.execute(
            "SELECT NVL(iznos,0), NVL(iznos_denari,0) FROM viki.os_aneks_faktura WHERE os_aneks_fakturaid = ?",
            [os_aneks_fakturaid]
        )
        before = cursor.fetchone()
        if not before:
            raise RuntimeError("Фактурата не е пронајдена.")
        star_iznos, star_iznos_denari = float(before[0] or 0), float(before[1] or 0)

        cursor.execute(
            "UPDATE viki.os_aneks_faktura SET iznos = ?, iznos_denari = ? WHERE os_aneks_fakturaid = ?",
            [nov_iznos, nov_iznos_denari, os_aneks_fakturaid]
        )
        cursor.execute(
            "UPDATE viki.fin_stavka SET iznos_d = ?, iznos_d_den = ? "
            "WHERE os_aneks_fakturaid = ? AND iznos_d IS NOT NULL",
            [nov_iznos, nov_iznos_denari, os_aneks_fakturaid]
        )

        try:
            conn.commit()
        except Exception:
            pass

        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().isoformat(timespec='seconds')}] user={user_name} "
                f"os_aneks_fakturaid={os_aneks_fakturaid} "
                f"iznos: {star_iznos} -> {nov_iznos} | iznos_denari: {star_iznos_denari} -> {nov_iznos_denari}\n"
            )

        return star_iznos, star_iznos_denari
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _render(request, user, polisa_broj, tip_promena, rows, error, success):
    return templates.TemplateResponse("promena_premija.html", {
        "request":     request,
        "user":        user,
        "active":      "promena_premija",
        "tipovi":      TIPOVI_PROMENA,
        "polisa_broj": polisa_broj,
        "tip_promena": tip_promena,
        "rows":        rows,
        "error":       error,
        "success":     success,
    })


@router.get("/promena-premija")
def promena_premija_get(request: Request):
    user, redirect = _require_role(request)
    if redirect:
        return redirect
    return _render(request, user, "", TIPOVI_PROMENA[0][0], None, None, None)


@router.post("/promena-premija/search")
def promena_premija_search(
    request:     Request,
    polisa_broj: str = Form(...),
    tip_promena: str = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    rows, error = None, None
    try:
        rows = _fetch_fakturi(polisa_broj)
        if not rows:
            error = "Нема пронајдени фактури за оваа полиса."
    except Exception as e:
        error = str(e)

    return _render(request, user, polisa_broj, tip_promena, rows, error, None)


@router.post("/promena-premija/save")
def promena_premija_save(
    request:            Request,
    polisa_broj:        str = Form(...),
    tip_promena:        str = Form(...),
    os_aneks_fakturaid: int = Form(...),
    nov_iznos:          float = Form(...),
    nov_iznos_denari:   float = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    try:
        star_iznos, star_iznos_denari = _update_premija(
            os_aneks_fakturaid, nov_iznos, nov_iznos_denari, user_name
        )
        success = (
            f"Фактурата е успешно ажурирана. Износ: {star_iznos:.2f} → {nov_iznos:.2f}, "
            f"Износ (ден.): {star_iznos_denari:.2f} → {nov_iznos_denari:.2f}"
        )
    except Exception as e:
        error = str(e)

    rows = None
    try:
        rows = _fetch_fakturi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, rows, error, success)

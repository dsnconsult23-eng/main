from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from auth.role_utils import has_any_role
from routers import Connection
import os
from datetime import date

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)

_ALLOWED_ROLES = ["admin", "kontrola_polisi"]


def _require_role(request: Request):
    user = request.session.get("user")
    if not user:
        return None, RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, *_ALLOWED_ROLES):
        raise HTTPException(status_code=403, detail="Немате пристап.")
    return user, None


def _run(sql, params=None):
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


# ------------------------------------------------------------------
# Проверка 1: капитализирана полиса (со максимален podbroj) → вкупното
# салдо по полиса (сума од сите фактури: износ - наплата) треба да е 0.
# Наплатата се зема преку vrati_naplata() UDF (иста логика како
# sql/zatvori_izvod.sql), не преку рачен fin_stavka join.
#
# Статусот (капитализирана или не) се утврдува преку максималниот podbroj
# на ПОСЛЕДНАТА понуда (par_statusid=18), но долгот/салдото се собира
# преку СИТЕ os_polisa записи што делат ист polisa_broj_cel — истата
# полиса може да има повеќе os_polisaid верзии низ времето (пред/по
# замена или капитализација), а долгот и наплатата се распределени низ
# нив. Ако се гледа само во os_polisaid на капитализираната верзија, се
# добива лажно ненулто салдо (веќе порамнетите фактури од претходната
# верзија остануваат надвор од пресметката).
#
# Секоја фактура мора да има поврзан fin_stavka ред (iznos_d IS NOT NULL)
# кој не е сторниран (f_rs <> 'N') — истиот услов како во "Преглед на
# фактури" (report_fakturi.py _BASE_FROM). Фактури чиј fin_stavka ред е
# означен со f_rs='N' (или воопшто го нема) не влегуваат во сметководствен
# промет и мора да се исклучат, инаку салдото испаѓа лажно ненулто.
# ------------------------------------------------------------------
def check_kapitalizirana_faktura_nula():
    sql = """
        SELECT p.polisa_broj_cel,
               SUM(NVL(f.iznos,0)) AS vk_iznos,
               SUM(NVL(vrati_naplata(f.os_aneks_fakturaid),0)) AS vk_naplata,
               SUM(NVL(f.iznos,0) - NVL(vrati_naplata(f.os_aneks_fakturaid),0)) AS saldo
        FROM os_polisa p
        JOIN os_aneks a         ON a.os_polisaid = p.os_polisaid
        JOIN os_aneks_faktura f ON f.os_aneksid  = a.os_aneksid
        JOIN fin_stavka x3      ON x3.os_aneks_fakturaid = f.os_aneks_fakturaid AND x3.iznos_d IS NOT NULL
        WHERE NVL(x3.f_rs,'R') <> 'N'
          AND p.polisa_broj_cel IN (
            SELECT p2.polisa_broj_cel
            FROM os_ponuda o2
            JOIN os_polisa p2 ON p2.os_ponudaid = o2.os_ponudaid
            WHERE o2.par_statusid = 18
              AND o2.ponuda_podbroj = maxpodbroj_datum(o2.ponuda_broj, p2.polisa_broj, o2.os_produktid, TODAY)
        )
        GROUP BY p.polisa_broj_cel
        HAVING ROUND(SUM(NVL(f.iznos,0) - NVL(vrati_naplata(f.os_aneks_fakturaid),0)), 2) <> 0
    """
    rows = _run(sql)
    return [
        {
            "polisa_broj": r[0],
            "vk_iznos": float(r[1] or 0),
            "vk_naplata": float(r[2] or 0),
            "saldo": float(r[3] or 0),
        }
        for r in rows
    ]


# ------------------------------------------------------------------
# Проверка 2: обновена полиса → провери дали ги има сите фактури изгенерирано.
# Статусот се зема од ПОСЛЕДНАТА понуда (maxpodbroj), не било кој ponuda ред,
# и се исклучуваат раскинати/сторнирани (42) и капитализирани (18) полиси.
# Исклучени и полисите со префикс "19/" (не подлежат на оваа проверка) —
# иста логика како проверка 3.
# ------------------------------------------------------------------
def check_obnovena_nedostasuvaat_fakturi(godina):
    sql = """
        SELECT p.polisa_broj_cel, a.os_aneks, vrati_godina(a.par_yearid), a.br_rati,
               COUNT(f.os_aneks_fakturaid)
        FROM os_polisa p
        JOIN os_ponuda o ON o.os_ponudaid = p.os_ponudaid
        JOIN os_aneks a ON a.os_polisaid = p.os_polisaid
        LEFT JOIN os_aneks_faktura f ON f.os_aneksid = a.os_aneksid
        WHERE p.status_polisa = 'K'
          AND o.ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, p.polisa_broj, o.os_produktid, TODAY)
          AND o.par_statusid NOT IN (42, 18)
          AND p.polisa_broj_cel NOT LIKE '19/%'
          AND vrati_godina(a.par_yearid) = ?
        GROUP BY 1, 2, 3, 4
        HAVING COUNT(f.os_aneks_fakturaid) < a.br_rati
    """
    rows = _run(sql, [godina])
    return [
        {"polisa_broj": r[0], "aneks": r[1], "godina": r[2], "br_rati": r[3], "br_generirani": r[4]}
        for r in rows
    ]


# ------------------------------------------------------------------
# Проверка 3: активна полиса → провери дали се изгенерирани сите фактури
# за анексот (без разлика дали се веќе доспеани — фактурите обично се
# генерираат однапред за целата година, па data_faktura < TODAY погрешно
# ги исклучувал веќе-генерираните идни рати и лажно ги пријавувал како
# "недостасуваат").
# Не важи за полиси со еднократна премија (os_produkt_uplata.par_nacin_platiid = 75).
# Исклучени и полисите со префикс "19/" (не подлежат на оваа проверка).
# ------------------------------------------------------------------
def check_aktivna_nedostasuvaat_fakturi(godina):
    sql = """
        SELECT p.polisa_broj_cel, a.os_aneks, vrati_godina(a.par_yearid), a.br_rati,
               COUNT(f.os_aneks_fakturaid)
        FROM os_polisa p
        JOIN os_ponuda o ON o.os_ponudaid = p.os_ponudaid
        JOIN os_produkt_uplata pu ON pu.os_produkt_uplataid = o.os_produkt_uplataid
        JOIN os_aneks a  ON a.os_polisaid = p.os_polisaid
        LEFT JOIN os_aneks_faktura f
               ON f.os_aneksid = a.os_aneksid
        WHERE p.status_polisa = 'K'
          AND o.ponuda_podbroj = maxpodbroj_datum(o.ponuda_broj, p.polisa_broj, o.os_produktid, TODAY)
          AND o.par_statusid IN (17,18)
          AND pu.par_nacin_platiid <> 75
          AND p.polisa_broj_cel NOT LIKE '19/%'
          AND vrati_godina(a.par_yearid) = ?
        GROUP BY 1, 2, 3, 4
        HAVING COUNT(f.os_aneks_fakturaid) < a.br_rati
    """
    rows = _run(sql, [godina])
    return [
        {"polisa_broj": r[0], "aneks": r[1], "godina": r[2], "br_rati": r[3], "br_generirani": r[4]}
        for r in rows
    ]


# ------------------------------------------------------------------
# Проверка 4: фактури со наплата поголема од износот на фактурата.
# Наплатата се зема преку vrati_naplata() UDF, не преку рачен fin_stavka join.
# Собрано на НИВО НА ФАКТУРА (aneks + година + рата), не по одделен
# os_aneks_fakturaid ред — иста логика на групирање како _FAKTURA_EXPR во
# report_fakturi.py. Истата "фактура" (истиот aneks/година-рата) може да
# има повеќе os_aneks_faktura записи (оригинал + сторно/корекција), па
# споредбата per-ред лажно пријавува нарушување иако вкупниот салдо за
# таа фактура е во ред.
# ------------------------------------------------------------------
def check_naplata_pogolema_od_faktura():
    sql = """
        SELECT FIRST 5000
               p.polisa_broj_cel,
               MAX(c.desc) AS client_naziv,
               UPPER((a.os_aneks || '/' || TRIM(vrati_godina(a.par_yearid)) || '-' || f.rata)) AS faktura,
               MAX(f.data_faktura) AS data_faktura,
               SUM(NVL(f.iznos,0)) AS iznos,
               SUM(NVL(vrati_naplata(f.os_aneks_fakturaid),0)) AS naplata
        FROM os_aneks_faktura f
        JOIN os_aneks a   ON a.os_aneksid  = f.os_aneksid
        JOIN os_polisa p  ON p.os_polisaid = a.os_polisaid
        JOIN par_client c ON c.par_clientid = a.par_clientid
        GROUP BY 1, 3
        HAVING SUM(NVL(vrati_naplata(f.os_aneks_fakturaid),0)) > SUM(NVL(f.iznos,0))
        ORDER BY 1, 4
    """
    rows = _run(sql)
    return [
        {
            "polisa_broj": r[0], "client_naziv": r[1], "faktura": r[2],
            "data_faktura": str(r[3]) if r[3] is not None else "",
            "iznos": float(r[4] or 0), "naplata": float(r[5] or 0),
        }
        for r in rows
    ]


def _render(request, user, godina, results, error):
    return templates.TemplateResponse("kontrola_polisi.html", {
        "request": request,
        "user": user,
        "active": "kontrola_polisi",
        "godina": godina,
        "results": results,
        "error": error,
        "searched": results is not None,
    })


@router.get("/kontrola-polisi")
async def kontrola_polisi_get(request: Request):
    user, redirect = _require_role(request)
    if redirect:
        return redirect
    return _render(request, user, date.today().year, None, None)


@router.post("/kontrola-polisi")
def kontrola_polisi_post(request: Request, godina: int = Form(...)):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    checks = [
        ("kapitalizirana_faktura_nula", lambda: check_kapitalizirana_faktura_nula()),
        ("obnovena_nedostasuvaat", lambda: check_obnovena_nedostasuvaat_fakturi(godina)),
        ("aktivna_nedostasuvaat", lambda: check_aktivna_nedostasuvaat_fakturi(godina)),
        ("naplata_pogolema_od_faktura", lambda: check_naplata_pogolema_od_faktura()),
    ]

    results = {}
    for key, fn in checks:
        try:
            results[key] = fn()
        except Exception as e:
            print(f"[KONTROLA_POLISI] {key} failed: {e}")
            results[key] = {"error": str(e)}

    return _render(request, user, godina, results, None)

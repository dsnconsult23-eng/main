from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException
from auth.role_utils import has_any_role
from routers import Connection
from typing import List, Optional
import io, os, datetime, openpyxl
import jpype
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)

_ALLOWED_ROLES = ["admin", "aso_reports", "finansii", "finance", "report_fakturi"]

_PDF_FONT_DIR = os.path.dirname(__file__)
try:
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_PDF_FONT_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_PDF_FONT_DIR, "DejaVuSans-Bold.ttf")))
except Exception:
    pass  # веројатно веќе регистрирани од друг router (GeneratePDFOpomeni.py итн.)

PRODAZNI_KANALI = [
    "Банки",
    "Директна продажба",
    "Друштва за застапување во осигурување",
    "Застапници во осигурување",
    "Осиг.Брокерски друштва",
    "Промотор",
]


def _require_role(request: Request):
    user = request.session.get("user")
    if not user:
        return None, RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, *_ALLOWED_ROLES):
        raise HTTPException(status_code=403, detail="Немате пристап.")
    return user, None


def _s(v) -> str:
    return (v or "").strip()


def _to_db_date(v):
    # HTML5 <input type="date"> праќа ISO string ("YYYY-MM-DD"). jaydebeapi не знае
    # автоматски да bind-ира Python datetime.date, а плаин string го фаќа локалниот
    # date-format на Informix (DBDATE=MDY4/, т.е. mm/dd/yyyy), па филтрите молчешкум
    # не работат исправно. Затоа праќаме вистински java.sql.Date, чиј valueOf()
    # секогаш очекува "yyyy-mm-dd", независно од Informix locale.
    if v is None or v == "":
        return None
    if isinstance(v, datetime.date):
        d = v
    else:
        try:
            d = datetime.datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
        except Exception:
            return None
    JavaDate = jpype.JClass("java.sql.Date")
    return JavaDate.valueOf(d.strftime("%Y-%m-%d"))


# ------------------------------------------------------------------
# Директен join на основните табели (истата логика како
# vesna.report_fakturi view — види Utils/db_views_reference.py) —
# СВЕСНО не ја користиме самата view, бидејќи view-то пресметува ~15
# UDF повици (име клиент, наплата, брокер, агент...) за СЕКОЈ ред
# ПРЕД да се примени нашиот WHERE филтер, што го прави пребарувањето
# многу бавно дури и со тесни филтри. Овде филтрите се на суровите
# join-нати колони, а UDF-повиците (само наплата/фактура/тип книжи)
# се пресметуваат дури откако филтрите веќе го намалиле бројот редови.
# ------------------------------------------------------------------
_BASE_FROM = """
    FROM viki.os_aneks_faktura x0
    JOIN viki.os_aneks x1  ON x0.os_aneksid = x1.os_aneksid
    JOIN viki.os_polisa x2 ON x2.os_polisaid = x1.os_polisaid
    JOIN viki.fin_stavka x3 ON x3.os_aneks_fakturaid = x0.os_aneks_fakturaid AND x3.iznos_d IS NOT NULL
    JOIN viki.os_ponuda x4 ON x4.os_ponudaid = x2.os_ponudaid
    JOIN vesna.par_client pc ON pc.par_clientid =
        CASE WHEN x4.par_tip_platiid != 36 THEN x1.par_clientid ELSE x4.dogovoruvac_par_client END
    LEFT JOIN vesna.par_client azc  ON azc.par_clientid = x4.banka_par_client
    LEFT JOIN vesna.par_client brk  ON brk.par_clientid = x4.broker_par_client
    LEFT JOIN vesna.par_client psr  ON psr.par_clientid = x4.posrednik_par_client
    LEFT JOIN par_agent agt         ON agt.par_agentid  = x4.par_agentid
    LEFT JOIN par_agent prm         ON prm.par_agentid  = x4.promotor_par_agent
    LEFT JOIN par_prod_kanal pk     ON pk.par_prod_kanalid = x4.par_prod_kanalid
"""
_FAKTURA_EXPR = "(x1.os_aneks || '/' || vesna.vrati_godina(x1.par_yearid) || '-' || x0.rata)"
_DATUM_ANEKS_EXPR = "CASE WHEN (x0.f_rs = 'S' AND x4.datecreated > x1.datum_aneks) THEN x4.datecreated ELSE x1.datum_aneks END"
_TIP_KNIZI_EXPR = "vesna.vrati_tip_knizi(x0.par_tip_kniziid)"
_NAPLATA_EXPR = "vesna.vrati_naplata(x0.os_aneks_fakturaid)"
_NAPLATA_DEN_EXPR = "vesna.vrati_naplata_den(x0.os_aneks_fakturaid)"


def _build_sql(f: dict, nivo: str):
    where, params = [], []

    def add(cond, val):
        where.append(cond)
        params.append(val)

    if _s(f.get("klient")):
        add("AND UPPER(pc.desc) LIKE ?", "%" + _s(f["klient"]).upper() + "%")
    if _s(f.get("faktura")):
        add(f"AND UPPER({_FAKTURA_EXPR}) LIKE ?", "%" + _s(f["faktura"]).upper() + "%")
    if _s(f.get("tip_knizi")):
        add(f"AND UPPER({_TIP_KNIZI_EXPR}) LIKE ?", "%" + _s(f["tip_knizi"]).upper() + "%")
    polisa_raw = _s(f.get("polisa_broj"))
    if polisa_raw:
        polisas = [p.strip() for p in polisa_raw.replace(";", ",").split(",") if p.strip()]
        if len(polisas) == 1:
            add("AND UPPER(x2.polisa_broj_cel) LIKE ?", "%" + polisas[0].upper() + "%")
        elif len(polisas) > 1:
            conds = " OR ".join(["UPPER(x2.polisa_broj_cel) LIKE ?" for _ in polisas])
            where.append(f"AND ({conds})")
            params.extend(["%" + p.upper() + "%" for p in polisas])
    if _s(f.get("iznos_od")):
        add("AND x0.iznos >= ?", _s(f["iznos_od"]))
    if _s(f.get("iznos_do")):
        add("AND x0.iznos <= ?", _s(f["iznos_do"]))
    if _s(f.get("iznos_den_od")):
        add("AND x0.iznos_denari >= ?", _s(f["iznos_den_od"]))
    if _s(f.get("iznos_den_do")):
        add("AND x0.iznos_denari <= ?", _s(f["iznos_den_do"]))
    if _s(f.get("naplata_od")):
        add(f"AND {_NAPLATA_EXPR} >= ?", _s(f["naplata_od"]))
    if _s(f.get("naplata_do")):
        add(f"AND {_NAPLATA_EXPR} <= ?", _s(f["naplata_do"]))
    if _s(f.get("naplata_den_od")):
        add(f"AND {_NAPLATA_DEN_EXPR} >= ?", _s(f["naplata_den_od"]))
    if _s(f.get("naplata_den_do")):
        add(f"AND {_NAPLATA_DEN_EXPR} <= ?", _s(f["naplata_den_do"]))
    if _s(f.get("datum_aneks_od")):
        add(f"AND {_DATUM_ANEKS_EXPR} >= ?", _to_db_date(f["datum_aneks_od"]))
    if _s(f.get("datum_aneks_do")):
        add(f"AND {_DATUM_ANEKS_EXPR} <= ?", _to_db_date(f["datum_aneks_do"]))
    if _s(f.get("datum_valuta_od")):
        add("AND x0.data_valuta >= ?", _to_db_date(f["datum_valuta_od"]))
    if _s(f.get("datum_valuta_do")):
        add("AND x0.data_valuta <= ?", _to_db_date(f["datum_valuta_do"]))
    if _s(f.get("datum_faktura_od")):
        add("AND x0.data_faktura >= ?", _to_db_date(f["datum_faktura_od"]))
    if _s(f.get("datum_faktura_do")):
        add("AND x0.data_faktura <= ?", _to_db_date(f["datum_faktura_do"]))
    if _s(f.get("datum_knizi_od")):
        add("AND x3.dat_nalog >= ?", _to_db_date(f["datum_knizi_od"]))
    if _s(f.get("datum_knizi_do")):
        add("AND x3.dat_nalog <= ?", _to_db_date(f["datum_knizi_do"]))
    if _s(f.get("broker")):
        add("AND UPPER(brk.desc) LIKE ?", "%" + _s(f["broker"]).upper() + "%")
    if _s(f.get("agent")):
        add("AND UPPER(agt.desc) LIKE ?", "%" + _s(f["agent"]).upper() + "%")
    if _s(f.get("posrednik")):
        add("AND UPPER(psr.desc) LIKE ?", "%" + _s(f["posrednik"]).upper() + "%")
    if _s(f.get("promotor")):
        add("AND UPPER(prm.desc) LIKE ?", "%" + _s(f["promotor"]).upper() + "%")
    if f.get("dospeana"):
        where.append(f"AND (NVL(x0.iznos,0) - NVL({_NAPLATA_EXPR},0)) > 0.005")
        if not _s(f.get("datum_faktura_do")):
            where.append("AND x0.data_faktura <= ?")
            params.append(_to_db_date(datetime.date.today()))

    klient_tip = _s(f.get("klient_tip"))
    if klient_tip == "Физичко":
        add("AND pc.client_tip_pf = ?", "F")
    elif klient_tip == "Правно":
        add("AND pc.client_tip_pf = ?", "P")

    kanali = f.get("kanali") or []
    if kanali:
        ph = ", ".join(["?" for _ in kanali])
        where.append(f"AND pk.desc_mk IN ({ph})")
        params.extend(kanali)

    if _s(f.get("admin_zabrana_klient")):
        add("AND UPPER(azc.desc) LIKE ?", "%" + _s(f["admin_zabrana_klient"]).upper() + "%")
    elif f.get("samo_admin_zabrana"):
        where.append("AND x4.banka_par_client IS NOT NULL")

    w = " ".join(where)

    if nivo == "polisa":
        sql = f"""
SELECT FIRST 2000
    x2.polisa_broj_cel AS polisa_broj,
    MAX(pc.desc) AS client_naziv,
    SUM(NVL(x0.iznos,0))         AS vk_iznos,
    SUM(NVL(x0.iznos_denari,0))  AS vk_iznos_den,
    SUM(NVL({_NAPLATA_EXPR},0))  AS vk_naplata,
    SUM(NVL({_NAPLATA_DEN_EXPR},0)) AS vk_naplata_den,
    SUM(NVL(x0.iznos,0) - NVL({_NAPLATA_EXPR},0)) AS saldo,
    MAX(azc.desc) AS admin_zabrana_naziv
{_BASE_FROM}
WHERE NVL(x3.f_rs,'R') <> 'N' {w}
GROUP BY x2.polisa_broj_cel, x2.os_polisaid
ORDER BY x2.polisa_broj_cel
"""
    elif nivo == "faktura":
        sql = f"""
SELECT FIRST 2000
    x2.polisa_broj_cel AS polisa_broj,
    MAX(pc.desc) AS client_naziv,
    {_FAKTURA_EXPR} AS faktura,
    x0.data_faktura,
    MAX({_TIP_KNIZI_EXPR}) AS tip_knizi,
    SUM(NVL(x0.iznos,0))         AS vk_iznos,
    SUM(NVL(x0.iznos_denari,0))  AS vk_iznos_den,
    SUM(NVL({_NAPLATA_EXPR},0))  AS vk_naplata,
    SUM(NVL({_NAPLATA_DEN_EXPR},0)) AS vk_naplata_den,
    SUM(NVL(x0.iznos,0) - NVL({_NAPLATA_EXPR},0)) AS saldo
{_BASE_FROM}
WHERE NVL(x3.f_rs,'R') <> 'N' {w}
GROUP BY 1, x2.os_polisaid, 3, 4
ORDER BY x2.polisa_broj_cel, x0.data_faktura, faktura
"""
    else:  # red
        sql = f"""
SELECT FIRST 2000
    x2.polisa_broj_cel AS polisa_broj,
    pc.desc AS client_naziv,
    {_FAKTURA_EXPR} AS faktura,
    x0.rata,
    x0.data_faktura, x0.data_valuta,
    {_TIP_KNIZI_EXPR} AS tip_knizi,
    NVL(x0.iznos,0)         AS iznos,
    NVL(x0.iznos_denari,0)  AS iznos_den,
    NVL({_NAPLATA_EXPR},0)      AS naplata,
    NVL({_NAPLATA_DEN_EXPR},0)  AS naplata_den,
    NVL(x0.iznos,0) - NVL({_NAPLATA_EXPR},0) AS saldo,
    brk.desc AS broker_name, agt.desc AS par_agent_name, psr.desc AS posrednik_name, pk.desc_mk AS prodazen_kanal
{_BASE_FROM}
WHERE NVL(x3.f_rs,'R') <> 'N' {w}
ORDER BY x2.polisa_broj_cel, x0.data_faktura, faktura, x0.rata
"""
    return sql, params


def _run_query(sql, params):
    cursor, ok = Connection.OSISinit()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        try:
            cursor.close()
        except Exception:
            pass


def _resolve_polisa_group(polisa_broj: str) -> list:
    """
    Итеративно ги наоѓа сите поврзани полиси (синџири на замени, може 3+).
    За секоја новопронајдена полиса проверува и двете насоки:
      1. polisa_zamena на таа полиса (напред во синџирот)
      2. полиси чиј polisa_zamena покажува кон неа (назад во синџирот)
    Повторува додека не се пронајдат нови полиси.
    """
    found = {polisa_broj.strip()}
    queue = list(found)
    try:
        cursor, ok = Connection.OSISinit()
        if not ok or cursor is None:
            return list(found)
        try:
            while queue:
                pb = queue.pop(0)
                # насока напред: замената на оваа полиса
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
                # насока назад: полиси кои ја имаат оваа kako zamena
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
        finally:
            try:
                cursor.close()
            except Exception:
                pass
    except Exception:
        pass
    return sorted(found)


def _auto_expand_polisa(filters: dict):
    """
    Ако е внесена само ЕДНА полиса (без запирка), автоматски ги бара
    поврзаните полиси (оригинал ↔ замена) и ги додава во filters['polisa_broj'].
    """
    pb = _s(filters.get("polisa_broj"))
    if not pb or "," in pb or ";" in pb:
        return
    group = _resolve_polisa_group(pb)
    if len(group) > 1:
        filters["polisa_broj"] = ", ".join(group)


def _fmt_date(v):
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%d.%m.%Y")
    s = str(v)[:10]
    if len(s) == 10 and s[4] == '-':
        return s[8:10] + '.' + s[5:7] + '.' + s[:4]
    return s


def _to_rows_polisa(raw):
    rows = []
    tot = {"vk_iznos": 0, "vk_iznos_den": 0, "vk_naplata": 0, "vk_naplata_den": 0, "saldo": 0}
    for r in raw:
        row = {
            "polisa_broj":    r[0] or "",
            "client_naziv":   r[1] or "",
            "vk_iznos":       float(r[2] or 0),
            "vk_iznos_den":   float(r[3] or 0),
            "vk_naplata":     float(r[4] or 0),
            "vk_naplata_den": float(r[5] or 0),
            "saldo":          float(r[6] or 0),
            "admin_zabrana_naziv": r[7] or "",
        }
        rows.append(row)
        for k in tot:
            tot[k] += row[k]
    return rows, tot


def _to_rows_faktura(raw):
    rows = []
    tot = {"vk_iznos": 0, "vk_iznos_den": 0, "vk_naplata": 0, "vk_naplata_den": 0, "saldo": 0}
    for r in raw:
        row = {
            "polisa_broj":    r[0] or "",
            "client_naziv":   r[1] or "",
            "faktura":        r[2] or "",
            "data_faktura":   _fmt_date(r[3]),
            "tip_knizi":      r[4] or "",
            "vk_iznos":       float(r[5] or 0),
            "vk_iznos_den":   float(r[6] or 0),
            "vk_naplata":     float(r[7] or 0),
            "vk_naplata_den": float(r[8] or 0),
            "saldo":          float(r[9] or 0),
        }
        rows.append(row)
        for k in tot:
            if k in row:
                tot[k] += row[k]
    return rows, tot


def _to_rows_red(raw):
    rows = []
    tot = {"iznos": 0, "iznos_den": 0, "naplata": 0, "naplata_den": 0, "saldo": 0}
    for r in raw:
        row = {
            "polisa_broj":  r[0] or "",
            "client_naziv": r[1] or "",
            "faktura":      r[2] or "",
            "rata":         r[3],
            "data_faktura": _fmt_date(r[4]),
            "data_valuta":  _fmt_date(r[5]),
            "tip_knizi":    r[6] or "",
            "iznos":        float(r[7] or 0),
            "iznos_den":    float(r[8] or 0),
            "naplata":      float(r[9] or 0),
            "naplata_den":  float(r[10] or 0),
            "saldo":        float(r[11] or 0),
            "broker":       r[12] or "",
            "agent":        r[13] or "",
            "posrednik":    r[14] or "",
            "prodazen_kanal": r[15] or "",
        }
        rows.append(row)
        for k in tot:
            if k in row:
                tot[k] += row[k]
    return rows, tot


# ------------------------------------------------------------------
# Синтетичка картица — репликација на vesna.kartica_kl_sintetika
# (директно на основните табели, плус клиент со административна
# забрана: os_ponuda.banka_par_client)
# ------------------------------------------------------------------
def _build_sintetika_sql(f: dict):
    where, params = [], []

    def add(cond, val):
        where.append(cond)
        params.append(val)

    if _s(f.get("polisa_broj")):
        add("AND UPPER(x3.polisa_broj_cel) LIKE ?", "%" + _s(f["polisa_broj"]).upper() + "%")
    if _s(f.get("klient")):
        add("AND UPPER(pc.desc) LIKE ?", "%" + _s(f["klient"]).upper() + "%")
    if _s(f.get("admin_zabrana_klient")):
        add("AND UPPER(pcb.desc) LIKE ?", "%" + _s(f["admin_zabrana_klient"]).upper() + "%")

    klient_tip = _s(f.get("klient_tip"))
    if klient_tip == "Физичко":
        add("AND pcd.client_tip_pf = ?", "F")
    elif klient_tip == "Правно":
        add("AND pcd.client_tip_pf = ?", "P")

    if f.get("samo_admin_zabrana") or _s(f.get("admin_zabrana_klient")):
        where.append("AND x4.banka_par_client IS NOT NULL")

    w = " ".join(where)

    sql = f"""
        SELECT FIRST 20000
            x1.datum,
            x1.datum_knizi,
            x2.par_tip_dokument,
            vesna.vrati_client_id(x1.par_clientid)   AS client_id,
            vesna.vrati_client_name(x1.par_clientid) AS client_naziv,
            ((x5.sifra_polisa || '/' || x3.polisa_broj) || ' ' || x3.polisa_pod_broj) AS polisa,
            x3.polisa_broj_cel,
            SUM(x1.iznos_d)     AS iznos_d,
            SUM(x1.iznos_d_den) AS iznos_d_den,
            SUM(x1.iznos_p)     AS iznos_p,
            SUM(x1.iznos_p_den) AS iznos_p_den,
            vesna.vrati_faktura_broj(x1.os_aneks_fakturaid)    AS faktura,
            vesna.vrati_faktura_brojint(x1.os_aneks_fakturaid) AS fakturaint,
            pcb.desc AS admin_zabrana_naziv
        FROM viki.fin_stavka x1
        JOIN viki.par_tip_dokument x2  ON x2.par_tip_dokumentid = x1.par_tip_dokumentid
        JOIN viki.os_polisa x3         ON x1.os_polisaid = x3.os_polisaid
        JOIN viki.os_ponuda x4         ON x3.os_ponudaid = x4.os_ponudaid
        JOIN viki.os_produkt x5        ON x5.os_produktid = x4.os_produktid
        JOIN vesna.par_client pc       ON pc.par_clientid = x1.par_clientid
        LEFT JOIN vesna.par_client pcd ON pcd.par_clientid = x4.dogovoruvac_par_client
        LEFT JOIN vesna.par_client pcb ON pcb.par_clientid = x4.banka_par_client
        WHERE x1.datum <= TODAY
          AND NVL(x1.f_rs,'R') != 'N'
          AND x2.znak != 0
          AND x1.par_tip_dokumentid = 285
          {w}
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 12, 13, 14
        ORDER BY 4, 13, 1
    """
    return sql, params


def _to_groups_sintetika(raw):
    """
    Групира прво по клиент (прикажан еднаш), а внатре по фактура
    (секоја со своја подсума "Вкупно :").

    Групирањето е по клуч (dict), НЕ по соседност во листата — редовите
    на исти os_aneks/anex+година можат да припаѓаат на РАЗЛИЧНИ клиенти
    (пр. збиренаneks поврзувачки повеќе полиси/клиенти) и да се
    испреплетени во ORDER BY редоследот (сортиран по fakturaint), па
    истиот клиент/фактура може да се појави повеќе пати не-соседно.
    Групирање по соседност тогаш создава дупликат "Клиент:" блокови со
    нецелосни (погрешни) подсуми/салда.
    """
    clients_by_id = {}
    clients = []
    grand = {"iznos_d": 0, "iznos_d_den": 0, "iznos_p": 0, "iznos_p_den": 0}

    for r in raw:
        row = {
            "datum":       _fmt_date(r[0]),
            "_datum_raw":  r[0],
            "datum_knizi": _fmt_date(r[1]),
            "tip_dokument": r[2] or "",
            "client_id":    r[3] or "",
            "client_naziv": r[4] or "",
            "polisa":       r[5] or "",
            "polisa_broj_cel": r[6] or "",
            "iznos_d":     float(r[7] or 0),
            "iznos_d_den": float(r[8] or 0),
            "iznos_p":     float(r[9] or 0),
            "iznos_p_den": float(r[10] or 0),
            "faktura":     r[11] or "",
            "admin_zabrana_naziv": r[13] or "",
        }

        client = clients_by_id.get(row["client_id"])
        if client is None:
            client = {
                "client_id": row["client_id"],
                "client_naziv": row["client_naziv"],
                "admin_zabrana_naziv": row["admin_zabrana_naziv"],
                "faktura_groups": [],
                "_faktura_by_key": {},
                "subtotal": {"iznos_d": 0, "iznos_d_den": 0, "iznos_p": 0, "iznos_p_den": 0},
            }
            clients_by_id[row["client_id"]] = client
            clients.append(client)

        fg = client["_faktura_by_key"].get(row["faktura"])
        if fg is None:
            fg = {
                "polisa": row["polisa"],
                "faktura": row["faktura"],
                "rows": [],
                "subtotal": {"iznos_d": 0, "iznos_d_den": 0, "iznos_p": 0, "iznos_p_den": 0},
            }
            client["_faktura_by_key"][row["faktura"]] = fg
            client["faktura_groups"].append(fg)

        fg["rows"].append(row)
        for k in ("iznos_d", "iznos_d_den", "iznos_p", "iznos_p_den"):
            fg["subtotal"][k] += row[k]
            client["subtotal"][k] += row[k]
            grand[k] += row[k]

    for c in clients:
        del c["_faktura_by_key"]
        for fg in c["faktura_groups"]:
            fg["rows"].sort(key=lambda r: (r["_datum_raw"] is None, r["_datum_raw"]))
            for r in fg["rows"]:
                del r["_datum_raw"]
            fg["subtotal"]["saldo"] = fg["subtotal"]["iznos_d"] - fg["subtotal"]["iznos_p"]
        c["subtotal"]["saldo"] = c["subtotal"]["iznos_d"] - c["subtotal"]["iznos_p"]
    grand["saldo"] = grand["iznos_d"] - grand["iznos_p"]

    return clients, grand


class _NumberedCanvas(pdfcanvas.Canvas):
    """Canvas што овозможува 'Page X of Y' footer (двопроходно рендерирање)."""
    def __init__(self, *args, **kwargs):
        pdfcanvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(num_pages)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_footer(self, page_count):
        self.setFont("DejaVu", 8)
        self.setFillColor(colors.HexColor("#555555"))
        self.drawString(15 * mm, 10 * mm, "СИНТЕТИЧКА КАРТИЦА НА ФАКТУРИРАНА И НАПЛАТЕНА ПРЕМИЈА")
        self.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {self._pageNumber} of {page_count}")


def _fmt_amount(v, blank_if_zero=True):
    if v is None or (blank_if_zero and not v):
        return ""
    return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _pdf_sintetika(groups, grand, polisa_broj_label=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleMk", parent=styles["Title"], fontName="DejaVu-Bold", fontSize=13)
    normal_style = ParagraphStyle("NormalMk", parent=styles["Normal"], fontName="DejaVu", fontSize=9)
    warn_style = ParagraphStyle("WarnMk", parent=normal_style, fontName="DejaVu-Bold")
    hdr_style = ParagraphStyle("HdrMk", parent=styles["Normal"], fontName="DejaVu-Bold", fontSize=7.5,
                                textColor=colors.white, alignment=1, leading=9)
    cell_style = ParagraphStyle("CellMk", parent=styles["Normal"], fontName="DejaVu", fontSize=8, leading=10)
    num_style = ParagraphStyle("NumMk", parent=cell_style, alignment=2)
    label_style = ParagraphStyle("LabelMk", parent=cell_style, fontName="DejaVu-Bold", alignment=2)

    elements = [
        Paragraph(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), normal_style),
        Spacer(1, 4),
        Paragraph("СИНТЕТИЧКА КАРТИЦА НА ФАКТУРИРАНА И НАПЛАТЕНА ПРЕМИЈА", title_style),
    ]
    if polisa_broj_label:
        elements.append(Paragraph(f"<b>Полиса бр.:</b> {polisa_broj_label}", normal_style))

    admin_names = sorted({c["admin_zabrana_naziv"] for c in groups if c.get("admin_zabrana_naziv")})
    if admin_names:
        elements.append(Spacer(1, 3))
        elements.append(Paragraph(
            "⚠ Административна забрана: " + "; ".join(admin_names), warn_style
        ))
    elements.append(Spacer(1, 8))

    col_headers = [Paragraph(h, hdr_style) for h in
                   ["Полиса број", "Фактура", "Датум", "Датум книжи",
                    "Износ д.", "Износ п.", "Износ д.д.", "Износ п.д.", "Салдо"]]

    def num_cell(v):
        return Paragraph(_fmt_amount(v), num_style)

    def label_row(text, sub):
        return [
            "", "", "", Paragraph(text, label_style),
            Paragraph(_fmt_amount(sub["iznos_d"]), num_style),
            Paragraph(_fmt_amount(sub["iznos_p"]), num_style),
            Paragraph(_fmt_amount(sub["iznos_d_den"]), num_style),
            Paragraph(_fmt_amount(sub["iznos_p_den"]), num_style),
            Paragraph(_fmt_amount(sub["saldo"], blank_if_zero=False), num_style),
        ]

    data = [col_headers]
    row_styles = []
    row_idx = 1

    for c in groups:
        client_label = f"Клиент: {c['client_id']}  {c['client_naziv']}"
        data.append([Paragraph(client_label, label_style)] + [""] * 8)
        row_styles.append((row_idx, "client"))
        row_idx += 1

        for fg in c["faktura_groups"]:
            for r in fg["rows"]:
                data.append([
                    Paragraph(fg["polisa"], cell_style), Paragraph(fg["faktura"], cell_style),
                    Paragraph(r["datum"], cell_style), Paragraph(r["datum_knizi"], cell_style),
                    num_cell(r["iznos_d"]), num_cell(r["iznos_p"]),
                    num_cell(r["iznos_d_den"]), num_cell(r["iznos_p_den"]), "",
                ])
                row_idx += 1

            data.append(label_row("Вкупно :", fg["subtotal"]))
            row_styles.append((row_idx, "subtotal"))
            row_idx += 1

        data.append(label_row("Вкупно за клиент :", c["subtotal"]))
        row_styles.append((row_idx, "client_total"))
        row_idx += 1

    data.append(label_row("ВКУПНО :", grand))
    row_styles.append((row_idx, "grand"))

    table = Table(
        data,
        colWidths=[26 * mm, 24 * mm, 20 * mm, 20 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 15 * mm],
        repeatRows=1,
    )

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A3A5C")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfc")]),
    ]
    for idx, kind in row_styles:
        if kind == "client":
            style_cmds += [
                ("SPAN", (0, idx), (-1, idx)),
                ("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#eef4fb")),
                ("TOPPADDING", (0, idx), (-1, idx), 6),
            ]
        elif kind == "subtotal":
            style_cmds += [
                ("SPAN", (0, idx), (3, idx)),
                ("LINEABOVE", (0, idx), (-1, idx), 0.6, colors.black),
            ]
        elif kind == "client_total":
            style_cmds += [
                ("SPAN", (0, idx), (3, idx)),
                ("LINEABOVE", (0, idx), (-1, idx), 0.8, colors.HexColor("#1A3A5C")),
                ("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#dfeaf5")),
            ]
        elif kind == "grand":
            style_cmds += [
                ("SPAN", (0, idx), (3, idx)),
                ("LINEABOVE", (0, idx), (-1, idx), 1, colors.black),
                ("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#eef4fb")),
            ]

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    doc.build(elements, canvasmaker=_NumberedCanvas)
    buf.seek(0)
    return buf


def _render(request, user, filters, nivo, rows, totals, error, sintetika_groups=None, sintetika_grand=None):
    return templates.TemplateResponse("report_fakturi.html", {
        "request":          request,
        "user":             user,
        "active":           "report_fakturi",
        "f":                filters,
        "nivo":             nivo,
        "rows":             rows,
        "totals":           totals,
        "error":            error,
        "searched":         rows is not None or sintetika_groups is not None,
        "prodazni_kanali":  PRODAZNI_KANALI,
        "sintetika_groups": sintetika_groups,
        "sintetika_grand":  sintetika_grand,
    })


# ------------------------------------------------------------------
# GET  — empty filter form
# ------------------------------------------------------------------
@router.get("/report-fakturi")
def report_fakturi_get(request: Request):
    user, redirect = _require_role(request)
    if redirect:
        return redirect
    return _render(request, user, {}, "polisa", None, None, None)


# ------------------------------------------------------------------
# POST — execute search
# ------------------------------------------------------------------
@router.post("/report-fakturi")
def report_fakturi_post(
    request:             Request,
    nivo:                str = Form("polisa"),
    klient:              str = Form(""),
    faktura:             str = Form(""),
    tip_knizi:           str = Form(""),
    polisa_broj:         str = Form(""),
    iznos_od:            str = Form(""),
    iznos_do:       str = Form(""),
    iznos_den_od:   str = Form(""),
    iznos_den_do:   str = Form(""),
    naplata_od:     str = Form(""),
    naplata_do:     str = Form(""),
    naplata_den_od: str = Form(""),
    naplata_den_do: str = Form(""),
    datum_aneks_od:   str = Form(""),
    datum_aneks_do:   str = Form(""),
    datum_valuta_od:  str = Form(""),
    datum_valuta_do:  str = Form(""),
    datum_faktura_od: str = Form(""),
    datum_faktura_do: str = Form(""),
    datum_knizi_od:   str = Form(""),
    datum_knizi_do:   str = Form(""),
    broker:         str = Form(""),
    agent:          str = Form(""),
    posrednik:      str = Form(""),
    promotor:       str = Form(""),
    dospeana:       Optional[str] = Form(None),
    klient_tip:     str = Form("site"),
    kanali:         List[str] = Form(default=[]),
    samo_admin_zabrana:   Optional[str] = Form(None),
    admin_zabrana_klient: str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    filters = {
        "nivo": nivo, "klient": klient, "faktura": faktura, "tip_knizi": tip_knizi,
        "polisa_broj": polisa_broj,
        "iznos_od": iznos_od, "iznos_do": iznos_do,
        "iznos_den_od": iznos_den_od, "iznos_den_do": iznos_den_do,
        "naplata_od": naplata_od, "naplata_do": naplata_do,
        "naplata_den_od": naplata_den_od, "naplata_den_do": naplata_den_do,
        "datum_aneks_od": datum_aneks_od, "datum_aneks_do": datum_aneks_do,
        "datum_valuta_od": datum_valuta_od, "datum_valuta_do": datum_valuta_do,
        "datum_faktura_od": datum_faktura_od, "datum_faktura_do": datum_faktura_do,
        "datum_knizi_od": datum_knizi_od, "datum_knizi_do": datum_knizi_do,
        "broker": broker, "agent": agent, "posrednik": posrednik, "promotor": promotor,
        "dospeana": bool(dospeana), "klient_tip": klient_tip, "kanali": kanali,
        "samo_admin_zabrana": bool(samo_admin_zabrana),
        "admin_zabrana_klient": admin_zabrana_klient,
    }

    _auto_expand_polisa(filters)

    if nivo == "sintetika":
        sintetika_groups, sintetika_grand, error = None, None, None
        try:
            sql, params = _build_sintetika_sql(filters)
            raw = _run_query(sql, params)
            sintetika_groups, sintetika_grand = _to_groups_sintetika(raw)
        except Exception as e:
            error = str(e)
        return _render(request, user, filters, nivo, None, None, error,
                        sintetika_groups=sintetika_groups, sintetika_grand=sintetika_grand)

    rows, totals, error = None, None, None
    try:
        sql, params = _build_sql(filters, nivo)
        raw = _run_query(sql, params)
        if nivo == "polisa":
            rows, totals = _to_rows_polisa(raw)
        elif nivo == "faktura":
            rows, totals = _to_rows_faktura(raw)
        else:
            rows, totals = _to_rows_red(raw)
    except Exception as e:
        error = str(e)

    return _render(request, user, filters, nivo, rows, totals, error)


# ------------------------------------------------------------------
# POST — Синтетичка картица PDF (печатење идентично со примерот)
# ------------------------------------------------------------------
@router.post("/report-fakturi/sintetika-pdf")
def report_fakturi_sintetika_pdf(
    request:              Request,
    polisa_broj:          str = Form(""),
    klient:               str = Form(""),
    klient_tip:           str = Form("site"),
    samo_admin_zabrana:   Optional[str] = Form(None),
    admin_zabrana_klient: str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    filters = {
        "polisa_broj": polisa_broj, "klient": klient, "klient_tip": klient_tip,
        "samo_admin_zabrana": bool(samo_admin_zabrana),
        "admin_zabrana_klient": admin_zabrana_klient,
    }

    try:
        sql, params = _build_sintetika_sql(filters)
        raw = _run_query(sql, params)
        groups, grand = _to_groups_sintetika(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not groups:
        raise HTTPException(status_code=404, detail="Нема резултати за зададените филтри.")

    buf = _pdf_sintetika(groups, grand, polisa_broj_label=_s(polisa_broj) or None)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="SintetickaKarticaKlient.pdf"'},
    )


# ------------------------------------------------------------------
# POST — Синтетичка картица Excel (исти групи/подсуми како PDF)
# ------------------------------------------------------------------
@router.post("/report-fakturi/sintetika-excel")
def report_fakturi_sintetika_excel(
    request:              Request,
    polisa_broj:          str = Form(""),
    klient:               str = Form(""),
    klient_tip:           str = Form("site"),
    samo_admin_zabrana:   Optional[str] = Form(None),
    admin_zabrana_klient: str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    filters = {
        "polisa_broj": polisa_broj, "klient": klient, "klient_tip": klient_tip,
        "samo_admin_zabrana": bool(samo_admin_zabrana),
        "admin_zabrana_klient": admin_zabrana_klient,
    }

    try:
        sql, params = _build_sintetika_sql(filters)
        raw = _run_query(sql, params)
        groups, grand = _to_groups_sintetika(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not groups:
        raise HTTPException(status_code=404, detail="Нема резултати за зададените филтри.")

    buf = _excel_sintetika(groups, grand)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="SintetickaKarticaKlient.xlsx"'},
    )


# ------------------------------------------------------------------
# POST — Excel export (same filters, always "red" level)
# ------------------------------------------------------------------
@router.post("/report-fakturi/excel")
def report_fakturi_excel(
    request:             Request,
    nivo:                str = Form("polisa"),
    klient:              str = Form(""),
    faktura:             str = Form(""),
    tip_knizi:           str = Form(""),
    polisa_broj:         str = Form(""),
    iznos_od:            str = Form(""),
    iznos_do:       str = Form(""),
    iznos_den_od:   str = Form(""),
    iznos_den_do:   str = Form(""),
    naplata_od:     str = Form(""),
    naplata_do:     str = Form(""),
    naplata_den_od: str = Form(""),
    naplata_den_do: str = Form(""),
    datum_aneks_od:   str = Form(""),
    datum_aneks_do:   str = Form(""),
    datum_valuta_od:  str = Form(""),
    datum_valuta_do:  str = Form(""),
    datum_faktura_od: str = Form(""),
    datum_faktura_do: str = Form(""),
    datum_knizi_od:   str = Form(""),
    datum_knizi_do:   str = Form(""),
    broker:         str = Form(""),
    agent:          str = Form(""),
    posrednik:      str = Form(""),
    promotor:       str = Form(""),
    dospeana:       Optional[str] = Form(None),
    klient_tip:     str = Form("site"),
    kanali:         List[str] = Form(default=[]),
    samo_admin_zabrana:   Optional[str] = Form(None),
    admin_zabrana_klient: str = Form(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    filters = {
        "nivo": nivo, "klient": klient, "faktura": faktura, "tip_knizi": tip_knizi,
        "polisa_broj": polisa_broj,
        "iznos_od": iznos_od, "iznos_do": iznos_do,
        "iznos_den_od": iznos_den_od, "iznos_den_do": iznos_den_do,
        "naplata_od": naplata_od, "naplata_do": naplata_do,
        "naplata_den_od": naplata_den_od, "naplata_den_do": naplata_den_do,
        "datum_aneks_od": datum_aneks_od, "datum_aneks_do": datum_aneks_do,
        "datum_valuta_od": datum_valuta_od, "datum_valuta_do": datum_valuta_do,
        "datum_faktura_od": datum_faktura_od, "datum_faktura_do": datum_faktura_do,
        "datum_knizi_od": datum_knizi_od, "datum_knizi_do": datum_knizi_do,
        "broker": broker, "agent": agent, "posrednik": posrednik, "promotor": promotor,
        "dospeana": bool(dospeana), "klient_tip": klient_tip, "kanali": kanali,
        "samo_admin_zabrana": bool(samo_admin_zabrana),
        "admin_zabrana_klient": admin_zabrana_klient,
    }

    _auto_expand_polisa(filters)

    try:
        sql, params = _build_sql(filters, nivo)
        raw = _run_query(sql, params)
        if nivo == "polisa":
            rows, totals = _to_rows_polisa(raw)
            buf = _excel_polisa(rows, totals)
        elif nivo == "faktura":
            rows, totals = _to_rows_faktura(raw)
            buf = _excel_faktura(rows, totals)
        else:
            rows, totals = _to_rows_red(raw)
            buf = _excel_red(rows, totals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    nivo_label = {"polisa": "Polisa", "faktura": "Faktura", "red": "Red"}.get(nivo, nivo)
    filename = f"ReportFakturi_{nivo_label}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ------------------------------------------------------------------
# POST — Excel for selected invoices (zatvaranje)
# ------------------------------------------------------------------
@router.post("/report-fakturi/excel-zatvaranje")
def report_fakturi_excel_zatvaranje(
    request:             Request,
    nivo:                str = Form("faktura"),
    klient:              str = Form(""),
    faktura:             str = Form(""),
    tip_knizi:           str = Form(""),
    polisa_broj:         str = Form(""),
    iznos_od:            str = Form(""),
    iznos_do:       str = Form(""),
    iznos_den_od:   str = Form(""),
    iznos_den_do:   str = Form(""),
    naplata_od:     str = Form(""),
    naplata_do:     str = Form(""),
    naplata_den_od: str = Form(""),
    naplata_den_do: str = Form(""),
    datum_aneks_od:   str = Form(""),
    datum_aneks_do:   str = Form(""),
    datum_valuta_od:  str = Form(""),
    datum_valuta_do:  str = Form(""),
    datum_faktura_od: str = Form(""),
    datum_faktura_do: str = Form(""),
    datum_knizi_od:   str = Form(""),
    datum_knizi_do:   str = Form(""),
    broker:         str = Form(""),
    agent:          str = Form(""),
    posrednik:      str = Form(""),
    promotor:       str = Form(""),
    dospeana:       Optional[str] = Form(None),
    klient_tip:     str = Form("site"),
    kanali:         List[str] = Form(default=[]),
    sel_faktura:    List[str] = Form(default=[]),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    if not sel_faktura:
        raise HTTPException(status_code=400, detail="Не е избрана ниедна фактура.")

    filters = {
        "nivo": "faktura", "klient": klient, "faktura": faktura, "tip_knizi": tip_knizi,
        "polisa_broj": polisa_broj,
        "iznos_od": iznos_od, "iznos_do": iznos_do,
        "iznos_den_od": iznos_den_od, "iznos_den_do": iznos_den_do,
        "naplata_od": naplata_od, "naplata_do": naplata_do,
        "naplata_den_od": naplata_den_od, "naplata_den_do": naplata_den_do,
        "datum_aneks_od": datum_aneks_od, "datum_aneks_do": datum_aneks_do,
        "datum_valuta_od": datum_valuta_od, "datum_valuta_do": datum_valuta_do,
        "datum_faktura_od": datum_faktura_od, "datum_faktura_do": datum_faktura_do,
        "datum_knizi_od": datum_knizi_od, "datum_knizi_do": datum_knizi_do,
        "broker": broker, "agent": agent, "posrednik": posrednik, "promotor": promotor,
        "dospeana": bool(dospeana), "klient_tip": klient_tip, "kanali": kanali,
    }

    _auto_expand_polisa(filters)

    try:
        sql, params = _build_sql(filters, "faktura")
        raw = _run_query(sql, params)
        all_rows, _ = _to_rows_faktura(raw)
        # sel_faktura values are "faktura|polisa_broj"
        sel_set = set(sel_faktura)
        selected = [r for r in all_rows if f"{r['faktura']}|{r['polisa_broj']}" in sel_set]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    buf = _excel_zatvaranje(selected)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Zatvaranje_Fakturi.xlsx"'},
    )


# ------------------------------------------------------------------
# GET — expand polisa → faktura rows (AJAX/JSON)
# ------------------------------------------------------------------
@router.get("/report-fakturi/expand-polisa")
def expand_polisa(request: Request, polisa_broj: str = Query(...)):
    user, redirect = _require_role(request)
    if redirect:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    sql = f"""
SELECT
    x2.polisa_broj_cel AS polisa_broj,
    MAX(pc.desc) AS client_naziv,
    {_FAKTURA_EXPR} AS faktura,
    x0.data_faktura,
    MAX({_TIP_KNIZI_EXPR}) AS tip_knizi,
    SUM(NVL(x0.iznos,0))         AS vk_iznos,
    SUM(NVL(x0.iznos_denari,0))  AS vk_iznos_den,
    SUM(NVL({_NAPLATA_EXPR},0))  AS vk_naplata,
    SUM(NVL({_NAPLATA_DEN_EXPR},0)) AS vk_naplata_den,
    SUM(NVL(x0.iznos,0) - NVL({_NAPLATA_EXPR},0)) AS saldo
{_BASE_FROM}
WHERE NVL(x3.f_rs,'R') <> 'N' AND x2.polisa_broj_cel = ?
GROUP BY 1, x2.os_polisaid, 3, 4
ORDER BY x0.data_faktura, faktura
"""
    try:
        raw = _run_query(sql, [polisa_broj])
        rows, _ = _to_rows_faktura(raw)
        for r in rows:
            r["data_faktura"] = str(r["data_faktura"])
        return JSONResponse({"rows": rows})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# GET — expand faktura → red rows (AJAX/JSON)
# ------------------------------------------------------------------
@router.get("/report-fakturi/expand-faktura")
def expand_faktura(request: Request,
                         polisa_broj: str = Query(...),
                         faktura: str = Query(...)):
    user, redirect = _require_role(request)
    if redirect:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    sql = f"""
SELECT
    x2.polisa_broj_cel AS polisa_broj,
    pc.desc AS client_naziv,
    {_FAKTURA_EXPR} AS faktura,
    x0.rata,
    x0.data_faktura, x0.data_valuta,
    {_TIP_KNIZI_EXPR} AS tip_knizi,
    NVL(x0.iznos,0)         AS iznos,
    NVL(x0.iznos_denari,0)  AS iznos_den,
    NVL({_NAPLATA_EXPR},0)      AS naplata,
    NVL({_NAPLATA_DEN_EXPR},0)  AS naplata_den,
    NVL(x0.iznos,0) - NVL({_NAPLATA_EXPR},0) AS saldo,
    brk.desc AS broker_name, agt.desc AS par_agent_name, psr.desc AS posrednik_name, pk.desc_mk AS prodazen_kanal
{_BASE_FROM}
WHERE NVL(x3.f_rs,'R') <> 'N' AND x2.polisa_broj_cel = ? AND {_FAKTURA_EXPR} = ?
ORDER BY x0.rata
"""
    try:
        raw = _run_query(sql, [polisa_broj, faktura])
        rows, _ = _to_rows_red(raw)
        for r in rows:
            r["data_faktura"] = str(r["data_faktura"])
            r["data_valuta"]  = str(r["data_valuta"])
        return JSONResponse({"rows": rows})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# GET — popup за пребарување клиент (ЕДБ/ЕМБГ, Опис, Клиент ID)
# ------------------------------------------------------------------
@router.get("/report-fakturi/search-client")
def search_client(
    request: Request,
    edb: str = Query(""),
    opis: str = Query(""),
    client_id: str = Query(""),
):
    user, redirect = _require_role(request)
    if redirect:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    where, params = [], []
    if _s(edb):
        where.append("AND UPPER(edb) LIKE ?")
        params.append("%" + _s(edb).upper() + "%")
    if _s(opis):
        where.append("AND UPPER(desc) LIKE ?")
        params.append("%" + _s(opis).upper() + "%")
    if _s(client_id):
        where.append("AND (vesna.vrati_client_id(par_clientid) LIKE ? OR par_clientid::VARCHAR(20) LIKE ?)")
        params.append("%" + _s(client_id) + "%")
        params.append("%" + _s(client_id) + "%")

    sql = f"""
        SELECT FIRST 100
            par_clientid,
            vesna.vrati_client_id(par_clientid) AS client_id,
            TRIM(desc)   AS opis,
            NVL(edb, '') AS edb
        FROM vesna.par_client
        WHERE 1 = 1 {' '.join(where)}
        ORDER BY desc
    """
    try:
        raw = _run_query(sql, params)
        rows = [
            {"par_clientid": r[0], "client_id": r[1] or "", "opis": r[2] or "", "edb": r[3] or ""}
            for r in raw
        ]
        return JSONResponse({"rows": rows})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Excel builders ────────────────────────────────────────────────

def _new_wb(title: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title
    return wb, ws


_HDR_FILL = PatternFill("solid", fgColor="1A3A5C")
_HDR_FONT = Font(color="FFFFFF", bold=True, name="Calibri", size=10)
_TOT_FILL = PatternFill("solid", fgColor="D5E8D4")
_BOLD     = Font(bold=True, name="Calibri", size=10)
_NORM     = Font(name="Calibri", size=10)
_CTR      = Alignment(horizontal="center", vertical="center")
_RGT      = Alignment(horizontal="right",  vertical="center")
_LFT      = Alignment(horizontal="left",   vertical="center")
_THIN     = Side(border_style="thin", color="CCCCCC")
_BRD      = Border(top=_THIN, bottom=_THIN, left=_THIN, right=_THIN)
_NUM      = '#,##0.00'


def _hdr_row(ws, headers):
    ws.append(headers)
    r = ws.max_row
    for ci in range(1, len(headers) + 1):
        c = ws.cell(r, ci)
        c.fill = _HDR_FILL; c.font = _HDR_FONT
        c.alignment = _CTR; c.border = _BRD


def _data_cell(ws, row_idx, col_idx, value, is_num=False):
    c = ws.cell(row_idx, col_idx, value)
    c.font = _NORM; c.border = _BRD
    if is_num:
        c.alignment = _RGT
        c.number_format = _NUM
        if isinstance(value, (int, float)) and value < 0:
            c.font = Font(name="Calibri", size=10, color="C0392B")
    else:
        c.alignment = _LFT


def _tot_row(ws, n_cols, label_col, nums: dict):
    ws.append([])
    r = ws.max_row
    for ci in range(1, n_cols + 1):
        c = ws.cell(r, ci)
        c.fill = _TOT_FILL; c.font = _BOLD; c.border = _BRD
    ws.cell(r, label_col, "ВКУПНО").alignment = _LFT
    for ci, val in nums.items():
        c = ws.cell(r, ci, val)
        c.alignment = _RGT; c.number_format = _NUM


def _save(wb):
    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    return buf


def _excel_polisa(rows, tot):
    wb, ws = _new_wb("По полиса")
    _hdr_row(ws, ["Полиса", "Клиент", "Вк. Износ", "Вк. Износ (ден.)",
                  "Вк. Наплата", "Вк. Наплата (ден.)", "Салдо", "Клиент Административна забрана"])
    for r in rows:
        ws.append([r["polisa_broj"], r["client_naziv"], r["vk_iznos"], r["vk_iznos_den"],
                   r["vk_naplata"], r["vk_naplata_den"], r["saldo"], r.get("admin_zabrana_naziv", "")])
        dr = ws.max_row
        _data_cell(ws, dr, 1, r["polisa_broj"])
        _data_cell(ws, dr, 2, r["client_naziv"])
        for ci, k in [(3,"vk_iznos"),(4,"vk_iznos_den"),(5,"vk_naplata"),(6,"vk_naplata_den"),(7,"saldo")]:
            _data_cell(ws, dr, ci, r[k], is_num=True)
        _data_cell(ws, dr, 8, r.get("admin_zabrana_naziv", ""))
    _tot_row(ws, 8, 1, {3: tot["vk_iznos"], 4: tot["vk_iznos_den"],
                        5: tot["vk_naplata"], 6: tot["vk_naplata_den"], 7: tot["saldo"]})
    for ci, w in [(1,22),(2,35),(3,15),(4,17),(5,15),(6,17),(7,15),(8,30)]:
        ws.column_dimensions[get_column_letter(ci)].width = w
    return _save(wb)


def _excel_faktura(rows, tot):
    wb, ws = _new_wb("По фактури")
    _hdr_row(ws, ["Полиса", "Клиент", "Фактура", "Дат. Фактура", "Тип",
                  "Износ", "Износ (ден.)", "Наплата", "Наплата (ден.)", "Салдо"])
    for r in rows:
        dr_vals = [r["polisa_broj"], r["client_naziv"], r["faktura"], r["data_faktura"],
                   r["tip_knizi"], r["vk_iznos"], r["vk_iznos_den"],
                   r["vk_naplata"], r["vk_naplata_den"], r["saldo"]]
        ws.append(dr_vals)
        dr = ws.max_row
        for ci, is_n in [(1,False),(2,False),(3,False),(4,False),(5,False),
                         (6,True),(7,True),(8,True),(9,True),(10,True)]:
            _data_cell(ws, dr, ci, dr_vals[ci-1], is_num=is_n)
    _tot_row(ws, 10, 1, {6: tot["vk_iznos"], 7: tot["vk_iznos_den"],
                         8: tot["vk_naplata"], 9: tot["vk_naplata_den"], 10: tot["saldo"]})
    for ci, w in [(1,20),(2,32),(3,18),(4,14),(5,12),(6,14),(7,16),(8,14),(9,16),(10,14)]:
        ws.column_dimensions[get_column_letter(ci)].width = w
    return _save(wb)


def _excel_zatvaranje(rows_selected: list):
    """Excel for selected invoices marked for closing (no payment)."""
    wb, ws = _new_wb("За затварање")
    _hdr_row(ws, ["Полиса", "Клиент", "Фактура", "Дат. Фактура", "Тип",
                  "Износ", "Износ (ден.)", "Наплата", "Наплата (ден.)", "Салдо"])
    tot = {"vk_iznos": 0, "vk_iznos_den": 0, "vk_naplata": 0, "vk_naplata_den": 0, "saldo": 0}
    for r in rows_selected:
        vals = [r["polisa_broj"], r["client_naziv"], r["faktura"], r["data_faktura"],
                r["tip_knizi"], r["vk_iznos"], r["vk_iznos_den"],
                r["vk_naplata"], r["vk_naplata_den"], r["saldo"]]
        ws.append(vals)
        dr = ws.max_row
        for ci, is_n in [(1,False),(2,False),(3,False),(4,False),(5,False),
                         (6,True),(7,True),(8,True),(9,True),(10,True)]:
            _data_cell(ws, dr, ci, vals[ci-1], is_num=is_n)
        for k in tot:
            if k in r:
                tot[k] += r[k]
    _tot_row(ws, 10, 1, {6: tot["vk_iznos"], 7: tot["vk_iznos_den"],
                         8: tot["vk_naplata"], 9: tot["vk_naplata_den"], 10: tot["saldo"]})
    for ci, w in [(1,20),(2,32),(3,18),(4,14),(5,12),(6,14),(7,16),(8,14),(9,16),(10,14)]:
        ws.column_dimensions[get_column_letter(ci)].width = w
    return _save(wb)


def _excel_sintetika(groups, grand):
    wb, ws = _new_wb("Синтетичка картица")
    _hdr_row(ws, ["Полиса број", "Фактура", "Датум", "Датум книжи",
                  "Износ д.", "Износ п.", "Износ д.д.", "Износ п.д.", "Салдо"])

    client_fill = PatternFill("solid", fgColor="EEF4FB")
    total_fill  = PatternFill("solid", fgColor="DFEAF5")

    def sub_row(label, sub, fill=None):
        ws.append(["", "", "", label, sub["iznos_d"], sub["iznos_p"],
                   sub["iznos_d_den"], sub["iznos_p_den"], sub["saldo"]])
        r = ws.max_row
        for ci in range(1, 10):
            c = ws.cell(r, ci)
            c.font = _BOLD; c.border = _BRD
            if fill:
                c.fill = fill
            if ci >= 5:
                c.alignment = _RGT; c.number_format = _NUM

    for c in groups:
        ws.append([f"Клиент: {c['client_id']}  {c['client_naziv']}"] + [""] * 8)
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
        cell = ws.cell(r, 1)
        cell.font = _BOLD; cell.fill = client_fill; cell.alignment = _LFT; cell.border = _BRD

        for fg in c["faktura_groups"]:
            for row in fg["rows"]:
                vals = [fg["polisa"], fg["faktura"], row["datum"], row["datum_knizi"],
                        row["iznos_d"], row["iznos_p"], row["iznos_d_den"], row["iznos_p_den"], ""]
                ws.append(vals)
                dr = ws.max_row
                for ci, is_n in [(1,False),(2,False),(3,False),(4,False),
                                 (5,True),(6,True),(7,True),(8,True),(9,True)]:
                    _data_cell(ws, dr, ci, vals[ci-1], is_num=is_n)

            sub_row("Вкупно :", fg["subtotal"])

        sub_row("Вкупно за клиент :", c["subtotal"], fill=total_fill)

    sub_row("ВКУПНО :", grand, fill=total_fill)

    for ci, w in [(1,26),(2,20),(3,13),(4,13),(5,14),(6,14),(7,14),(8,14),(9,14)]:
        ws.column_dimensions[get_column_letter(ci)].width = w
    return _save(wb)


def _excel_red(rows, tot):
    wb, ws = _new_wb("По ред")
    _hdr_row(ws, ["Полиса", "Клиент", "Фактура", "Рат.", "Дат. Фактура", "Дат. Валута",
                  "Тип", "Износ", "Износ (ден.)", "Наплата", "Наплата (ден.)",
                  "Салдо", "Брокер", "Агент", "Посредник", "Прод. Канал"])
    for r in rows:
        vals = [r["polisa_broj"], r["client_naziv"], r["faktura"], r["rata"],
                r["data_faktura"], r["data_valuta"], r["tip_knizi"],
                r["iznos"], r["iznos_den"], r["naplata"], r["naplata_den"], r["saldo"],
                r["broker"], r["agent"], r["posrednik"], r["prodazen_kanal"]]
        ws.append(vals)
        dr = ws.max_row
        num_cols = {8,9,10,11,12}
        for ci in range(1, 17):
            _data_cell(ws, dr, ci, vals[ci-1], is_num=(ci in num_cols))
    _tot_row(ws, 16, 1, {8: tot["iznos"], 9: tot["iznos_den"],
                         10: tot["naplata"], 11: tot["naplata_den"], 12: tot["saldo"]})
    for ci, w in [(1,18),(2,30),(3,16),(4,6),(5,13),(6,13),(7,10),
                  (8,13),(9,15),(10,13),(11,15),(12,13),(13,20),(14,20),(15,20),(16,22)]:
        ws.column_dimensions[get_column_letter(ci)].width = w
    return _save(wb)

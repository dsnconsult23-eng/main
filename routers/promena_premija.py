from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from auth.role_utils import has_any_role
from routers import Connection
from typing import List
import os, datetime
import jpype

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)

_ALLOWED_ROLES = ["admin", "promena_premija"]

TIPOVI_PROMENA = [
    ("premija_kolektivno", "Промена на премија на Фактура Колективно"),
    ("dopolnitelno_osiguruvanje", "Додавање на дополнително осигурување"),
    ("promena_datum_faktura", "Промена на датум на фактура и датум на валута"),
    ("promena_godina_aneks", "Промена на година на анекс"),
]

TIP_KNIZI_DOPOLNITELNO = [
    ("DPREM", "Осигурување за незгода"),
    ("ZPREM", "Здравствена премија"),
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
                NVL(vesna.vrati_naplata(x0.os_aneks_fakturaid),0) AS naplata,
                (SELECT COUNT(*) FROM viki.fin_stavka fs
                  WHERE fs.os_aneks_fakturaid = x0.os_aneks_fakturaid
                    AND fs.nal_vid IS NOT NULL) AS br_knizeni,
                NVL(pv.valuta, 'EUR') AS valuta_kod,
                pc.desc AS client_naziv
            FROM viki.os_aneks_faktura x0
            JOIN viki.os_aneks x1  ON x0.os_aneksid = x1.os_aneksid
            JOIN viki.os_polisa x2 ON x2.os_polisaid = x1.os_polisaid
            LEFT JOIN par_valuta pv ON pv.par_valutaid = x1.par_valutaid
            LEFT JOIN par_client pc ON pc.par_clientid = x1.par_clientid
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
        iznos = float(r[5] or 0)
        naplata = float(r[7] or 0)
        rows.append({
            "os_aneks_fakturaid": int(r[0]),
            "faktura":            r[1] or "",
            "data_faktura":       _fmt_date(r[2]),
            "data_valuta":        _fmt_date(r[3]),
            "tip_knizi":          r[4] or "",
            "iznos":              iznos,
            "iznos_denari":       float(r[6] or 0),
            "naplata":            naplata,
            "saldo":              iznos - naplata,
            "e_proknizena":       bool(r[8] or 0),
            "valuta_kod":         r[9] or "EUR",
            "client_naziv":       r[10] or "",
        })
    return rows


def _fetch_aneksi(polisa_broj: str):
    cursor, ok = Connection.OSISinit()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        sql = """
            SELECT a.os_aneksid, a.os_aneks, py.par_year, a.datum_aneks,
                   (SELECT COUNT(*) FROM viki.os_aneks_faktura f WHERE f.os_aneksid = a.os_aneksid) AS br_fakturi
            FROM viki.os_aneks a
            JOIN viki.par_year py ON py.par_yearid = a.par_yearid
            JOIN viki.os_polisa p ON p.os_polisaid = a.os_polisaid
            WHERE UPPER(p.polisa_broj_cel) = ?
            ORDER BY a.os_aneks, py.par_year
        """
        cursor.execute(sql, [polisa_broj.strip().upper()])
        raw = cursor.fetchall()
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    aneksi = []
    for r in raw:
        aneksi.append({
            "os_aneksid":   int(r[0]),
            "os_aneks":     r[1] or "",
            "godina":       int(r[2]) if r[2] is not None else None,
            "datum_aneks":  _fmt_date(r[3]),
            "br_fakturi":   int(r[4] or 0),
        })
    return aneksi


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
            "SELECT COUNT(*) FROM viki.fin_stavka WHERE os_aneks_fakturaid = ? AND nal_vid IS NOT NULL",
            [os_aneks_fakturaid]
        )
        knizeno = cursor.fetchone()
        if knizeno and knizeno[0]:
            raise RuntimeError(
                "Фактурата е веќе прокнижена во финансии — директна промена на износ не е дозволена. "
                "Користете ја опцијата 'Додади ставка'."
            )

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


def _izbrisi_stavka(os_aneks_fakturaid: int, user_name: str):
    """Бришење на непрокнижена фактура (пр. погрешно додадена корективна
    ставка). Не ги менува data_faktura/data_valuta на ништо друго — само ја
    отстранува ставката (и празниот анекс, ако нема повеќе фактури под него)."""
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        cursor.execute(
            "SELECT os_aneksid, iznos, iznos_denari FROM viki.os_aneks_faktura WHERE os_aneks_fakturaid = ?",
            [os_aneks_fakturaid]
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Фактурата не е пронајдена.")
        os_aneksid, iznos, iznos_denari = row

        cursor.execute(
            "SELECT COUNT(*) FROM viki.fin_stavka WHERE os_aneks_fakturaid = ? AND nal_vid IS NOT NULL",
            [os_aneks_fakturaid]
        )
        knizeno = cursor.fetchone()
        if knizeno and knizeno[0]:
            raise RuntimeError(
                "Фактурата е веќе прокнижена во финансии — не може да се избрише."
            )

        cursor.execute(
            "DELETE FROM viki.fin_stavka WHERE os_aneks_fakturaid = ?",
            [os_aneks_fakturaid]
        )
        cursor.execute(
            "DELETE FROM viki.os_aneks_faktura WHERE os_aneks_fakturaid = ?",
            [os_aneks_fakturaid]
        )

        os_aneks_izbrisan = False
        cursor.execute(
            "SELECT COUNT(*) FROM viki.os_aneks_faktura WHERE os_aneksid = ?",
            [os_aneksid]
        )
        preostanati = cursor.fetchone()
        if preostanati and preostanati[0] == 0:
            cursor.execute("DELETE FROM viki.os_aneks WHERE os_aneksid = ?", [os_aneksid])
            os_aneks_izbrisan = True

        try:
            conn.commit()
        except Exception:
            pass

        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().isoformat(timespec='seconds')}] user={user_name} "
                f"IZBRISANA_STAVKA os_aneks_fakturaid={os_aneks_fakturaid} os_aneksid={os_aneksid} "
                f"iznos={iznos} iznos_denari={iznos_denari} os_aneks_izbrisan={os_aneks_izbrisan}\n"
            )

        return os_aneks_izbrisan
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


def _to_py_date(v):
    # Драјверот некогаш враќа датуми како datetime.date, а некогаш како ISO
    # string ("2026-04-01"), па нормализираме до вистински date.
    if v is None or v == "":
        return None
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _to_db_date(v):
    # jaydebeapi не bind-ира Python datetime.date/string автоматски за Informix DATE
    # колони ("Input value is not valid"); java.sql.Date.valueOf() секогаш очекува
    # "yyyy-mm-dd", независно од Informix DBDATE=MDY локалот.
    d = _to_py_date(v)
    if d is None:
        return None
    JavaDate = jpype.JClass("java.sql.Date")
    return JavaDate.valueOf(d.strftime("%Y-%m-%d"))


def _exec_logged(cursor, sql: str, params=None):
    print(f"[promena_premija SQL] {sql.strip()} | params={params}")
    if params is None:
        cursor.execute(sql)
    else:
        cursor.execute(sql, params)


def _konverzija_eur_mkd(cursor, na_datum, iznos_eur: float) -> float:
    d = _to_py_date(na_datum)
    if d is None:
        raise RuntimeError(f"Неважечки датум за конверзија: {na_datum!r}")
    datum_str = d.strftime("%d/%m/%Y")
    _exec_logged(
        cursor,
        "SELECT konverzija(?, ?, 'EUR', 'MKD') FROM systables WHERE tabid = 1",
        [datum_str, iznos_eur]
    )
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _vrati_valuta_kod(cursor, par_valutaid) -> str:
    if par_valutaid is None:
        return "MKD"
    _exec_logged(
        cursor,
        "SELECT valuta FROM par_valuta WHERE par_valutaid = ?",
        [par_valutaid]
    )
    row = cursor.fetchone()
    return (row[0] if row and row[0] else "MKD").strip()


def _konverzija_na_mkd(cursor, na_datum, iznos: float, valuta_kod: str) -> float:
    if valuta_kod.upper() == "MKD":
        return iznos
    d = _to_py_date(na_datum)
    if d is None:
        raise RuntimeError(f"Неважечки датум за конверзија: {na_datum!r}")
    datum_str = d.strftime("%d/%m/%Y")
    _exec_logged(
        cursor,
        "SELECT konverzija(?, ?, ?, 'MKD') FROM systables WHERE tabid = 1",
        [datum_str, iznos, valuta_kod]
    )
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _create_dopolnitelno_faktura(os_aneks_fakturaid: int, tip_knizi_kod: str,
                                  nov_iznos_eur: float, user_name: str):
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        _exec_logged(
            cursor,
            "SELECT par_tip_kniziid FROM viki.par_tip_knizi WHERE par_tip_knizi = ?",
            [tip_knizi_kod]
        )
        tip_row = cursor.fetchone()
        if not tip_row:
            raise RuntimeError(f"Не е пронајден тип на книжење '{tip_knizi_kod}'.")
        nov_par_tip_kniziid = tip_row[0]

        _exec_logged(
            cursor,
            """
            SELECT x0.os_aneksid, x0.par_tip_dokumentid, x0.rata, x0.os_ponuda_detailid,
                   x0.data_faktura, x0.data_valuta, x0.os_aneks_rataid,
                   f.par_filijalaid, f.par_clientid, f.par_yearid, f.datum, f.datum_knizi,
                   f.datum_stavka, f.datum_fakt_valuta, f.par_valutaid, f.par_kursid,
                   f.os_polisaid, f.par_agent_id, f.pat_tip_platiid,
                   x2.os_polisaid
            FROM viki.os_aneks_faktura x0
            JOIN viki.os_aneks x1 ON x1.os_aneksid = x0.os_aneksid
            JOIN viki.os_polisa x2 ON x2.os_polisaid = x1.os_polisaid
            LEFT JOIN viki.fin_stavka f
                   ON f.os_aneks_fakturaid = x0.os_aneks_fakturaid AND f.iznos_d IS NOT NULL
            WHERE x0.os_aneks_fakturaid = ?
            """,
            [os_aneks_fakturaid]
        )
        src = cursor.fetchone()
        if not src:
            raise RuntimeError(f"Фактурата {os_aneks_fakturaid} не е пронајдена.")

        (os_aneksid, par_tip_dokumentid, rata, os_ponuda_detailid, data_faktura, data_valuta,
         os_aneks_rataid, par_filijalaid, par_clientid, par_yearid, datum, datum_knizi,
         datum_stavka, datum_fakt_valuta, par_valutaid, par_kursid, os_polisaid, par_agent_id,
         pat_tip_platiid, os_polisaid_reliable) = src

        _exec_logged(
            cursor,
            """
            SELECT MAX(os_ponuda_detailid)
            FROM os_ponuda_detail
            WHERE os_ponudaid IN (
                SELECT os_ponudaid FROM viki.os_ponuda
                WHERE os_ponudaid IN (
                    SELECT os_ponudaid FROM viki.os_polisa WHERE os_polisaid = ?
                )
            )
            AND ts_type_insuranceid IN (
                SELECT ts_type_insuranceid FROM viki.par_tip_knizi WHERE par_tip_kniziid = ?
            )
            """,
            [os_polisaid_reliable, nov_par_tip_kniziid]
        )
        detail_row = cursor.fetchone()
        if not detail_row or detail_row[0] is None:
            raise RuntimeError(
                f"Не е пронајдена соодветна ставка (os_ponuda_detail) за тип на книжење '{tip_knizi_kod}'."
            )
        os_ponuda_detailid = detail_row[0]

        nov_iznos = nov_iznos_eur
        nov_iznos_denari = _konverzija_eur_mkd(cursor, data_faktura, nov_iznos_eur)

        data_faktura_db = _to_db_date(data_faktura)
        data_valuta_db = _to_db_date(data_valuta)
        datum_db = _to_db_date(datum)
        datum_knizi_db = _to_db_date(datum_knizi)
        datum_stavka_db = _to_db_date(datum_stavka)
        datum_fakt_valuta_db = _to_db_date(datum_fakt_valuta)

        _exec_logged(cursor, "SELECT sq_os_aneks_fakturaid.NEXTVAL FROM systables WHERE tabid = 1")
        nov_os_aneks_fakturaid = cursor.fetchone()[0]

        _exec_logged(
            cursor,
            """
            INSERT INTO viki.os_aneks_faktura(
                os_aneks_fakturaid, datecreated, usercreated, version,
                os_aneksid, par_tip_dokumentid, par_tip_kniziid, rata, os_ponuda_detailid,
                data_faktura, data_valuta, iznos, iznos_denari, par_statusid, os_aneks_rataid)
            VALUES (?, CURRENT, ?, 0,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 1, ?)
            """,
            [nov_os_aneks_fakturaid, user_name,
             os_aneksid, par_tip_dokumentid, nov_par_tip_kniziid, rata, os_ponuda_detailid,
             data_faktura_db, data_valuta_db, nov_iznos, nov_iznos_denari, os_aneks_rataid]
        )

        if par_filijalaid is not None:
            _exec_logged(cursor, "SELECT sq_fin_stavka.NEXTVAL FROM systables WHERE tabid = 1")
            nov_fin_stavkaid = cursor.fetchone()[0]

            _exec_logged(
                cursor,
                """
                INSERT INTO viki.fin_stavka(
                    fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
                    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
                    par_yearid, datum, datum_knizi, datum_stavka, datum_fakt_valuta, par_valutaid,
                    par_kursid, os_polisaid, par_agent_id, pat_tip_platiid,
                    iznos_otvoren, f_rs, iznos_d, iznos_d_den, par_statusid)
                VALUES (?, CURRENT, ?, 0, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, 'R', ?, ?, 1)
                """,
                [nov_fin_stavkaid, user_name, par_filijalaid,
                 par_tip_dokumentid, nov_par_tip_kniziid, par_clientid, nov_os_aneks_fakturaid,
                 par_yearid, datum_db, datum_knizi_db, datum_stavka_db, datum_fakt_valuta_db, par_valutaid,
                 par_kursid, os_polisaid, par_agent_id, pat_tip_platiid,
                 nov_iznos, nov_iznos, nov_iznos_denari]
            )

        try:
            conn.commit()
        except Exception:
            pass

        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().isoformat(timespec='seconds')}] user={user_name} "
                f"DOPOLNITELNO_OSIGURUVANJE izvor_fakturaid={os_aneks_fakturaid} "
                f"nova_fakturaid={nov_os_aneks_fakturaid} tip_knizi={tip_knizi_kod} "
                f"iznos={nov_iznos} iznos_denari={nov_iznos_denari}\n"
            )

        return nov_os_aneks_fakturaid
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


def _dodaj_stavka_kolektivno(os_aneks_fakturaid: int, nov_iznos_naveden: float, user_name: str):
    """Наместо директна промена на веќе прокнижена фактура, се додава нов анекс
    (датиран денес) со копирана ставка и целосниот нов износ, за да падне во
    денешното автоматско книжење наместо да предизвика разлика со финансии."""
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        _exec_logged(
            cursor,
            """
            SELECT x0.par_tip_dokumentid, x0.par_tip_kniziid, x0.rata, x0.os_ponuda_detailid,
                   x0.os_aneks_rataid, x0.data_faktura, x0.data_valuta,
                   x1.os_aneks, x1.par_yearid, x1.os_polisaid, x1.par_clientid,
                   x1.par_valutaid, x1.par_tip_platiid, x1.br_rati, x1.godisnica_aneks,
                   f.par_filijalaid, f.par_agent_id, f.pat_tip_platiid,
                   f.datum, f.datum_knizi, f.datum_stavka, f.datum_fakt_valuta,
                   d.par_kursid
            FROM viki.os_aneks_faktura x0
            JOIN viki.os_aneks x1 ON x1.os_aneksid = x0.os_aneksid
            LEFT JOIN viki.fin_stavka f
                   ON f.os_aneks_fakturaid = x0.os_aneks_fakturaid AND f.iznos_d IS NOT NULL
            LEFT JOIN os_ponuda_detail d ON d.os_ponuda_detailid = x0.os_ponuda_detailid
            WHERE x0.os_aneks_fakturaid = ?
            """,
            [os_aneks_fakturaid]
        )
        src = cursor.fetchone()
        if not src:
            raise RuntimeError(f"Фактурата {os_aneks_fakturaid} не е пронајдена.")

        (par_tip_dokumentid, par_tip_kniziid, rata, os_ponuda_detailid, os_aneks_rataid,
         data_faktura, data_valuta,
         os_aneks_broj, par_yearid, os_polisaid, par_clientid, par_valutaid, par_tip_platiid,
         br_rati, godisnica_aneks, par_filijalaid, par_agent_id, pat_tip_platiid,
         fs_datum, fs_datum_knizi, fs_datum_stavka, fs_datum_fakt_valuta, par_kursid) = src

        # Датумот на фактурата/валутата НЕ се менуваат — остануваат исти како
        # на изворната фактура. Само датумот на анексот (datum_aneks/datum_potpis)
        # е денешен, за да се препознае корективниот анекс како создаден денес.
        denes = datetime.date.today()
        denes_db = _to_db_date(denes)
        godisnica_aneks_db = _to_db_date(godisnica_aneks)
        data_faktura_db = _to_db_date(data_faktura)
        data_valuta_db = _to_db_date(data_valuta)
        fs_datum_db = _to_db_date(fs_datum) if fs_datum is not None else data_faktura_db
        fs_datum_knizi_db = _to_db_date(fs_datum_knizi) if fs_datum_knizi is not None else data_valuta_db
        fs_datum_stavka_db = _to_db_date(fs_datum_stavka) if fs_datum_stavka is not None else data_faktura_db
        fs_datum_fakt_valuta_db = _to_db_date(fs_datum_fakt_valuta) if fs_datum_fakt_valuta is not None else data_valuta_db

        valuta_kod = _vrati_valuta_kod(cursor, par_valutaid)
        nov_iznos = nov_iznos_naveden
        nov_iznos_denari = _konverzija_na_mkd(cursor, data_faktura, nov_iznos, valuta_kod)

        # Ако веќе постои "корективен" анекс со ист број/година за оваа полиса,
        # креиран денес (пр. од претходна ставка додадена истиот ден под истиот
        # анекс), се користи истиот наместо да се создава дупликат анекс со
        # ист (os_aneks, par_yearid) — тоа предизвикуваше дупли анекси кога
        # се коригираат повеќе фактури под ист анекс во еден ден.
        _exec_logged(
            cursor,
            """
            SELECT os_aneksid, NVL(iznos_premija,0), NVL(iznos_premija_den,0)
            FROM viki.os_aneks
            WHERE os_polisaid = ? AND os_aneks = ? AND par_yearid = ? AND datum_aneks = ?
            """,
            [os_polisaid, os_aneks_broj, par_yearid, denes_db]
        )
        postoechki = cursor.fetchone()

        if postoechki:
            nov_os_aneksid, star_premija, star_premija_den = postoechki
            _exec_logged(
                cursor,
                "UPDATE viki.os_aneks SET iznos_premija = ?, iznos_premija_den = ? WHERE os_aneksid = ?",
                [float(star_premija or 0) + nov_iznos, float(star_premija_den or 0) + nov_iznos_denari, nov_os_aneksid]
            )
        else:
            _exec_logged(cursor, "SELECT sq_os_aneksid.NEXTVAL FROM systables WHERE tabid = 1")
            nov_os_aneksid = cursor.fetchone()[0]

            _exec_logged(
                cursor,
                """
                INSERT INTO viki.os_aneks(
                    os_aneksid, datecreated, usercreated, version,
                    os_aneks, par_yearid, datum_aneks, datum_potpis,
                    os_polisaid, par_clientid, par_valutaid, par_tip_platiid,
                    br_rati, iznos_premija, iznos_premija_den, par_statusid, godisnica_aneks)
                VALUES (?, CURRENT, ?, 0,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, 1, ?)
                """,
                [nov_os_aneksid, user_name,
                 os_aneks_broj, par_yearid, denes_db, denes_db,
                 os_polisaid, par_clientid, par_valutaid, par_tip_platiid,
                 br_rati, nov_iznos, nov_iznos_denari, godisnica_aneks_db]
            )

        _exec_logged(cursor, "SELECT sq_os_aneks_fakturaid.NEXTVAL FROM systables WHERE tabid = 1")
        nov_os_aneks_fakturaid = cursor.fetchone()[0]

        _exec_logged(
            cursor,
            """
            INSERT INTO viki.os_aneks_faktura(
                os_aneks_fakturaid, datecreated, usercreated, version,
                os_aneksid, par_tip_dokumentid, par_tip_kniziid, rata, os_ponuda_detailid,
                data_faktura, data_valuta, iznos, iznos_denari, par_statusid, os_aneks_rataid)
            VALUES (?, CURRENT, ?, 0,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 1, ?)
            """,
            [nov_os_aneks_fakturaid, user_name,
             nov_os_aneksid, par_tip_dokumentid, par_tip_kniziid, rata, os_ponuda_detailid,
             data_faktura_db, data_valuta_db, nov_iznos, nov_iznos_denari, os_aneks_rataid]
        )

        if par_filijalaid is not None:
            _exec_logged(cursor, "SELECT sq_fin_stavka.NEXTVAL FROM systables WHERE tabid = 1")
            nov_fin_stavkaid = cursor.fetchone()[0]

            _exec_logged(
                cursor,
                """
                INSERT INTO viki.fin_stavka(
                    fin_stavkaid, datecreated, usercreated, version, par_filijalaid,
                    par_tip_dokumentid, par_tip_kniziid, par_clientid, os_aneks_fakturaid,
                    par_yearid, datum, datum_knizi, datum_stavka, datum_fakt_valuta, par_valutaid,
                    par_kursid, os_polisaid, par_agent_id, pat_tip_platiid,
                    iznos_otvoren, f_rs, iznos_d, iznos_d_den, par_statusid)
                VALUES (?, CURRENT, ?, 0, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, 'R', ?, ?, 1)
                """,
                [nov_fin_stavkaid, user_name, par_filijalaid,
                 par_tip_dokumentid, par_tip_kniziid, par_clientid, nov_os_aneks_fakturaid,
                 par_yearid, fs_datum_db, fs_datum_knizi_db, fs_datum_stavka_db, fs_datum_fakt_valuta_db, par_valutaid,
                 par_kursid, os_polisaid, par_agent_id, pat_tip_platiid,
                 nov_iznos, nov_iznos, nov_iznos_denari]
            )

        try:
            conn.commit()
        except Exception:
            pass

        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().isoformat(timespec='seconds')}] user={user_name} "
                f"DODAJ_STAVKA_KOLEKTIVNO izvor_fakturaid={os_aneks_fakturaid} "
                f"nov_aneksid={nov_os_aneksid} nova_fakturaid={nov_os_aneks_fakturaid} "
                f"iznos={nov_iznos} iznos_denari={nov_iznos_denari}\n"
            )

        return nov_os_aneksid, nov_os_aneks_fakturaid
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


def _smeni_datum_faktura(os_aneks_fakturaid: int, nova_godina: int, user_name: str):
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        _exec_logged(
            cursor,
            """
            SELECT os_aneksid, rata, par_tip_kniziid, os_ponuda_detailid,
                   data_faktura, data_valuta
            FROM viki.os_aneks_faktura
            WHERE os_aneks_fakturaid = ?
            """,
            [os_aneks_fakturaid]
        )
        src = cursor.fetchone()
        if not src:
            raise RuntimeError(f"Фактурата {os_aneks_fakturaid} не е пронајдена.")

        (os_aneksid, rata, par_tip_kniziid, os_ponuda_detailid,
         data_faktura, data_valuta) = src

        stara_data_faktura = _to_py_date(data_faktura)
        stara_data_valuta = _to_py_date(data_valuta)
        if stara_data_faktura is None:
            raise RuntimeError("Фактурата нема валиден датум на фактура.")

        _exec_logged(
            cursor,
            """
            SELECT py.par_year
            FROM viki.os_aneks a
            JOIN viki.par_year py ON py.par_yearid = a.par_yearid
            WHERE a.os_aneksid = ?
            """,
            [os_aneksid]
        )
        aneks_year_row = cursor.fetchone()
        if not aneks_year_row:
            raise RuntimeError("Не можe да се утврди годината на анексот.")
        aneks_godina = int(aneks_year_row[0])

        delta_godini = nova_godina - aneks_godina

        def _shift_year(d):
            if d is None:
                return None
            try:
                return d.replace(year=d.year + delta_godini)
            except ValueError:
                # 29.02 во невисока година
                return d.replace(year=d.year + delta_godini, day=28)

        nova_data_faktura = _shift_year(stara_data_faktura)
        nova_data_valuta = _shift_year(stara_data_valuta)

        if os_ponuda_detailid is None:
            detail_clause = "os_ponuda_detailid IS NULL"
            detail_params = []
        else:
            detail_clause = "os_ponuda_detailid = ?"
            detail_params = [os_ponuda_detailid]

        _exec_logged(
            cursor,
            f"""
            SELECT COUNT(*) FROM viki.os_aneks_faktura
            WHERE os_aneksid = ? AND rata = ? AND par_tip_kniziid = ?
              AND {detail_clause}
              AND data_faktura = ?
              AND os_aneks_fakturaid <> ?
            """,
            [os_aneksid, rata, par_tip_kniziid, *detail_params,
             _to_db_date(nova_data_faktura), os_aneks_fakturaid]
        )
        kolizija = cursor.fetchone()
        if kolizija and kolizija[0]:
            raise RuntimeError(
                f"Веќе постои фактура за истиот анекс/рата/тип за {nova_godina} година (колизија)."
            )

        _exec_logged(
            cursor,
            "SELECT par_yearid FROM viki.par_year WHERE par_year = ?",
            [nova_godina]
        )
        year_row = cursor.fetchone()
        if not year_row:
            raise RuntimeError(f"Не е пронајдена година {nova_godina} во par_year.")
        nov_par_yearid = year_row[0]

        nova_data_faktura_db = _to_db_date(nova_data_faktura)
        nova_data_valuta_db = _to_db_date(nova_data_valuta)

        _exec_logged(
            cursor,
            "UPDATE viki.os_aneks_faktura SET data_faktura = ?, data_valuta = ? "
            "WHERE os_aneks_fakturaid = ?",
            [nova_data_faktura_db, nova_data_valuta_db, os_aneks_fakturaid]
        )

        _exec_logged(
            cursor,
            "UPDATE viki.fin_stavka SET par_yearid = ?, datum = ?, datum_knizi = ? "
            "WHERE os_aneks_fakturaid = ? AND iznos_d IS NOT NULL",
            [nov_par_yearid, nova_data_faktura_db, nova_data_valuta_db, os_aneks_fakturaid]
        )

        try:
            conn.commit()
        except Exception:
            pass

        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().isoformat(timespec='seconds')}] user={user_name} "
                f"PROMENA_DATUM_FAKTURA os_aneks_fakturaid={os_aneks_fakturaid} "
                f"data_faktura: {stara_data_faktura} -> {nova_data_faktura} | "
                f"data_valuta: {stara_data_valuta} -> {nova_data_valuta} | "
                f"par_yearid -> {nov_par_yearid}\n"
            )

        return nova_data_faktura, nova_data_valuta
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


def _smeni_godina_aneks(os_aneksid: int, nova_godina: int, user_name: str):
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or cursor is None:
        raise RuntimeError("Нема конекција кон базата")
    try:
        _exec_logged(
            cursor,
            """
            SELECT a.os_aneks, a.os_polisaid, py.par_year
            FROM viki.os_aneks a
            JOIN viki.par_year py ON py.par_yearid = a.par_yearid
            WHERE a.os_aneksid = ?
            """,
            [os_aneksid]
        )
        aneks_row = cursor.fetchone()
        if not aneks_row:
            raise RuntimeError(f"Анексот {os_aneksid} не е пронајден.")
        os_aneks_broj, os_polisaid, aneks_godina = aneks_row
        aneks_godina = int(aneks_godina)

        delta_godini = nova_godina - aneks_godina

        # Забелешка: намерно НЕ се проверува колизија на (os_aneks, par_year) —
        # може легитимно да постојат повеќе os_aneks редови со ист број/година
        # (пр. корективен анекс од "Додади ставка"), сè додека os_aneksid е различен.

        _exec_logged(
            cursor,
            "SELECT par_yearid FROM viki.par_year WHERE par_year = ?",
            [nova_godina]
        )
        year_row = cursor.fetchone()
        if not year_row:
            raise RuntimeError(f"Не е пронајдена година {nova_godina} во par_year.")
        nov_par_yearid = year_row[0]

        _exec_logged(
            cursor,
            "SELECT os_aneks_fakturaid, data_faktura, data_valuta FROM viki.os_aneks_faktura "
            "WHERE os_aneksid = ?",
            [os_aneksid]
        )
        fakturi = cursor.fetchall()

        def _shift_year(d):
            if d is None:
                return None
            try:
                return d.replace(year=d.year + delta_godini)
            except ValueError:
                return d.replace(year=d.year + delta_godini, day=28)

        izmeneti_fakturi = 0
        for os_aneks_fakturaid, data_faktura, data_valuta in fakturi:
            nova_data_faktura = _shift_year(_to_py_date(data_faktura))
            nova_data_valuta = _shift_year(_to_py_date(data_valuta))
            nova_data_faktura_db = _to_db_date(nova_data_faktura)
            nova_data_valuta_db = _to_db_date(nova_data_valuta)

            _exec_logged(
                cursor,
                "UPDATE viki.os_aneks_faktura SET data_faktura = ?, data_valuta = ? "
                "WHERE os_aneks_fakturaid = ?",
                [nova_data_faktura_db, nova_data_valuta_db, os_aneks_fakturaid]
            )
            _exec_logged(
                cursor,
                "UPDATE viki.fin_stavka SET par_yearid = ?, datum = ?, datum_knizi = ? "
                "WHERE os_aneks_fakturaid = ? AND iznos_d IS NOT NULL",
                [nov_par_yearid, nova_data_faktura_db, nova_data_valuta_db, os_aneks_fakturaid]
            )
            izmeneti_fakturi += 1

        _exec_logged(
            cursor,
            "UPDATE viki.os_aneks SET par_yearid = ? WHERE os_aneksid = ?",
            [nov_par_yearid, os_aneksid]
        )

        try:
            conn.commit()
        except Exception:
            pass

        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.datetime.now().isoformat(timespec='seconds')}] user={user_name} "
                f"PROMENA_GODINA_ANEKS os_aneksid={os_aneksid} os_aneks={os_aneks_broj} "
                f"godina: {aneks_godina} -> {nova_godina} | fakturi_izmeneti={izmeneti_fakturi}\n"
            )

        return izmeneti_fakturi
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


def _render(request, user, polisa_broj, tip_promena, rows, error, success, aneksi=None):
    return templates.TemplateResponse("promena_premija.html", {
        "request":            request,
        "user":               user,
        "active":             "promena_premija",
        "tipovi":             TIPOVI_PROMENA,
        "tipovi_knizi_dopolnitelno": TIP_KNIZI_DOPOLNITELNO,
        "polisa_broj":        polisa_broj,
        "tip_promena":        tip_promena,
        "rows":               rows,
        "aneksi":             aneksi,
        "error":              error,
        "success":            success,
    })


def _fetch_za_prikaz(polisa_broj, tip_promena):
    if tip_promena == "promena_godina_aneks":
        return None, _fetch_aneksi(polisa_broj)
    return _fetch_fakturi(polisa_broj), None


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

    rows, aneksi, error = None, None, None
    try:
        rows, aneksi = _fetch_za_prikaz(polisa_broj, tip_promena)
        if not rows and not aneksi:
            error = "Нема пронајдени резултати за оваа полиса."
    except Exception as e:
        error = str(e)

    return _render(request, user, polisa_broj, tip_promena, rows, error, None, aneksi=aneksi)


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


@router.post("/promena-premija/izbrisi-stavka")
def promena_premija_izbrisi_stavka(
    request:            Request,
    polisa_broj:        str = Form(...),
    tip_promena:        str = Form(...),
    os_aneks_fakturaid: int = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    try:
        os_aneks_izbrisan = _izbrisi_stavka(os_aneks_fakturaid, user_name)
        success = "Ставката е успешно избришана." + (
            " Празниот анекс исто така е отстранет." if os_aneks_izbrisan else ""
        )
    except Exception as e:
        error = str(e)

    rows = None
    try:
        rows = _fetch_fakturi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, rows, error, success)


@router.post("/promena-premija/izbrisi-stavki")
def promena_premija_izbrisi_stavki(
    request:     Request,
    polisa_broj: str = Form(...),
    tip_promena: str = Form(...),
    fakturi_ids: List[int] = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    izbrisani, greski = [], []
    for os_aneks_fakturaid in fakturi_ids:
        try:
            _izbrisi_stavka(os_aneks_fakturaid, user_name)
            izbrisani.append(os_aneks_fakturaid)
        except Exception as e:
            greski.append(f"{os_aneks_fakturaid}: {e}")

    if izbrisani:
        success = f"Успешно избришани {len(izbrisani)} ставка(и)."
    if greski:
        error = "Некои ставки не можеа да се избришат — " + "; ".join(greski)

    rows = None
    try:
        rows = _fetch_fakturi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, rows, error, success)


@router.post("/promena-premija/dodaj-stavka")
def promena_premija_dodaj_stavka(
    request:            Request,
    polisa_broj:        str = Form(...),
    tip_promena:        str = Form(...),
    os_aneks_fakturaid: int = Form(...),
    nov_iznos:          float = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    try:
        nov_os_aneksid, nov_os_aneks_fakturaid = _dodaj_stavka_kolektivno(
            os_aneks_fakturaid, nov_iznos, user_name
        )
        success = (
            f"Успешно е додадена нова ставка (анекс {nov_os_aneksid}, фактура "
            f"{nov_os_aneks_fakturaid}) со износ {nov_iznos:.2f}, датирана денес."
        )
    except Exception as e:
        error = str(e)

    rows = None
    try:
        rows = _fetch_fakturi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, rows, error, success)


@router.post("/promena-premija/dodaj-dopolnitelno")
def promena_premija_dodaj_dopolnitelno(
    request:          Request,
    polisa_broj:      str = Form(...),
    tip_promena:      str = Form(...),
    tip_knizi_novo:   str = Form(...),
    fakturi_ids:      List[int] = Form(...),
    nov_iznos:        float = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    kreirani = []
    try:
        for os_aneks_fakturaid in fakturi_ids:
            nov_id = _create_dopolnitelno_faktura(
                os_aneks_fakturaid, tip_knizi_novo, nov_iznos, user_name
            )
            kreirani.append(nov_id)
        success = f"Успешно се креирани {len(kreirani)} нова(и) фактура(и) за дополнително осигурување."
    except Exception as e:
        error = str(e)

    rows = None
    try:
        rows = _fetch_fakturi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, rows, error, success)


@router.post("/promena-premija/smeni-datum")
def promena_premija_smeni_datum(
    request:     Request,
    polisa_broj: str = Form(...),
    tip_promena: str = Form(...),
    fakturi_ids: List[int] = Form(...),
    nova_godina: int = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    izmeneti = []
    try:
        for os_aneks_fakturaid in fakturi_ids:
            _smeni_datum_faktura(os_aneks_fakturaid, nova_godina, user_name)
            izmeneti.append(os_aneks_fakturaid)
        success = f"Успешно се изменети {len(izmeneti)} фактура(и) на година {nova_godina}."
    except Exception as e:
        error = str(e)

    rows = None
    try:
        rows = _fetch_fakturi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, rows, error, success)


@router.post("/promena-premija/smeni-godina-aneks")
def promena_premija_smeni_godina_aneks(
    request:     Request,
    polisa_broj: str = Form(...),
    tip_promena: str = Form(...),
    os_aneksid:  int = Form(...),
    nova_godina: int = Form(...),
):
    user, redirect = _require_role(request)
    if redirect:
        return redirect

    error, success = None, None
    user_name = user.get("username") or user.get("name") or "?"
    try:
        br_fakturi = _smeni_godina_aneks(os_aneksid, nova_godina, user_name)
        success = f"Анексот е успешно префрлен на година {nova_godina} ({br_fakturi} фактура(и) изменети)."
    except Exception as e:
        error = str(e)

    aneksi = None
    try:
        aneksi = _fetch_aneksi(polisa_broj)
    except Exception:
        pass

    return _render(request, user, polisa_broj, tip_promena, None, error, success, aneksi=aneksi)

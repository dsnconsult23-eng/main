# aso_reports.py

import pandas as pd
from io import BytesIO
import calendar

from routers import ASO
from routers import Connection
from typing import Dict, Optional
import re




# =========================================================
# CONSTANTS
# =========================================================

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

USER_CREATED = "admin"


# =========================================================
# EXISTING REPORT FUNCTIONS (UNCHANGED)
# =========================================================

def ImportSI(mesec, godina):
    try:
        month_number = MONTHS.index(mesec) + 1
        OK, _, rez = ASO.prebSI(month_number, godina)
        if not OK:
            return False, "❌ Грешка при пребарување број 1"
        return True, f"✅ Операцијата е успешна! Резултат: {rez}"
    except Exception as e:
        return False, f"⚠️ Грешка: {str(e)}"


def genSI(mesec, godina):
    try:
        month_number = MONTHS.index(mesec) + 1
        OK, rez = ASO.ImportSISp11(month_number, godina)
        if not OK:
            return False, f"❌ Грешка: {rez}"
        return True, f"✅ Операцијата е успешна! Резултат: {rez}"
    except Exception as e:
        return False, f"⚠️ Грешка: {str(e)}"


def Sp1analitika_a(mesec, godina):
    try:
        month_number = MONTHS.index(mesec) + 1
        OK, rez = ASO.SP1analitika2(month_number, godina)
        if not OK:
            return False, f"❌ Грешка: {rez}"
        return True, f"✅ Операцијата е успешна! Резултат: {rez}"
    except Exception as e:
        return False, f"⚠️ Грешка: {str(e)}"


def Sp2analitika_a(mesec, godina):
    try:
        month_number = MONTHS.index(mesec) + 1
        OK, rez = ASO.SP2analitika(month_number, godina)
        if not OK:
            return False, f"❌ Грешка: {rez}"
        return True, f"✅ Операцијата е успешна! Резултат: {rez}"
    except Exception as e:
        return False, f"⚠️ Грешка: {str(e)}"


# =========================================================
# EXCEL PARSER
# =========================================================

def _parse_sheet_df(excel_bytes: bytes, sheet_name: str,skiprowsdef :int) -> pd.DataFrame:
    """
    - Reads from row 10 (skip first 9 rows)
    - Column B (index 1) => vid_stavka
    - Cleans vid_stavka values (19, 1901, 190101)
    """

    print(f"[EXCEL] Reading sheet: {sheet_name}")

    df = pd.read_excel(
        BytesIO(excel_bytes),
        sheet_name=sheet_name,
        skiprows=skiprowsdef  # ✅ start from row 9
    )

    if df is None or df.empty:
        print(f"[EXCEL] Sheet {sheet_name} is EMPTY")
        return pd.DataFrame()

    if len(df.columns) < 2:
        print(f"[EXCEL] Sheet {sheet_name} invalid: <2 columns")
        return pd.DataFrame()

    print(f"[EXCEL] Columns found: {list(df.columns)}")
    print(f"[EXCEL] Total rows before cleaning: {len(df)}")

    # Column B -> vid_stavka
    df = df.rename(columns={df.columns[1]: "vid_stavka"})

    # normalize col names
    df.columns = [str(c).strip() for c in df.columns]

    # clean vid_stavka
    df["vid_stavka"] = (
        df["vid_stavka"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    # drop empty rows
    df = df[df["vid_stavka"].notna() & (df["vid_stavka"] != "")]

    print(f"[EXCEL] Rows after cleaning: {len(df)}")
    print("[EXCEL] First 5 vid_stavka values:")
    print(df["vid_stavka"].head())

    return df


# =========================================================
# CORE INSERT (INFORMIX SAFE)
# =========================================================


from decimal import Decimal, InvalidOperation


from typing import Optional

import calendar
import pandas as pd
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any

def _insert_rows_stat_izvestai(
    *,
    df: pd.DataFrame,
    mesec: str,
    godina: int,
    stat_izvestaj_value: str,
    excel_to_db: Dict[Any, str],          # <-- може int (index) или str (name)
    usercreated: str = USER_CREATED,
    treat_empty_as_null: bool = True,
    cast_decimals: Optional[str] = None
):
    def _norm_colname(x) -> str:
        return str(x).replace("\n", " ").replace("\r", " ").strip()

    def _to_decimal_or_none(v):
        if v is None:
            return None if treat_empty_as_null else Decimal("0")
        try:
            if pd.isna(v):
                return None if treat_empty_as_null else Decimal("0")
        except Exception:
            pass

        s = str(v).strip()
        if s == "" or s.lower() in ("nan", "none", "null", "inf", "-inf"):
            return None if treat_empty_as_null else Decimal("0")

        # normalize MK/EU formats:
        s = s.replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")

        try:
            return Decimal(s)
        except InvalidOperation:
            return None if treat_empty_as_null else Decimal("0")

    # Date
    month = MONTHS.index(mesec) + 1
    year = int(godina)
    day = calendar.monthrange(year, month)[1]

    results, OK = Connection.OSISinit()
    if not OK:
        return False, "Nema vrska so baza"

    if df is None or df.empty:
        return False, "Нема редови за внес (df е празен)."

    df = df.copy()
    df.columns = [_norm_colname(c) for c in df.columns]

    # IMPORTANT: НЕ ги нормализирај int клучевите во стринг!
    excel_to_db_fixed = {}
    for k, v in (excel_to_db or {}).items():
        if isinstance(k, int):
            excel_to_db_fixed[k] = v
        else:
            excel_to_db_fixed[_norm_colname(k)] = v
    excel_to_db = excel_to_db_fixed

    inserted = 0
    print("[DB] Report:", stat_izvestaj_value)
    print(f"[DB] Datum: {day:02d}.{month:02d}.{year}")
    print("[DB] Rows to insert:", len(df))
    print("[DF] columns:", list(df.columns))

    # debug: which mappings actually match?
    matched = []
    for k in excel_to_db.keys():
        if isinstance(k, int):
            if k < len(df.columns):
                matched.append((k, df.columns[k]))
        else:
            if k in df.columns:
                matched.append((k, k))
    print("[MAP] matched (first 20):", matched[:20])

    try:
        has_client = "client_name" in df.columns

        for i, r in df.iterrows():
            vid = r.get("vid_stavka")
            vid = "" if vid is None or (isinstance(vid, float) and pd.isna(vid)) else str(vid).strip()
            if not vid:
                continue

            client_name = None
            if has_client:
                cn = r.get("client_name", None)
                if cn is None or (isinstance(cn, float) and pd.isna(cn)):
                    client_name = None
                else:
                    cn = str(cn).strip()
                    client_name = cn if cn else None

            cols = [
                "stat_izvestaiid",
                "datecreated",
                "usercreated",
                "datum",
                "stat_izvestaj",
                "vid_stavka",
            ]
            vals = [
                "appuser.stat_izvestai_seq.nextval",
                "CURRENT",
                "?",
                "MDY(?, ?, ?)",
                "?",
                "?",
            ]
            params = [
                usercreated,
                int(month), int(day), int(year),
                stat_izvestaj_value,
                vid,
            ]

            if has_client:
                cols.append("client_name")
                vals.append("?")
                params.append(client_name)

            for k, db_col in excel_to_db.items():
                # resolve excel column name from mapping key
                if isinstance(k, int):
                    if k >= len(df.columns):
                        continue
                    excel_col = df.columns[k]
                else:
                    excel_col = k
                    if excel_col not in df.columns:
                        continue

                raw_val = r.get(excel_col, None)
                dec = _to_decimal_or_none(raw_val)

                cols.append(db_col)
                if cast_decimals:
                    vals.append("CAST(? AS %s)" % cast_decimals)
                    params.append(None if dec is None else str(dec))
                else:
                    vals.append("?")
                    params.append(dec)

                if inserted < 1:
                    print(f"[DBG] excel_col={excel_col} raw={raw_val!r} -> {db_col} dec={dec}")

            sql = "INSERT INTO appuser.stat_izvestai (%s) VALUES (%s)" % (
                ",".join(cols),
                ",".join(vals)
            )

            if inserted < 3:
                print("[SQL]", sql)
                print("[COLS]", cols[:10], "...", "len=", len(cols))
                print("[VALS]", vals[:10], "...", "len=", len(vals))
                print(f"[ROW {i}] vid_stavka={vid} client_name={client_name} params_len={len(params)}")

            results.execute(sql, tuple(params))
            inserted += 1

        print(f"[DB] ✅ Inserted {inserted} rows")
        return True, f"Внесени {inserted} редови."

    except Exception as e:
        print("[DB] ❌ ERROR:", str(e))
        return False, "Грешка при внес: %s" % str(e)




# =========================================================
# SHEET-SPECIFIC IMPORTS
# =========================================================

def Import_SP1_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP1_ZO] Starting import...")

    df = _parse_sheet_df(excel_bytes, "STA_SP1_ZO",8)
    if df.empty:
        print("[SP1_ZO] ❌ No data found")
        return False, "STA_SP1_ZO е празен или не постои"

    # Column C -> kol100, D -> kol101, ...
    MAP_SP1 = {
        2: "kol100",
        3: "kol102",
        4: "kol103",
        5: "kol104",
        6: "kol105",
        7: "kol106",
        8: "kol107",
        9: "kol200",
        10: "kol201",
        11: "kol202",
        12: "kol203",
        13: "kol204",
        14: "kol205",
        15: "kol206",
        16: "kol207",
        17: "kol300",
        18: "kol301",
        19: "kol302",
        20: "kol303",
        21: "kol304",
        22: "kol305",
        23: "kol306",
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-1",
        excel_to_db=MAP_SP1,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[SP1_ZO] Done: ok={ok} msg={msg}")
    return ok, msg


def Import_SP2_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP2_ZO] Starting import...")

    df = _parse_sheet_df(excel_bytes, "STA_SP2_ZO",8)
    if df.empty:
        print("[SP2_ZO] ❌ No data found")
        return False, "STA_SP2_ZO е празен или не постои"

    MAP_SP2 = {
        2: "kol100",
        3: "kol200",
        4: "kol200a",
        6: "kol201",
        7: "kol202",
        8: "kol203",
        9: "kol204",
        10: "kol205",
        11: "kol205a",
        12: "kol206",
        13: "kol207",
        14: "kol300",
        15: "kol301",
        16: "kol302",
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-2",
        excel_to_db=MAP_SP2,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[SP2_ZO] Done: ok={ok} msg={msg}")
    return ok, msg

def Import_SP3_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP3_ZO] Starting import...")

    df = _parse_sheet_df(excel_bytes, "STA_SP3_ZO",8)
    if df.empty:
        print("[SP3_ZO] ❌ No data found")
        return False, "STA_SP3_ZO е празен или не постои"

    MAP_SP3 = {
        2: "kol100",
        3: "kol101",
        4: "kol102",
        5: "kol200",
        6: "kol300",
        7: "kol301",
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-3",
        excel_to_db=MAP_SP3,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[SP3_ZO] Done: ok={ok} msg={msg}")
    return ok, msg

def Import_SP4_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP4_ZO] Starting import...")

    df = _parse_sheet_df(excel_bytes, "STA_SP4_ZO",8)
    if df.empty:
        print("[STA_SP4_ZO] ❌ No data found")
        return False, "STA_SP4_ZO е празен или не постои"

    MAP_SP4 = {
        2: "kol100",  # C
        3: "kol101",  # D
        4: "kol102",  # E
        5: "kol103",  # F
        6: "kol104",  # G
        7: "kol105",  # H
        8: "kol106",  # I
        9: "kol107",  # J
    }
    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-4",
        excel_to_db=MAP_SP4,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[STA_SP4_ZO] Done: ok={ok} msg={msg}")
    return ok, msg


def Import_SP7_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP7_ZO] Starting import...")

    # Sheet: STA_SP7_ZO
    # NOTE: assumes _parse_sheet_df supports skiprows parameter
    # Example: def _parse_sheet_df(excel_bytes, sheet_name, skiprows=9)
    df = _parse_sheet_df(excel_bytes, "STA_SP7_ZO", 8)
    if df.empty:
        print("[STA_SP7_ZO] ❌ No data found")
        return False, "STA_SP7_ZO е празен или не постои"

    # Based on your screenshot:
    # B = vid_stavka
    # C..J = 100..107
    MAP_SP7 = {
        2: "kol100",  # C
        3: "kol101",  # D
        4: "kol102",  # E
        5: "kol103",  # F
        6: "kol104",  # G
        7: "kol105",  # H
        8: "kol106",  # I
        9: "kol107",  # J
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-7",
        excel_to_db=MAP_SP7,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[STA_SP7_ZO] Done: ok={ok} msg={msg}")
    return ok, msg

def Import_SP4_RS_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP4_RS_ZO] Starting import...")

    # Sheet: STA_SP4_RS_ZO
    df = _parse_sheet_df(excel_bytes, "STA_SP4_RS_ZO", 8)
    if df.empty:
        print("[STA_SP4_RS_ZO] ❌ No data found")
        return False, "STA_SP4_RS_ZO е празен или не постои"

    # Based on your screenshot:
    # B = vid_stavka
    # C..H = 200..205
    # I..N = 300..305
    #
    # Index mapping (0=A, 1=B, 2=C, ...):
    # C=2 -> kol200
    # D=3 -> kol201
    # E=4 -> kol202
    # F=5 -> kol203
    # G=6 -> kol204
    # H=7 -> kol205
    # I=8 -> kol300
    # J=9 -> kol301
    # K=10 -> kol302
    # L=11 -> kol303
    # M=12 -> kol304
    # N=13 -> kol305
    MAP_SP4_RS = {
        2: "kol200",
        3: "kol201",
        4: "kol202",
        5: "kol203",
        6: "kol204",
        7: "kol205",
        8: "kol300",
        9: "kol301",
        10: "kol302",
        11: "kol303",
        12: "kol304",
        13: "kol305",
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-4-RS",
        excel_to_db=MAP_SP4_RS,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[STA_SP4_RS_ZO] Done: ok={ok} msg={msg}")
    return ok, msg

def Import_SP4_MR(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP4_MR] Starting import (978 -> kol101_1, 807 -> kol101_2)...")

    sheet_978 = "STA_SP4_VU_MR - 978"
    sheet_807 = "STA_SP4_VU_MR - 807"

    # read from row 10; column B = vid_stavka (your _parse_sheet_df already does that)
    df_978 = _parse_sheet_df(excel_bytes, sheet_978, 9)
    df_807 = _parse_sheet_df(excel_bytes, sheet_807, 9)

    if df_978.empty and df_807.empty:
        print("[SP4_MR] ❌ Both sheets are empty/missing")
        return False, "STA_SP4_VU_MR - 978 и STA_SP4_VU_MR - 807 се празни или не постојат"

    # In these MR sheets you have ONLY one numeric column (column C) -> "101" in header
    # But sometimes Excel headers are messy, so we take the FIRST numeric column after vid_stavka.
    def _extract_first_value_col(df: pd.DataFrame, new_col_name: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["vid_stavka", new_col_name])

        # keep only vid_stavka + first value column after it
        cols = list(df.columns)

        if "vid_stavka" not in cols:
            return pd.DataFrame(columns=["vid_stavka", new_col_name])

        vid_idx = cols.index("vid_stavka")

        # first column after vid_stavka (usually column C in Excel)
        val_col = cols[vid_idx + 1] if vid_idx + 1 < len(cols) else None
        if not val_col:
            return pd.DataFrame(columns=["vid_stavka", new_col_name])

        out = df[["vid_stavka", val_col]].copy()
        out = out.rename(columns={val_col: new_col_name})

        # numeric clean
        out[new_col_name] = pd.to_numeric(out[new_col_name], errors="coerce").fillna(0)

        # clean vid_stavka
        out["vid_stavka"] = (
            out["vid_stavka"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        )

        return out

    df978 = _extract_first_value_col(df_978, "kol101_1")
    df807 = _extract_first_value_col(df_807, "kol101_2")

    # merge on vid_stavka -> single row per vid_stavka
    df_merged = pd.merge(df978, df807, on="vid_stavka", how="outer")
    df_merged["kol101_1"] = pd.to_numeric(df_merged.get("kol101_1", 0), errors="coerce").fillna(0)
    df_merged["kol101_2"] = pd.to_numeric(df_merged.get("kol101_2", 0), errors="coerce").fillna(0)

    # remove empty vid_stavka
    df_merged = df_merged[df_merged["vid_stavka"].notna() & (df_merged["vid_stavka"] != "")]

    if df_merged.empty:
        print("[SP4_MR] ❌ No merged rows")
        return False, "Нема редови за внес (по merge) за SP-4-MR"

    # Now insert BOTH columns into one row
    MAP_SP4_MR = {
        "kol101_1": "kol101_1",
        "kol101_2": "kol101_2",
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df_merged,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-4-MR",
        excel_to_db=MAP_SP4_MR,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[SP4_MR] Done: ok={ok} msg={msg}")
    return ok, msg

import pandas as pd
from io import BytesIO

# ----------------------------
# Helpers (NO regex)
# ----------------------------
def _read_sheet_raw(excel_bytes: bytes, sheet_name: str, skiprows: int = 8) -> pd.DataFrame:
    print(f"[EXCEL] Reading RAW sheet: {sheet_name} (skiprows={skiprows})")
    df_raw = pd.read_excel(BytesIO(excel_bytes), sheet_name=sheet_name, header=None, skiprows=skiprows)
    print(f"[EXCEL] Raw shape: {df_raw.shape}")
    return df_raw

def _norm_txt(x) -> str:
    return " ".join(str(x).replace("\u00a0", " ").split()).lower()

def _row_contains_any_plain(row_vals, needles_norm: list[str]) -> bool:
    row_join = " ".join(_norm_txt(v) for v in row_vals)
    return any(n in row_join for n in needles_norm)

def _find_row_contains_any(df_raw: pd.DataFrame, texts: list[str]) -> int:
    needles = [_norm_txt(t) for t in texts]
    for i in range(len(df_raw)):
        if _row_contains_any_plain(df_raw.iloc[i].tolist(), needles):
            return i
    return -1

def _find_next_title_row(df_raw: pd.DataFrame, start_row: int, titles_keywords: list[str], min_gap: int = 6) -> int:
    
    needles = [_norm_txt(t) for t in titles_keywords]

    begin = start_row + min_gap
    if begin < start_row + 1:
        begin = start_row + 1

    for i in range(begin, len(df_raw)):
        if _row_contains_any_plain(df_raw.iloc[i].tolist(), needles):
            return i
    return len(df_raw)


def _cell_to_token(x) -> str:
    """
    Convert cell to comparable token for header detection:
    101, 101.0, "101" -> "101"
    """
    if pd.isna(x):
        return ""
    # numeric
    if isinstance(x, (int, float)):
        try:
            xi = int(round(float(x)))
            if abs(float(x) - xi) < 1e-6:
                return str(xi)
        except Exception:
            pass
        return str(x).strip()
    # string
    s = str(x).strip()
    s = s.replace("\u00a0", " ")
    s = " ".join(s.split())
    # handle "101.0"
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    # handle plain digits
    if s.isdigit():
        return s
    return s


def _extract_block_as_table(df_raw: pd.DataFrame, start_row: int, end_row: int) -> pd.DataFrame:
    """
    From raw slice, detect the header row where we can find 101/102/103 (any of them),
    then build a table.
    """
    block = df_raw.iloc[start_row:end_row].copy()

    # DEBUG: print first ~12 rows so you can see what is inside the slice
    print(f"[EXCEL] Block slice rows: {start_row}..{end_row} (len={len(block)})")
    for i in range(min(12, len(block))):
        toks = [_cell_to_token(v) for v in block.iloc[i].tolist()]
        print(f"[EXCEL] block row+{i}: {toks}")

    header_idx = None
    max_scan = min(80, len(block))

    target_headers = {"100", "101", "102", "103", "104", "105", "106", "107"}

    for i in range(max_scan):
        toks = [_cell_to_token(v) for v in block.iloc[i].tolist()]
        hits = sum(t in target_headers for t in toks)
        # ✅ SP6 често има само 101/102/103 => доволно е 1 hit (или 2 ако сакаш построго)
        if hits >= 1:
            # дополнителна проверка: барем еден од 101/102/103
            if any(t in {"101", "102", "103"} for t in toks):
                header_idx = i
                break

    if header_idx is None:
        print("[EXCEL] ❌ Header row not found in block (no 101/102/103 detected)")
        return pd.DataFrame()

    header = [_cell_to_token(c) for c in block.iloc[header_idx].tolist()]
    data = block.iloc[header_idx + 1:].copy()
    data.columns = header

    data = data.dropna(how="all")
    return data


def _insert_rows_stat_izvestai_sp6(
    *,
    df: pd.DataFrame,
    mesec: str,
    godina: int,
    stat_izvestaj_value: str,
    include_client_name: bool = False
):
    month = MONTHS.index(mesec) + 1
    year = int(godina)
    day = calendar.monthrange(year, month)[1]  # last day

    results, OK = Connection.OSISinit()
    if not OK or results is None:
        return False, "Nema vrska so baza"

    inserted = 0

    try:
        for i, r in df.iterrows():
            vid = str(r.get("vid_stavka", "")).strip()
            if not vid or vid.lower() in ("nan", "none"):
                continue

            cols = [
                "stat_izvestaiid",
                "datecreated",
                "usercreated",
                "datum",
                "stat_izvestaj",
                "vid_stavka",
            ]

            vals = [
                "appuser.stat_izvestai_seq.nextval",
                "CURRENT",
                "?",
                "MDY(?, ?, ?)",
                "?",
                "?",
            ]

            params = [
                USER_CREATED,
                month, day, year,
                stat_izvestaj_value,
                vid,
            ]

            # optional client_name
            if include_client_name:
                cols.append("client_name")
                vals.append("?")
                params.append(str(r.get("client_name", "")).strip())

            # numeric cols
            for c, db_col in [("101", "kol101"), ("102", "kol102"), ("103", "kol103")]:
                cols.append(db_col)
                vals.append("?")
                v = r.get(c, 0)
                try:
                    v = 0 if pd.isna(v) else float(v)
                except Exception:
                    v = 0.0
                params.append(v)

            sql = f"""
                INSERT INTO appuser.stat_izvestai
                ({",".join(cols)})
                VALUES ({",".join(vals)})
            """

            # debug print
            cn = r.get("client_name", None) if include_client_name else None
            print(f"[ROW {i}] vid_stavka={vid} client_name={cn} params_len={len(params)}")

            results.execute(sql, tuple(params))
            inserted += 1

        print(f"[DB] ✅ Inserted {inserted} rows")
        return True, f"Внесени {inserted} редови."

    except Exception as e:
        print("[DB] ❌ ERROR:", str(e))
        return False, f"Грешка при внес: {str(e)}"



# def Import_SP6_ZO(excel_bytes: bytes, mesec: str, godina: int):
#     print("[SP6_ZO] Starting import...")

#     SHEET = "STA_SP6_ZO"
#     MAP_101_102_103 = {"101": "kol101", "102": "kol102", "103": "kol103"}

#     # Клучни зборови/титлови за да се најде крај на блок
#     TITLES = [
#         "сп-6",
#         "продажба по канали",
#         "осиг. брокерски друштва",
#         "друштва за застапување",
#         "банки (основно)",
#         "банки (дополнително)",
#         "банки (рентно)",
#         "банки (останато)",
#         "детали",
#         "вкупно",
#     ]

#     df_raw = _read_sheet_raw(excel_bytes, SHEET, skiprows=8)
#     if df_raw is None or df_raw.empty:
#         print("[SP6_ZO] ❌ Sheet empty")
#         return False, f"{SHEET} е празен или не постои"

#     # -----------------------------
#     # helpers
#     # -----------------------------
#     def _to_number(x):
#         # "42.192,00" -> 42192.00
#         if x is None:
#             return 0.0
#         s = str(x).strip()
#         if s == "" or s.lower() in ("nan", "none"):
#             return 0.0
#         s = s.replace(".", "").replace(",", ".")
#         try:
#             return float(s)
#         except:
#             return 0.0

#     def _detect_101_102_103_columns(tbl: pd.DataFrame):
#         """
#         Сигурно детектира каде се 101/102/103 колони.
#         Работи и кога 101/102/103 се појавуваат во првите редови како header линија.
#         """
#         # 1) ако постојат како имиња на колони
#         direct = {}
#         for c in tbl.columns:
#             sc = str(c).strip()
#             if sc in ("101", "102", "103"):
#                 direct[sc] = c
#         if len(direct) == 3:
#             return direct

#         # 2) барај во првите редови
#         head = tbl.head(10).astype(str)
#         found = {}
#         for target in ("101", "102", "103"):
#             for col_name in head.columns:
#                 if head[col_name].str.match(rf"^\s*{target}\s*$", na=False).any():
#                     found[target] = col_name
#                     break

#         if len(found) != 3:
#             raise ValueError(
#                 f"Не можам да ги детектирам 101/102/103 колоните. Колони: {list(tbl.columns)}"
#             )
#         return found

#     def _clean_rows_basic(df: pd.DataFrame):
#         # фрла празни и header-like редови во vid_stavka
#         bad = {
#             "", "nan", "none",
#             "ставка бр", "име на посредникот",
#             "0", "100", "101", "102", "103",
#         }
#         s = df["vid_stavka"].astype(str).str.strip()
#         s_low = s.str.lower()

#         df = df[s.notna()]
#         df = df[s.str.strip() != ""]
#         df = df[~s_low.isin(bad)]
#         return df

#     def _find_row_contains_any(df: pd.DataFrame, needles):
#         # пробај повеќе варијанти за старт ред
#         for n in needles:
#             idx = _find_row_contains(df, n)
#             if idx >= 0:
#                 return idx
#         return -1

#     # -----------------------------
#     # 1) Продажба по канали (summary)
#     # -----------------------------
#     def import_sales_by_channels():
#         title = "СП-6 (ж.о.): Продажба по канали"
#         print(f"[SP6_ZO] Import block: {title}")

#         start = _find_row_contains_any(df_raw, ["продажба по канали"])
#         if start < 0:
#             return False, f"Не е најден блок: {title}"

#         end = _find_next_title_row(df_raw, start, TITLES)
#         tbl = _extract_block_as_table(df_raw, start, end)
#         if tbl is None or tbl.empty:
#             return False, f"Блокот е празен: {title}"

#         # ✅ FIX: земај колони по позиција (iloc), не по име (може да е дупликат)
#         cand_a = tbl.iloc[:, 0].astype(str).str.strip()
#         cand_b = tbl.iloc[:, 1].astype(str).str.strip()

#         vid_series = cand_a.where(
#             (cand_a.notna()) & (cand_a != "") & (cand_a.str.lower() != "nan"),
#             cand_b
#         ).str.replace(r"\.0$", "", regex=True)

#         colmap = _detect_101_102_103_columns(tbl)

#         df = pd.DataFrame()
#         df["vid_stavka"] = vid_series

#         df["101"] = tbl[colmap["101"]].apply(_to_number)
#         df["102"] = tbl[colmap["102"]].apply(_to_number)
#         df["103"] = tbl[colmap["103"]].apply(_to_number)

#         df = _clean_rows_basic(df)

#         return _insert_rows_stat_izvestai(
#             df=df,
#             mesec=mesec,
#             godina=godina,
#             stat_izvestaj_value="SP-6",
#             excel_to_db=MAP_101_102_103
#         )

#     # -----------------------------
#     # 2) Детали блок (брокери/застапување/банки)
#     # -----------------------------
#     def import_detail_block(title_contains_variants, prefix: str):
#         """
#         title_contains_variants: листа со можни делови од насловот
#         prefix: "200", "300", "400-1" ...
#         """
#         print(f"[SP6_ZO] Import detail block (prefix={prefix}) variants={title_contains_variants}")

#         start = _find_row_contains_any(df_raw, title_contains_variants)
#         if start < 0:
#             return False, f"Не е најден блок: {title_contains_variants[0]}"

#         end = _find_next_title_row(df_raw, start, TITLES)
#         tbl = _extract_block_as_table(df_raw, start, end)

#         # ✅ ако блокот е реално празен -> не е грешка
#         if tbl is None or tbl.empty:
#             return True, f"Нема податоци: {title_contains_variants[0]}"

#         colmap = _detect_101_102_103_columns(tbl)

#         # A=ставка бр, B=име (но земи по позиција за да не се распадне на дупликати)
#         a_ser = tbl.iloc[:, 0].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
#         b_ser = tbl.iloc[:, 1].astype(str).str.strip()

#         df = pd.DataFrame()
#         df["vid_stavka"] = a_ser.apply(
#             lambda x: f"{prefix}_{x}" if str(x).strip().lower() not in ("", "nan", "none") else ""
#         )
#         df["client_name"] = b_ser

#         df["101"] = tbl[colmap["101"]].apply(_to_number)
#         df["102"] = tbl[colmap["102"]].apply(_to_number)
#         df["103"] = tbl[colmap["103"]].apply(_to_number)

#         df = _clean_rows_basic(df)

#         # исфрли празни client_name (header редови и празни линии)
#         cn = df["client_name"].astype(str).str.strip()
#         df = df[cn.notna()]
#         df = df[cn != ""]
#         df = df[cn.str.lower() != "nan"]

#         # ако после чистење нема редови -> исто не е грешка
#         if df.empty:
#             return True, f"Нема податоци (по чистење): {title_contains_variants[0]}"

#         return _insert_rows_stat_izvestai(
#             df=df,
#             mesec=mesec,
#             godina=godina,
#             stat_izvestaj_value="SP-6",
#             excel_to_db=MAP_101_102_103
#         )

#     # -----------------------------
#     # Run blocks
#     # -----------------------------
#     IMPORT_BLOCKS = [
#         ("SP-6 канали", import_sales_by_channels),

#         ("SP-6 брокери детали",
#          lambda: import_detail_block(
#              ["Осиг. брокерски друштва - Детали", "Осиг. брокерски друштва", "брокерски друштва - детали"],
#              "200"
#          )),

#         ("SP-6 застапување детали",
#          lambda: import_detail_block(
#              ["Друштва за застапување во осиг.  - Детали", "Друштва за застапување во осиг.", "застапување во осиг. - детали"],
#              "300"
#          )),

#         ("SP-6 банки основно детали",
#          lambda: import_detail_block(
#              ["Банки (основно) - Детали", "Банки (основно)", "банки (основно)"],
#              "400-1"
#          )),

#         ("SP-6 банки дополнително детали",
#          lambda: import_detail_block(
#              ["Банки (дополнително) - Детали", "Банки (дополнително)", "банки (дополнително)"],
#              "400-2"
#          )),

#         ("SP-6 банки рентно детали",
#          lambda: import_detail_block(
#              ["Банки (рентно) - Детали", "Банки (рентно)", "банки (рентно)"],
#              "400-3"
#          )),

#         ("SP-6 банки останато детали",
#          lambda: import_detail_block(
#              ["Банки (останато) - Детали", "Банки (останато)", "банки (останато)"],
#              "400-99"
#          )),
#     ]

#     results_messages = []
#     total_ok = True

#     for label, fn in IMPORT_BLOCKS:
#         try:
#             ok, msg = fn()
#             results_messages.append(f"{'✅' if ok else '❌'} {label}: {msg}")
#             if not ok:
#                 total_ok = False
#         except Exception as e:
#             total_ok = False
#             results_messages.append(f"❌ {label}: {str(e)}")

#     final_msg = " | ".join(results_messages)
#     print("[SP6_ZO] Done:", final_msg)
#     return total_ok, final_msg
#  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%5
import pandas as pd

def Import_SP6_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP6_ZO] Starting import...")

    SHEET = "STA_SP6_ZO"
    MAP_101_102_103 = {"101": "kol101", "102": "kol102", "103": "kol103"}

    TITLES = [
        "сп-6",
        "продажба по канали",
        "осиг. брокерски друштва",
        "друштва за застапување",
        "банки (основно)",
        "банки (дополнително)",
        "банки (рентно)",
        "банки (останато)",
        "детали",
        "вкупно",
    ]

    # ✅ КЛУЧНО: мора да се вчита од почеток за да ги имаме насловите (ред 6)
    df_raw = None
    for sr in (0, 4, 6, 8, 10):
        tmp = _read_sheet_raw(excel_bytes, SHEET, skiprows=sr)
        if tmp is None or tmp.empty:
            continue
        # пробај дали го гледа насловот за канали
        if _find_row_contains(tmp, "продажба по канали") >= 0:
            df_raw = tmp
            print(f"[SP6_ZO] Using skiprows={sr}")
            break

    if df_raw is None:
        # fallback - земи 0 ако не најде
        df_raw = _read_sheet_raw(excel_bytes, SHEET, skiprows=0)

    if df_raw is None or df_raw.empty:
        print("[SP6_ZO] ❌ Sheet empty")
        return False, f"{SHEET} е празен или не постои"

    # -----------------------------
    # helpers
    # -----------------------------
    def _to_number(x):
        if x is None:
            return 0.0
        s = str(x).strip()
        if s == "" or s.lower() in ("nan", "none"):
            return 0.0
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    def _find_row_contains_fuzzy(df: pd.DataFrame, needle: str):
        n = needle.strip().lower()
        for i in range(len(df)):
            for v in df.iloc[i].tolist():
                if v is None:
                    continue
                if n in str(v).strip().lower():
                    return i
        return -1

    def _detect_101_102_103_columns(tbl: pd.DataFrame):
        # 1) ако веќе се имиња на колони
        direct = {}
        for c in tbl.columns:
            sc = str(c).strip()
            if sc in ("101", "102", "103"):
                direct[sc] = c
        if len(direct) == 3:
            return direct

        # 2) барај во првите редови каде стои редот ['','','101','102','103']
        head = tbl.head(12).astype(str)
        found = {}
        for target in ("101", "102", "103"):
            for col_name in head.columns:
                if head[col_name].str.match(rf"^\s*{target}\s*$", na=False).any():
                    found[target] = col_name
                    break

        if len(found) != 3:
            raise ValueError(f"Не можам да ги детектирам 101/102/103 колоните. Колони: {list(tbl.columns)}")
        return found

    def _clean_rows(df: pd.DataFrame):
        # фрли header/празни редови
        bad = {"", "nan", "none", "0", "100", "101", "102", "103", "ставка бр", "име на посредникот"}
        v = df["vid_stavka"].astype(str).str.strip()
        df = df[df["vid_stavka"].notna()]
        df = df[v.str.strip() != ""]
        df = df[~v.str.lower().isin(bad)]
        return df

    # -----------------------------
    # 1) Продажба по канали (summary)
    # -----------------------------
    def import_sales_by_channels():
        print("[SP6_ZO] Import block: Продажба по канали (scan rows)")

        # најди старт ред (насловот во ред 6)
        start = _find_row_contains(df_raw, "продажба по канали")
        if start < 0:
            start = _find_row_contains_fuzzy(df_raw, "продажба по канали")
        if start < 0:
            return False, "Не е најден блок: Продажба по канали"

        # во твојата табела:
        # col0 = име, col1 = код, col2 = 101, col3 = 102, col4 = 103
        # има 2 header реда после title, па почнуваме од start+3
        rows = []
        i = start + 1

        # помини надолу доволно редови (табелата е мала, 100 е safe)
        for _ in range(120):
            if i >= len(df_raw):
                break

            name = "" if df_raw.shape[1] < 1 else str(df_raw.iloc[i, 0]).strip()
            code = "" if df_raw.shape[1] < 2 else str(df_raw.iloc[i, 1]).strip()
            c101 = "" if df_raw.shape[1] < 3 else df_raw.iloc[i, 2]
            c102 = "" if df_raw.shape[1] < 4 else df_raw.iloc[i, 3]
            c103 = "" if df_raw.shape[1] < 5 else df_raw.iloc[i, 4]

            # прескокни header линии (кај тебе се празни/101/102/103)
            if code.lower() in ("", "nan", "none") and str(c101).strip() in ("101", "Број на склучени договори"):
                i += 1
                continue
            if str(c101).strip() == "101" and str(c102).strip() == "102":
                i += 1
                continue

            # ✅ земаме ред само ако има код што личи на твоите (100,100-1,...,400-99,9999-99,0000)
            code_clean = code.replace(".0", "")
            is_code = bool(re.match(r"^(100(?:-\d+)?|200|300|400-\d+|9999(?:-\d+)?|0000)$", code_clean))

            if is_code:
                rows.append({
                    "client_name": name.replace('"', '').strip(),
                    "vid_stavka": code_clean,
                    "101": _to_number(c101),
                    "102": _to_number(c102),
                    "103": _to_number(c103),
                })

                # ✅ стоп на Вкупно
                if code_clean == "0000":
                    break

            i += 1

        if not rows:
            return False, "Не се прочитани редови од табелата: Продажба по канали"

        df = pd.DataFrame(rows)

        # (опционално) исфрли празни/NaN кодови
        df = df[df["vid_stavka"].astype(str).str.strip().ne("")]
        df = df[df["vid_stavka"].astype(str).str.strip().str.lower().ne("nan")]

        print(f"[SP6_ZO] Channels rows parsed: {len(df)}")  # очекувано 17

        return _insert_rows_stat_izvestai(
            df=df,
            mesec=mesec,
            godina=godina,
            stat_izvestaj_value="SP-6",
            excel_to_db=MAP_101_102_103
        )



    # -----------------------------
    # 2) Детали блокови
    # -----------------------------
    def import_detail_block(title_variants, prefix: str):
        start = -1
        for t in title_variants:
            start = _find_row_contains(df_raw, t)
            if start >= 0:
                break
        if start < 0:
            start = _find_row_contains_fuzzy(df_raw, title_variants[0])
        if start < 0:
            return False, f"Не е најден блок: {title_variants[0]}"

        end = _find_next_title_row(df_raw, start, TITLES)
        tbl = _extract_block_as_table(df_raw, start, end)

        if tbl is None or tbl.empty:
            return True, f"Нема податоци: {title_variants[0]}"

        colmap = _detect_101_102_103_columns(tbl)

        a_ser = tbl.iloc[:, 0].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        b_ser = tbl.iloc[:, 1].astype(str).str.strip()

        df = pd.DataFrame()
        df["vid_stavka"] = a_ser.apply(lambda x: f"{prefix}_{x}" if x.lower() not in ("", "nan", "none") else "")
        df["client_name"] = b_ser

        df["101"] = tbl[colmap["101"]].apply(_to_number)
        df["102"] = tbl[colmap["102"]].apply(_to_number)
        df["103"] = tbl[colmap["103"]].apply(_to_number)

        df = _clean_rows(df)

        cn = df["client_name"].astype(str).str.strip()
        df = df[cn.notna()]
        df = df[cn != ""]
        df = df[cn.str.lower() != "nan"]

        if df.empty:
            return True, f"Нема податоци (по чистење): {title_variants[0]}"

        return _insert_rows_stat_izvestai(
            df=df,
            mesec=mesec,
            godina=godina,
            stat_izvestaj_value="SP-6",
            excel_to_db=MAP_101_102_103
        )

    # -----------------------------
    # Run blocks
    # -----------------------------
    IMPORT_BLOCKS = [
        ("SP-6 канали", import_sales_by_channels),

        ("SP-6 брокери детали",
         lambda: import_detail_block(["Осиг. брокерски друштва - Детали", "Осиг. брокерски друштва"], "200")),

        ("SP-6 застапување детали",
         lambda: import_detail_block(["Друштва за застапување во осиг.  - Детали", "Друштва за застапување во осиг."], "300")),

        ("SP-6 банки основно детали",
         lambda: import_detail_block(["Банки (основно) - Детали", "Банки (основно)"], "400-1")),

        ("SP-6 банки дополнително детали",
         lambda: import_detail_block(["Банки (дополнително) - Детали", "Банки (дополнително)"], "400-2")),

        ("SP-6 банки рентно детали",
         lambda: import_detail_block(["Банки (рентно) - Детали", "Банки (рентно)"], "400-3")),

        ("SP-6 банки останато детали",
         lambda: import_detail_block(["Банки (останато) - Детали", "Банки (останато)"], "400-99")),
    ]

    results_messages = []
    total_ok = True

    for label, fn in IMPORT_BLOCKS:
        try:
            ok, msg = fn()
            results_messages.append(f"{'✅' if ok else '❌'} {label}: {msg}")
            if not ok:
                total_ok = False
        except Exception as e:
            total_ok = False
            results_messages.append(f"❌ {label}: {str(e)}")

    final_msg = " | ".join(results_messages)
    print("[SP6_ZO] Done:", final_msg)
    return total_ok, final_msg
#  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%5




def delete_all_stat_izvestai_for_month(mesec: str, godina: int):
    """
    Deletes ALL rows from appuser.stat_izvestai
    for the given month/year (uses LAST day of month).
    """

    try:
        # convert month name -> number
        MONTHS = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        month = MONTHS.index(mesec) + 1
        year = int(godina)
        day = calendar.monthrange(year, month)[1]  # ✅ last day of month

        print(f"[DB] Deleting stat_izvestai for datum = {day}.{month}.{year}")

        sql = """
            DELETE FROM appuser.stat_izvestai
            WHERE datum = MDY(?, ?, ?)
        """

        results, OK = Connection.OSISinit()
        if not OK:
            print("[DB] ❌ No connection")
            return False, "Нема врска со база"

        results.execute(sql, (month, day, year))

        print("[DB] ✅ Delete completed")
        return True, f"Избришани се сите редови за {day}.{month}.{year}"

    except Exception as e:
        print("[DB] ❌ Delete error:", str(e))
        return False, f"Грешка при бришење: {str(e)}"
    
def Import_SP3_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP3_ZO] Starting import...")

    # Sheet: STA_SP3_ZO
    # Ако заглавјето ти е малку погоре/подолу, смени го skiprows (пример 8/9/10)
    df = _parse_sheet_df(excel_bytes, "STA_SP3_ZO", 8)
    if df.empty:
        print("[STA_SP3_ZO] ❌ No data found")
        return False, "STA_SP3_ZO е празен или не постои"

    # Според сликата:
    # B = vid_stavka (код: 19, 1901, 190101, ...)
    # C = 100, D = 101, E = 102, F = 200, G = 300, H = 301
    MAP_SP3 = {
        2: "kol100",  # C
        3: "kol101",  # D
        4: "kol102",  # E
        5: "kol200",  # F
        6: "kol300",  # G
        7: "kol301",  # H
    }

    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-3",
        excel_to_db=MAP_SP3,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    return ok, msg


def _norm_txt(x: str) -> str:
    # normalize spaces + lowercase + remove weird NBSP
    return " ".join(str(x).replace("\u00a0", " ").split()).lower()

def _find_row_contains(df_raw: pd.DataFrame, text: str) -> int:
    """
    Find first row that contains text (case-insensitive), NOT regex.
    Works even if Excel has extra spaces like 'ж.о .'
    """
    target = _norm_txt(text)

    for i in range(len(df_raw)):
        row_vals = df_raw.iloc[i].tolist()
        row_join = " ".join(_norm_txt(v) for v in row_vals)
        if target in row_join:
            return i

    return -1

def Import_SP5_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP5_ZO] Starting import...")

    # исто како SP1: читај sheet со skiprows
    # ако не ти го фаќа header/редовите, пробај 7 или 9
    df = _parse_sheet_df(excel_bytes, "STA_SP5_ZO", 6)
    # Force D as vid_stavka (01-T, 01-0, 01-1...)
    d_col = df.columns[3]
    df["vid_stavka"] = df[d_col].apply(lambda x: "" if pd.isna(x) else str(x).strip())

    # quick sanity
    print("[SP5] sample vid_stavka:", df["vid_stavka"].head(10).tolist())



    if df.empty:
        print("[SP5_ZO] ❌ No data found")
        return False, "STA_SP5_ZO е празен или не постои"

    # Column indexes (0-based):
    # A=0, B=1, C=2, D=3, ...
    # Во SP-5 кодовите почнуваат од D (100)
    # 0-based indexes:
# A=0, B=1, C=2, D=3, E=4, F=5, G=6, ...

    MAP_SP5 = {
    4: "kol100",    # E -> 100
    5: "kol101",    # F -> 101
    6: "kol101a",   # G -> 101a (само ако постои во DB)
    7: "kol102",    # H -> 102
    8: "kol103",    # I -> 103
    9: "kol104",    # J -> 104
    10: "kol105",   # K -> 105
    11: "kol106",   # L -> 106
    12: "kol107",   # M -> 107
    13: "kol200",   # N -> 108 (ако кај тебе 108 оди во kol200)
}


    ok, msg = _insert_rows_stat_izvestai(
        df=df,
        mesec=mesec,
        godina=godina,
        stat_izvestaj_value="SP-5",
        excel_to_db=MAP_SP5,
        treat_empty_as_null=True,
        cast_decimals="DECIMAL(18,2)"
    )

    print(f"[SP5_ZO] Done: ok={ok} msg={msg}")
    return ok, msg


def Import_SP8_ZO(excel_bytes: bytes, mesec: str, godina: int):
    print("[SP8_ZO] Starting import...")

    SHEET = "STA_SP8_ZO"

    MAP_SP8 = {
        "101": "kol101",
        "102": "kol102",
        "103": "kol103",
        "200": "kol200",
        "300": "kol300",
    }

    df_raw = _read_sheet_raw(excel_bytes, SHEET, skiprows=0)
    if df_raw is None or df_raw.empty:
        return False, f"{SHEET} е празен или не постои"

    # ---------------- helpers ----------------
    def _to_number(x):
        if x is None:
            return 0.0
        s = str(x).strip()
        if s == "" or s.lower() in ("nan", "none"):
            return 0.0
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    def _norm_token(x) -> str:
        """
        Нормализира Excel header токени:
        101.0 -> 101, ' 101 ' -> 101, None -> ''
        """
        if x is None:
            return ""
        s = str(x).strip()
        if s.lower() in ("nan", "none"):
            return ""
        # тргни .0 ако е број како текст
        s = re.sub(r"\.0$", "", s)
        return s

    def _find_header_row_101_102_103_200_300(df: pd.DataFrame) -> int:
        need = {"101", "102", "103", "200", "300"}
        for r in range(len(df)):
            row_vals = {_norm_token(v) for v in df.iloc[r].tolist()}
            if need.issubset(row_vals):
                return r
        return -1

    def _find_header_indices(row_series) -> dict:
        """
        Враќа точни индекси за 101/102/103/200/300 во header редот.
        """
        tokens = [_norm_token(v) for v in row_series.tolist()]
        idx = {}
        for k in ("101", "102", "103", "200", "300"):
            idx[k] = tokens.index(k)
        return idx

    def _find_row_contains_fuzzy(df: pd.DataFrame, needle: str) -> int:
        n = needle.strip().lower()
        for i in range(len(df)):
            for v in df.iloc[i].tolist():
                if v is None:
                    continue
                if n in str(v).strip().lower():
                    return i
        return -1

    # ----------------
    # 1) SUMMARY – Канали (header-scan, без title зависност)
    # ----------------
    def import_channels_sp8():
        print("[SP8_ZO] Import block: Канали (header-scan)")

        header_row = _find_header_row_101_102_103_200_300(df_raw)
        if header_row < 0:
            # debug помош (ќе ти покаже каде има 101/102/103 во фајлот)
            r101 = _find_row_contains_fuzzy(df_raw, "101")
            return False, f"Не е најден header ред со 101/102/103/200/300 (прв 101 е на ред: {r101})"

        idx = _find_header_indices(df_raw.iloc[header_row])

        # Кај каналите: code е лево од 101, name е лево од code
        idx_code = idx["101"] - 1
        idx_name = idx_code - 1

        code_re = re.compile(r"^(100|200|300|400|9999|0000)$")

        rows = []
        for i in range(header_row + 1, min(header_row + 120, len(df_raw))):
            code = _norm_token(df_raw.iloc[i, idx_code])
            name = _norm_token(df_raw.iloc[i, idx_name])

            if not code_re.match(code):
                continue

            rows.append({
                "client_name": name.replace('"', '').strip(),
                "vid_stavka": code,
                "101": _to_number(df_raw.iloc[i, idx["101"]]),
                "102": _to_number(df_raw.iloc[i, idx["102"]]),
                "103": _to_number(df_raw.iloc[i, idx["103"]]),
                "200": _to_number(df_raw.iloc[i, idx["200"]]),
                "300": _to_number(df_raw.iloc[i, idx["300"]]),
            })

            if code == "0000":
                break

        if not rows:
            return False, "SP-8 канали: header најден, ама нема редови со кодови 100/200/300/400/9999/0000"

        df = pd.DataFrame(rows)
        print(f"[SP8_ZO] Channels rows parsed: {len(df)}")  # очекувано 6

        return _insert_rows_stat_izvestai(
            df=df,
            mesec=mesec,
            godina=godina,
            stat_izvestaj_value="SP-8",
            excel_to_db=MAP_SP8
        )

    # ----------------
    # 2) DETAILS – остави како што ти работи (fuzzy title + header scan во рамки)
    # ----------------
    def import_detail_block(title_variants, prefix: str):
        start = -1
        for t in title_variants:
            start = _find_row_contains_fuzzy(df_raw, t)
            if start >= 0:
                break
        if start < 0:
            return True, f"Нема блок: {title_variants[0]}"

        window = df_raw.iloc[start:start+120]
        header_rel = _find_header_row_101_102_103_200_300(window)
        if header_rel < 0:
            return True, f"Нема header (101/102/103/200/300): {title_variants[0]}"
        header_row = start + header_rel

        idx = _find_header_indices(df_raw.iloc[header_row])

        idx_stavka = 0
        idx_name = 1

        rows = []
        for i in range(header_row + 1, min(header_row + 350, len(df_raw))):
            stavka = _norm_token(df_raw.iloc[i, idx_stavka])
            name = _norm_token(df_raw.iloc[i, idx_name])

            if stavka == "" and name == "":
                if rows:
                    break
                continue

            if not stavka.isdigit():
                continue

            rows.append({
                "vid_stavka": f"{prefix}_{stavka}",
                "client_name": name.replace('"', '').strip(),
                "101": _to_number(df_raw.iloc[i, idx["101"]]),
                "102": _to_number(df_raw.iloc[i, idx["102"]]),
                "103": _to_number(df_raw.iloc[i, idx["103"]]),
                "200": _to_number(df_raw.iloc[i, idx["200"]]),
                "300": _to_number(df_raw.iloc[i, idx["300"]]),
            })

        if not rows:
            return True, f"Нема податоци: {title_variants[0]}"

        df = pd.DataFrame(rows)

        return _insert_rows_stat_izvestai(
            df=df,
            mesec=mesec,
            godina=godina,
            stat_izvestaj_value="SP-8",
            excel_to_db=MAP_SP8
        )

    # ---------------- RUN ----------------
    blocks = [
        ("SP-8 канали", import_channels_sp8),
        ("SP-8 брокери", lambda: import_detail_block(["брокерски друштва - Детали", "брокерски друштва"], "200")),
        ("SP-8 застапување", lambda: import_detail_block(["застапување", "друштва за застапување"], "300")),
        ("SP-8 банки", lambda: import_detail_block(["банки - Детали", "банки"], "400")),
    ]

    msgs = []
    ok_all = True

    for label, fn in blocks:
        try:
            ok, msg = fn()
            msgs.append(f"{'✅' if ok else '❌'} {label}: {msg}")
            if not ok:
                ok_all = False
        except Exception as e:
            ok_all = False
            msgs.append(f"❌ {label}: {str(e)}")

    final_msg = " | ".join(msgs)
    print("[SP8_ZO] Done:", final_msg)
    return ok_all, final_msg

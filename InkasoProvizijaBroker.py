import pandas as pd
import os
import routers.Connection as Connection


SMART_MONEY_BROKER_ID = 17374
LIFE_VISION_NAME_PARTS = (
    "LAJF VIZION",
    "LAJF VISION",
    "LIFE VISION",
    "ЛАЈФ ВИЗИОН",
)


def _norm_col(value):
    return str(value or "").strip().lower().replace(" ", "_")


def _find_column(df, candidates):
    normalized = {_norm_col(col): col for col in df.columns}
    for candidate in candidates:
        col = normalized.get(_norm_col(candidate))
        if col is not None:
            return col
    return None


def _is_life_vision_name(value):
    normalized = " ".join(str(value or "").upper().split())
    return any(part in normalized for part in LIFE_VISION_NAME_PARTS)


def _is_life_vision_broker(cursor, broker):
    sql = f"""
        SELECT TRIM(a.desc)
        FROM par_client a
        WHERE a.par_clientid = {int(broker)}
    """
    cursor.execute(sql)
    row = cursor.fetchone()
    return bool(row and _is_life_vision_name(row[0]))


def _insert_calculated_commission_column(df):
    target_col = "Пресметана провизија за рата"
    if target_col in df.columns:
        return df

    prov_life_col = _find_column(df, ["prov_rata", "provizija_rata", "presmetana_provizija_rata"])
    prov_extra_col = _find_column(df, ["prov_rata_nezgoda", "provizija_rata_nezgoda"])
    amount_col = _find_column(df, ["naplata", "naplata_den", "iznos", "iznos_rate"])
    percent_col = _find_column(df, ["provizija_proc", "proc_prov", "presmetana_proc_provizija"])

    if prov_life_col:
        commission = pd.to_numeric(df[prov_life_col], errors="coerce").fillna(0)
        if prov_extra_col:
            commission = commission + pd.to_numeric(df[prov_extra_col], errors="coerce").fillna(0)
    elif amount_col and percent_col:
        amount = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
        percent = pd.to_numeric(df[percent_col], errors="coerce").fillna(0)
        commission = (amount * percent / 100).round(2)
    else:
        commission = ""

    insert_after = _find_column(df, [
        "koja_platena_rata",
        "koja platena rata",
        "која платена рата",
        "koja_rata",
        "rata",
        "број на рата",
    ])

    if insert_after:
        insert_at = list(df.columns).index(insert_after) + 1
        df.insert(insert_at, target_col, commission)
    else:
        df[target_col] = commission

    return df


# -------------------------------------------------------
# CONNECT TO DB
# -------------------------------------------------------
def connect_to_database():
    try:
        cursor, OK = Connection.OSISinit()
    except Exception as e:
        print("❌ OSISinit crashed:", e)
        return False, None

    if not OK or cursor in ("", None):
        print("❌ Cannot connect to database")
        return False, None

    print("🔵 Connected to DB")
    return True, cursor


# -------------------------------------------------------
# MAIN FUNCTION USING YOUR STORED FUNCTION
# -------------------------------------------------------
def inkaso_prov_brokeri(mesec, godina, broker):

    OK, cursor = connect_to_database()
    if not OK:
        return "ERROR", "Cannot connect to DB"

    if _is_life_vision_broker(cursor, broker):
        return "ERROR", "ЛАЈФ ВИЗИОН е исклучен од книжење и генерирање пресметки."

    # ---------------------------------------------------
    # 1) CALL YOUR FUNCTION → IT RUNS THE PROCEDURE
    # ---------------------------------------------------
    sql_func = f"""
        SELECT inkaso_provizija({broker}, {godina})
        FROM systables WHERE tabid = 1;
    """

    print("\n▶️ Executing FUNCTION:")
    print(sql_func)

    cursor.execute(sql_func)
    row = cursor.fetchone()

    if not row:
        return "ERROR", "Function returned no temp table"

    table_name = row[0]
    print(f"🔵 FUNCTION returned TEMP table: {table_name}")


    # ---------------------------------------------------
    # 2) READ THE TEMP TABLE CREATED BY PROCEDURE
    # ---------------------------------------------------
    sql_read = f"SELECT * FROM {table_name};"

    print("\n▶️ Reading final_result:")
    print(sql_read)

    cursor.execute(sql_read)
    rows = cursor.fetchall()

    if not rows:
        print("⚠ final_result is empty")
        return "ERROR", "Empty final_result"

    columns = [desc[0] for desc in cursor.description]

    df = pd.DataFrame(rows, columns=columns)

    if int(broker) != SMART_MONEY_BROKER_ID:
        df = _insert_calculated_commission_column(df)

    print(f"✅ Loaded {len(df)} rows from final_result")


    # ---------------------------------------------------
    # 3) SAVE EXCEL (same folders as always)
    # ---------------------------------------------------
    if os.name == "nt":
        folder = f"C:\\Pregledi\\{mesec}_{godina}"
    else:
        folder = f"/opt/siglife-reporting/Pregledi/{mesec}_{godina}"

    os.makedirs(folder, exist_ok=True)

    out_file = os.path.join(folder, "inkaso_brokeri.xlsx")

    df.to_excel(out_file, index=False)

    print(f"📁 Excel saved at: {out_file}")

    return "OK", out_file

def Directories1(mesec, godina):
    configDIR = "/opt/siglife-reporting/Config"
    inputDIR = f"/opt/siglife-reporting/Pregledi/{mesec}_{godina}"
    return configDIR, inputDIR 

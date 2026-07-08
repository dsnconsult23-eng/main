import pandas as pd
import os
import routers.Connection as Connection


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
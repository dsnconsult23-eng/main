import pandas as pd
import routers.Connection as Connection
import numpy as np
import os
import platform
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
from openpyxl import load_workbook


# -------------------------------
# 🔗 Конекција кон базата
# -------------------------------
def connect_to_database():
    OK, conn = Connection.OSISinit()
    if not OK:
        print("Error - cannot connect to the database")
        return OK, None
    return OK, conn


# -------------------------------
# 🧮 Универзален query executor
# -------------------------------
def execute_sql_query(sql):
    try:
        results, OK = Connection.OSISinit()
        if not OK:
            print("Error connecting to the database")
            return None

        results.execute(sql)
        rows = results.fetchall()

        if rows:
            df = pd.DataFrame(rows)
            return df
        else:
            print("No data returned.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error executing SQL: {e}")
        return pd.DataFrame()


# -------------------------------
# 📂 Директориуми според систем
# -------------------------------
def Directories(m, g):
    """
    Враќа конфигурациски и инпут директориуми во зависност од OS.
    """
    if platform.system() == "Windows":
        sep = "\\"
        configDIR = "c:\\Anakonda\\PyInsurance"
        inputDIR = f"C:\\Pregledi\\{m}_{g}"
    else:
        sep = "/"
        configDIR = "/opt/siglife-reporting/"
        inputDIR = f"/opt/siglife-reporting/Pregledi/Inkaso_agent/{m}_{g}"
    return configDIR, inputDIR, sep


# -------------------------------
# 📊 Генерирање Excel извештај по агент
# -------------------------------
def inkaso_prov_agent(agent_id: int):
    """
    Повик на процедура get_provizija_po_agent и експорт во Excel.
    """
    sql = f"CALL get_provizija_po_agent({agent_id});"
    sql_df = execute_sql_query(sql)

    if sql_df.empty:
        return "ERROR", f"No data returned for agent {agent_id}", None

    folder = f"/opt/siglife-reporting/Provizija/{agent_id}"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"Provizija_Agent_{agent_id}.xlsx")
    headers = [
        "polisa","tip_produkcija","datum_presmetka","provizija","isplateno","ostanato"     ]

    # --- Assign headers manually (SQL returns unnamed columns) ---
    sql_df.columns = headers

    # --- Final DataFrame ---
    df = sql_df[headers]
    df.to_excel(file_path, index=False)

    return "OK", f"Excel generated for agent {agent_id}", file_path



def export_eksel(month: int, year: int):
    """
    Export Excel report for given month and year (all agents) with all headers,
    adding columns one by one from SQL result or empty if missing.
    """
    # --- Keep your SQL exactly as it is ---
    sql = f"""
        SELECT 
            mesec, par_yearid, godina, par_agentid, agent_name, agent_nivo, agent_email, agent_tim,
            startni_poeni, bodovi_licna_prod, bodovi_timska_prod,
            bodovi_period,
            novi_storno_bodovi_lp AS vk_bodovi_licna,
            novi_storno_bodovi_tp AS vk_bodovi_timska_pred_period,
            novi_storno_bodovi AS vk_bodovi_pred_period,
            rolling_vk AS bodovi_do_sledna_pozicija,
            novi_polisi_inkaso_lp AS inkaso_prov_licna,
            novi_polisi_inkaso_tp AS inkaso_pprov_timska,
            novi_inkaso_prov AS vk_inkaso_prov,
            bodovi_sl_pozicija_lp AS prov_licna,
            bodovi_sl_pozicija_tp AS prov_timska,
            bruto_provizija, bruto_provizija_den
        FROM vesna.zbiren_prov_promotori_ex
        WHERE mesec = {month} AND godina = {year}
    """

    sql_df = execute_sql_query(sql)
    print("=== SQL Query Results ===")
    print("Number of rows returned:", len(sql_df))
    print("Columns returned:", sql_df.columns.tolist())
    print("First 5 rows:\n", sql_df.head())
    
    if sql_df.empty:
        return "ERROR", f"No data returned for month {month} and year {year}", None

    # --- Desired headers ---
    headers = [
        "mesec", "par_yearid", "godina", "par_agentid", "agent_name",
        "agent_nivo", "agent_email", "agent_tim", "startni_poeni",
        "bodovi_licna_prod", "bodovi_timska_prod", "bodovi_period",
        "vk_bodovi_licna", "vk_bodovi_timska_pred_period",
        "vk_bodovi_pred_period", "bodovi_do_sledna_pozicija",
        "inkaso_prov_licna", "inkaso_pprov_timska", "vk_inkaso_prov",
        "prov_licna", "prov_timska", "bruto_provizija", "bruto_provizija_den"
    ]

    # --- Assign headers manually (SQL returns unnamed columns) ---
    sql_df.columns = headers

    # --- Final DataFrame ---
    df = sql_df[headers]

    # Create folder if it doesn't exist
    _, folder, _ = Directories(month, year)
    os.makedirs(folder, exist_ok=True)

    # File path
    file_path = os.path.join(folder, f"Eksel_{month}_{year}.xlsx")
    df.to_excel(file_path, index=False)

    # Format Excel: bold headers + auto-width
    wb = load_workbook(file_path)
    ws = wb.active

    for col_num, column_title in enumerate(headers, 1):
        cell = ws[f"{get_column_letter(col_num)}1"]
        cell.font = Font(bold=True)
        max_length = max(
            df[column_title].astype(str).map(len).max(),
            len(column_title)
        ) + 2
        ws.column_dimensions[get_column_letter(col_num)].width = max_length

    wb.save(file_path)

    return "OK", f"Excel generated for {month}/{year}", file_path





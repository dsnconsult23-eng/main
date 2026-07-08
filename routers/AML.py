from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import StreamingResponse, RedirectResponse,JSONResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO
import openpyxl
from db_ifx import informix_cursor
import os
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import uuid
import time
import threading
from io import BytesIO
from openpyxl.cell import WriteOnlyCell
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates


import traceback
from typing import Dict, Any, List, Optional

router = APIRouter()

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

# ---------------- SESSION CHECK ----------------
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)
    return user


# ---------------- DATE TO MDY (Informix) ----------------
def to_mdy(date_str):
    if not date_str:
        return None
    y, m, d = date_str.split("-")
    return f"mdy({int(m)}, {int(d)}, {int(y)})"


# ---------------- PAGE ----------------
@router.get("/AML")
async def aml_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "AML.html",
        {"request": request, "user": user, "active": "AML"}
    )


# ---------------- EXPORT ----------------
@router.post("/AML/export")
async def export_aml(
    request: Request,
    date_from: str = Form(None),
    date_to: str = Form(None),
    important_holder: list[str] = Form([]),
    risk_dog: list[str] = Form([]),      # договорувач ризик (mandatory)
    risk_osig: list[str] = Form([])      # осигуреник ризик (optional)
):

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    # ---------------- BASE SQL ----------------
    sql = """
    SELECT 
        polisa_broj,
        ponuda_broj,
        dogovoruvac_id,
        dogovoruvac,
        CASE WHEN javna_funkcija_dogovoruvac = 0 THEN 'Не' ELSE 'Да' END AS javna_funkcija_dog,
        dogovoruvac_rizik,
        osigurenik_id,
        osigurenik,
        CASE WHEN vrati_client_javna_funkcija(osigurenik_par_client) = 0 THEN 'Не' ELSE 'Да' END AS javna_funkcija_osig,
        CASE WHEN b.f_rizik = 'N' THEN 'Низок'
             WHEN b.f_rizik = 'S' THEN 'Среден'
             WHEN b.f_rizik = 'V' THEN 'Висок'
        END AS osigurenik_rizik,
        TO_CHAR(datum_ponuda, '%d/%m/%Y')datum_ponuda,
        TO_CHAR(skadenca_datum_od, '%d/%m/%Y') skadenca_datum_od,
        TO_CHAR(skadenca_datum_do, '%d/%m/%Y') skadenca_datum_do,
        period_osig,
        osig_suma_zivot,
        premija_zivot,
        valuta,
        par_tip_isplata,
        br_rati,
        tip_produkt,
        polisa_status,
        polisa_sosotojba,
        CASE WHEN nvl(koj_plaka, 'D') = 'D' THEN 'Договорувач' ELSE 'Осигуреник' END AS koj_plaka
    FROM vw_pregled2 a
    JOIN par_client b ON a.osigurenik_par_client = b.par_clientid
    JOIN par_client c ON a.dogovoruvac_par_client = c.par_clientid
    WHERE 1=1 AND polisa_pod_broj = vratipodbrojpolisa(polisa, os_produktid)
    """

    # ---------------- DATE FILTER ----------------
    if date_from:
        sql += f" AND datum_polisa >= {to_mdy(date_from)}"

    if date_to:
        sql += f" AND datum_polisa <= {to_mdy(date_to)}"

    # ---------------- IMPORTANT HOLDER FILTER ----------------
    if important_holder:

        if "DOG" in important_holder:
            sql += " AND javna_funkcija_dogovoruvac = 1"

        if "OSIG" in important_holder:
            sql += " AND vrati_client_javna_funkcija(osigurenik_par_client) = 1"

    # ---------------- DOGOVORUVAC RISK (MANDATORY) ----------------
    if risk_dog:
        values = "', '".join(risk_dog)
        sql += f" AND (c.f_rizik IN ('{values}') or  b.f_rizik IN ('{values}' ))"


    print("AML EXPORT SQL:", sql)       

    # ---------------- FETCH DATA ----------------
    with informix_cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return _export_excel(rows)


# ---------------- EXCEL BUILDER ----------------
def _export_excel(rows):

    columns = [
        "Рбр.",
        "Полиса број",
        "Понуда број",
        "Id на договорувач",
        "Договорувач",
        "Носител на јавна функција",
        "Проценка на ризик",
        "Id на осигуреник",
        "Осигуреник",
        "Носител на јавна функција",
        "Проценка на ризик",
        "Датум понуда",
        "Скаденца од",
        "Скаденца до",
        "Период осиг.",
        "Осиг. сума живот",
        "Премија живот",
        "Валута",
        "Начин на исплата",
        "Бр. Рати",
        "Тип на продукт",
        "Полиса статус",
        "Полиса состојба",
        "Кој плаќа"
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "AML"

    # -------- HEADER FORMAT --------
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle

    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    # Write header
    ws.append(columns)
    for col in range(1, len(columns) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = bold
        cell.alignment = center
        cell.fill = header_fill
        cell.border = thin_border

    # -------- ROWS --------
    for idx, row in enumerate(rows, start=1):
        excel_row = [
            idx, *row
        ]
        ws.append(excel_row)

    # -------- FORMAT ALL CELLS WITH BORDERS --------
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(columns)):
        for cell in r:
            cell.border = thin_border

    # -------- DATE FORMATTING --------
    date_cols = [12, 13, 14]  # Датум понуда, Скаденца од, Скаденца до

    for row in ws.iter_rows(min_row=2):
        for col in date_cols:
            cell = row[col - 1]
            if cell.value:
                try:
                    cell.number_format = "DD/MM/YYYY"
                except:
                    pass

    # -------- NUMBER FORMAT (PREMIJA, SUMA) --------
    money_cols = [16, 17]

    for row in ws.iter_rows(min_row=2):
        for col in money_cols:
            cell = row[col - 1]
            if isinstance(cell.value, (float, int)):
                cell.number_format = '#,##0.00'

    # -------- COLUMN WIDTHS --------
    widths = [
        5, 12, 14, 14, 22, 16, 16,
        14, 22, 16, 16, 14, 14, 14,
        12, 16, 16, 12, 18, 10, 16, 14, 14, 14
    ]

    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    # -------- TOTAL ROW --------
    total_row = ws.max_row + 1
    ws.cell(row=total_row, column=15).value = "Вкупно :"  # label
    ws.cell(row=total_row, column=15).font = bold

    ws.cell(row=total_row, column=17).value = f"=SUM(Q2:Q{ws.max_row - 1})"
    ws.cell(row=total_row, column=17).number_format = '#,##0.00'
    ws.cell(row=total_row, column=17).font = bold

    # Borders for total row
    for col in range(1, len(columns) + 1):
        ws.cell(row=total_row, column=col).border = thin_border

    # -------- RETURN STREAM --------
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=AML_export.xlsx"}
    )

# ---------------- EXPORT NAPLATA ----------------
@router.post("/naplata/export")
async def export_naplata(
    request: Request,
    uplata_from: str = Form(...),   # mandatory
    uplata_to: str = Form(...),     # mandatory
    important_holder_naplata: list[str] = Form([]),
    risk_naplata: list[str] = Form([]),   # <-- FIXED (не е задолжително)
):

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    # ---------------- BASE SQL ----------------
    sql = """
        SELECT 
            polisa,
            faktura,
            client_id,
            client_naziv,
            f_javna_funkcija_plakac,
            rizik_plakac,
            dogovoruvac_id,
            dogov_naziv,
            f_javna_funkcija_dog,
            rizik_dogovoruvac,
            osigurenik_id,
            osigurenik_naziv,
            f_javna_funkcija_osig,
            rizik_osigurenik,
            TO_CHAR(datum, '%d/%m/%Y') AS datum,
            izvod_name,
            broj_izvod,
            opis,
            iznos_p,
            iznos_p_den,
            par_tip_knizi
        FROM REPORT_NAPLATA
        WHERE 1=1

    """

    # ---------------- DATE FILTERS (MANDATORY) ----------------
    sql += f" AND datum >= {to_mdy(uplata_from)}"
    sql += f" AND datum <= {to_mdy(uplata_to)}"

    # ---------------- IMPORTANT HOLDER (OPTIONAL) ----------------
    if important_holder_naplata:
        holder_conditions = []

        if "DOG" in important_holder_naplata:
            holder_conditions.append("f_javna_funkcija_dog = 1")

        if "OSIG" in important_holder_naplata:
            holder_conditions.append("f_javna_funkcija_osig = 1")
        if "PLAKAC" in important_holder_naplata:
            holder_conditions.append("f_javna_funkcija_plakac = 1")

        if holder_conditions:
            sql += " AND (" + " OR ".join(holder_conditions) + ")"

    # ---------------- RISK FILTER (MANDATORY) ----------------
    if risk_naplata:
        risk_list = "', '".join(risk_naplata)
        sql += f"""
            AND (
                rizik_dogovoruvac IN ('{risk_list}')
                OR 
                rizik_osigurenik IN ('{risk_list}') 
                OR 
                rizik_plakac IN ('{risk_list}')
            )
        """

    print("NAPLATA EXPORT SQL:", sql)

    # ---------------- FETCH DATA ----------------
    with informix_cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return _export_excel_naplata(rows)
# ---------------- EXCEL BUILDER NAPLATA ----------------
def _export_excel_naplata(rows):

    # --- MAPPERS ---
    def jf(value):
        return "ДА" if value == 1 else "НЕ" 

    def risk(value):
        if value == "N":
            return "Низок"
        elif value == "S":
            return "Среден"
        elif value == "V":
            return "Висок"
        return ""

    # --- EXCEL HEADER ---
    columns = [
        "Рбр.",
        "Полиса",
        "Фактура",
        "Клиент ID",
        "Клиент",
        "Јавна функција - Плаќач",
        "Ризик - Плаќач",
        "Догов. ID",
        "Догов.",
        "Јавна функција - Дог.",
        "Ризик - Дог.",
        "Осиг. ID",
        "Осиг.",
        "Јавна функција - Осиг.",
        "Ризик - Осиг.",
        "Датум",
        "Извод",
        "Бр. извод",
        "Опис",
        "Наплата",
        "Наплата ден.",
        "Тип книжење"
    ]

    # --- CREATE EXCEL ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Наплата"

    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color="D9D9D9", fill_type="solid")

    # HEADER ROW
    ws.append(columns)
    for col in range(1, len(columns) + 1):
        c = ws.cell(row=1, column=col)
        c.font = bold
        c.alignment = center
        c.fill = header_fill
        c.border = thin_border

    # --- DATA ROWS ---
    for idx, row in enumerate(rows, start=1):

        row = list(row)

        # --- MAP PUBLIC FUNCTION ---
        row[4] = jf(row[4])     # f_javna_funkcija_plakac
        row[8] = jf(row[8])     # f_javna_funkcija_dog
        row[12] = jf(row[12])   # f_javna_funkcija_osig

        # --- MAP RISK ---
        row[5] = risk(row[5])   # rizik_plakac
        row[9] = risk(row[9])   # rizik_dogovoruvac
        row[13] = risk(row[13]) # rizik_osigurenik

        ws.append([idx, *row])

    # --- APPLY BORDER TO ALL DATA ---
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(columns)):
        for cell in r:
            cell.border = thin_border

    # --- MONEY FORMAT ---
    money_cols = [20, 21]  # Наплата, Наплата ден.
    for row in ws.iter_rows(min_row=2):
        for col in money_cols:
            cell = row[col - 1]
            if isinstance(cell.value, (float, int)):
                cell.number_format = '#,##0.00'
    total_row = ws.max_row + 1

    ws.cell(row=total_row, column=18).value = "ВКУПНО:"
    ws.cell(row=total_row, column=18).font = bold

    ws.cell(row=total_row, column=20).value = f"=SUM(T2:T{ws.max_row - 1})"
    ws.cell(row=total_row, column=20).number_format = '#,##0.00'
    ws.cell(row=total_row, column=20).font = bold

    ws.cell(row=total_row, column=21).value = f"=SUM(U2:U{ws.max_row - 1})"
    ws.cell(row=total_row, column=21).number_format = '#,##0.00'
    ws.cell(row=total_row, column=21).font = bold

    for col in range(1, len(columns) + 1):
        ws.cell(row=total_row, column=col).border = thin_border

    # --- COLUMN WIDTHS (AUTO PRETTY) ---
    widths = [
        6, 12, 12, 12, 22, 18, 14, 12, 18, 18,
        14, 12, 18, 18, 14, 12, 12, 12, 40, 14, 14, 60
    ]
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # --- RETURN DOWNLOAD FILE ---
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=naplata_export.xlsx"}
    )




# =========================
# SESSION CHECK
# =========================
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)
    return user


# =======================
# SIMPLE IN-MEM JOB STORE
# =======================
# job_id -> {"status": "running|done|error", "path": str|None, "error": str|None, "created": epoch}
EXPORT_JOBS: Dict[str, Dict[str, Any]] = {}
EXPORT_LOCK = threading.Lock()

EXPORT_DIR = "/tmp/siglife_exports"
os.makedirs(EXPORT_DIR, exist_ok=True)


def _cleanup_old_jobs(ttl_seconds: int = 3600):
    now = time.time()
    with EXPORT_LOCK:
        old = [jid for jid, j in EXPORT_JOBS.items() if now - j.get("created", now) > ttl_seconds]
        for jid in old:
            path = EXPORT_JOBS[jid].get("path")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            EXPORT_JOBS.pop(jid, None)


# =========================================================
# SQL: MAX PRODUCTS (max row_num) - partition by document identifier
# =========================================================
SQL_MAX_PRODUCTS_FIZICKI = """
WITH cte_polisa AS (
    SELECT
        TRIM(vrati_client_id(p.osigurenik_par_client)) AS customer_person_id1_document_identifier,
        polisa_broj_cel
    FROM os_ponuda p, os_produkt pr, os_polisa po
    WHERE p.os_produktid = pr.os_produktid
      AND p.os_ponudaid = po.os_ponudaid
      AND po.polisa_pod_broj = vratipodbrojpolisa(po.polisa_broj, p.os_produktid)
      AND p.par_statusid IN (17,18)
      AND p.osigurenik_par_client IS NOT NULL
      AND NVL(vrati_client_id(p.osigurenik_par_client), '') <> ''
),
cte_polisa_rn AS (
    SELECT
        customer_person_id1_document_identifier,
        ROW_NUMBER() OVER (
            PARTITION BY customer_person_id1_document_identifier
            ORDER BY polisa_broj_cel DESC
        ) AS row_num
    FROM cte_polisa
)
SELECT MAX(row_num) AS max_products
FROM cte_polisa_rn;
"""


# =========================================================
# SQL: PRODUCT ROWS (document_identifier,row_num + product fields)
# =========================================================
SQL_PRODUCT_ROWS_FIZICKI = """
WITH cte_polisa AS (
    SELECT
        p.os_ponudaid,
        TRIM(vrati_client_id(p.osigurenik_par_client)) AS customer_person_id1_document_identifier,

        (SELECT desc_en
         FROM os_tipprodukt
         WHERE os_tipproduktid = pr.os_tipproduktid) AS product_name,

        CASE WHEN po.status_polisa='K' THEN 'ACTIVE' ELSE 'NOACTIVE' END AS product_status,
        case when vrati_valuta_ponuda(p.os_ponudaid)='Евро' then 'EUR' else vrati_valuta_ponuda(p.os_ponudaid) end AS product_currency,
        vrati_br_rati(p.os_produkt_uplataid) AS product_monthly_transaction_count,

        (SELECT korporativen_opis
         FROM par_prod_kanal kk
         WHERE kk.par_prod_kanalid = p.par_prod_kanalid) AS product_onboarding_channel_in_branch_branch_identifier,

        polisa_broj_cel,p.skadenca_datum_od
    FROM os_ponuda p, os_produkt pr, os_polisa po
    WHERE p.os_produktid = pr.os_produktid
      AND p.os_ponudaid = po.os_ponudaid
      AND po.polisa_pod_broj = vratipodbrojpolisa(po.polisa_broj, p.os_produktid)
      AND p.par_statusid IN (17,18)
      AND p.osigurenik_par_client IS NOT NULL
      AND NVL(vrati_client_id(p.osigurenik_par_client), '') <> ''
),
cte_polisa_rn AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_person_id1_document_identifier
            ORDER BY polisa_broj_cel DESC
        ) AS row_num
    FROM cte_polisa
),
cte_avans AS (
    SELECT p.polisa_broj_cel AS polisa_broj, SUM(f.naplata) AS naplata
    FROM cte_polisa_rn p, report_fakturi f
    WHERE p.polisa_broj_cel = f.polisa_broj
      AND f.data_faktura >= TODAY
    GROUP BY 1
),
cte_premija AS (
    SELECT a.polisa_broj_cel, SUM(b.iznos_premija) AS premija
    FROM cte_polisa_rn a, os_ponuda_detail b
    WHERE a.os_ponudaid = b.os_ponudaid
    GROUP BY 1
),
final AS (
    SELECT
        a.customer_person_id1_document_identifier,
        a.row_num,
        a.product_name,
        a.product_status,
        a.product_currency,

        case when product_currency='EUR' then 
        ROUND(c.premija / a.product_monthly_transaction_count)
        else 
        case when vrati_kurs(skadenca_datum_od,'EUR')=0 then 
	    ROUND((c.premija / a.product_monthly_transaction_count)/61.8) else  
        ROUND((c.premija / a.product_monthly_transaction_count)/vrati_kurs(skadenca_datum_od,'EUR')) end 
        end  AS product_monthly_payment,
        case when product_currency='EUR' then 
        NVL(b.naplata, 0)
        else 
        case when vrati_kurs(skadenca_datum_od,'EUR')=0 then 
	    ROUND(NVL(b.naplata, 0)/61.8) else  
        ROUND(NVL(b.naplata, 0)/vrati_kurs(skadenca_datum_od,'EUR')) end 
        end AS product_monthly_received_amount,
        a.product_monthly_transaction_count,
        a.product_onboarding_channel_in_branch_branch_identifier
    FROM cte_polisa_rn a
    LEFT JOIN cte_avans b ON a.polisa_broj_cel = b.polisa_broj
    LEFT JOIN cte_premija c ON a.polisa_broj_cel = c.polisa_broj_cel
)
SELECT *
FROM final
ORDER BY customer_person_id1_document_identifier, row_num;
"""


# =========================================================
# SQL: BASE CUSTOMER (fizicki) - 1 row per document_identifier
# IMPORTANT: first column MUST be customer_person_id1_document_identifier (key)
# =========================================================
SQL_CUSTOMER_BASE_FIZICKI = """
SELECT
    TRIM(c.par_client) AS customer_person_id1_document_identifier,  -- KEY (first)

    '01997a80-9aad-7db6-9896-dc44e61464a5' AS customer_configuration_screening_configuration_identifier,
    'TRUE' AS customer_monitoring_entity_screening_enabled,
    'MK-LIFE-' || NVL(c.par_client, '') AS customer_external_identifier,
    'OSIS' AS customer_acquisition_source,

    DAY(c.datecreated) AS customer_customer_since_day,
    MONTH(c.datecreated) AS customer_customer_since_month,
    YEAR(c.datecreated) AS customer_customer_since_year,

    '' AS customer_person_title,
    CASE WHEN INSTR(c.desc, ' ') > 1 THEN SUBSTRING(c.desc FROM 1 FOR INSTR(c.desc, ' ') - 1) ELSE c.desc END AS customer_person_first_name,
    '' AS customer_person_middle_name,
    '' AS customer_person_last_name,
    '' AS customer_person_fathers_name,
    '' AS customer_person_mothers_name,
    TRIM(c.desc) AS customer_person_full_name,

    -- FIX: use your real gender column (example: c.pol)
    CASE WHEN c.pol = 'M' THEN 'MALE' ELSE 'FEMALE' END AS customer_person_gender,

    '' AS customer_person_suffix,
    '' AS customer_person_source_of_wealth,

    TRIM(c.adresa_ulica) AS customer_person_address1_line1,
    TRIM(c.adresa_broj)  AS customer_person_address1_line2,
    'MK' AS customer_person_address1_country,
    TRIM(c.adresa_mesto) AS customer_person_address1_country_subdivision,
    (SELECT pmu_transakciskaujp FROM par_municipality m WHERE m.par_municipalityid = c.par_municipalityid) AS customer_person_address1_postal_code,
    (SELECT desc_mk FROM par_town t WHERE t.par_townid = c.izvest_par_townid) AS customer_person_address1_town_name,
    'RESIDENTIAL_ADDRESS' AS customer_person_address1_type,

    TRIM(c.adresa_izvest_ulica) AS customer_person_address2_line1,
    TRIM(c.adresa_izvest_mesto) AS customer_person_address2_line2,
    'MK' AS customer_person_address2_country,
    TRIM(c.adresa_izvest_mesto) AS customer_person_address2_country_subdivision,
    '' AS customer_person_address2_postal_code,
    (SELECT desc_mk FROM par_town t2 WHERE t2.par_townid = c.izvest_par_townid) AS customer_person_address2_town_name,
    'RESIDENTIAL_ADDRESS' AS customer_person_address2_type,

    ''   AS customer_person_email1,
    ''        AS customer_person_email2,
    ''        AS customer_person_fax1,
    ''        AS customer_person_fax2,
    '' AS customer_person_phone1,
    ''        AS customer_person_url1,

    (SELECT iso_code FROM par_country co WHERE co.par_countryid = c.par_countryid) AS customer_person_country_of_birth,
    DAY(c.datumraganje)   AS customer_person_birth_day,
    MONTH(c.datumraganje) AS customer_person_birth_month,
    YEAR(c.datumraganje)  AS customer_person_birth_year,
    (SELECT iso_code FROM par_country co2 WHERE co2.par_countryid = c.par_countryid) AS customer_person_nationality1,
    '' AS customer_person_nationality2,

    CAST(NULL AS VARCHAR(10)) AS customer_person_id1_expiry_day,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id1_expiry_month,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id1_expiry_year,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id1_issue_day,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id1_issue_month,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id1_issue_year,

    -- Keep document_identifier field in schema as well (same as key)
    TRIM(c.par_client) AS customer_person_id1_document_identifier,
    (SELECT iso_code FROM par_country co3 WHERE co3.par_countryid = c.par_countryid) AS customer_person_id1_issuing_country,
    'IDENTITY_CARD' AS customer_person_id1_type,

    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_expiry_day,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_expiry_month,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_expiry_year,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_issue_day,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_issue_month,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_issue_year,
    CAST(NULL AS VARCHAR(50)) AS customer_person_id2_document_identifier,
    CAST(NULL AS VARCHAR(10)) AS customer_person_id2_issuing_country,
    CAST(NULL AS VARCHAR(30)) AS customer_person_id2_type,

    '' AS customer_person_profession1,
    '' AS customer_person_profession2,

    'MK'       AS customer_person_residence1_country,
    'RESIDENT' AS customer_person_residence1_status,
    'MK'       AS customer_person_residence2_country,
    'RESIDENT' AS customer_person_residence2_status,

    CAST(NULL AS VARCHAR(30)) AS customer_person_salary_high,
    CAST(NULL AS VARCHAR(30)) AS customer_person_salary_low,
    'MKD' AS customer_person_salary_currency,
    '' AS customer_person_industry,
    CAST(NULL AS VARCHAR(30)) AS customer_person_networth_amount,
    'MKD' AS customer_person_networth_currency,
    '' AS customer_person_income_source

FROM par_client c
WHERE c.client_tip_pf = 'F'
  AND c.par_statusid IN (1, 3)
  AND NVL(c.edb, '') <> ''
  AND NVL(c.par_client, '') <> '';
"""


# ---------------- Headers (base customer without key) ----------------
# We will NOT export the key column separately; we merge by it.
BASE_HEADERS: List[str] = [
    "customer.configuration.screening_configuration_identifier",
    "customer.monitoring.entity_screening.enabled",
    "customer.external_identifier",
    "customer.acquisition_source",
    "customer.customer_since.day",
    "customer.customer_since.month",
    "customer.customer_since.year",
    "customer.person.title",
    "customer.person.first_name",
    "customer.person.middle_name",
    "customer.person.last_name",
    "customer.person.fathers_name",
    "customer.person.mothers_name",
    "customer.person.full_name",
    "customer.person.gender",
    "customer.person.suffix",
    "customer.person.source_of_wealth",
    "customer.person.address[1].address_line1",
    "customer.person.address[1].address_line2",
    "customer.person.address[1].country",
    "customer.person.address[1].country_subdivision",
    "customer.person.address[1].postal_code",
    "customer.person.address[1].town_name",
    "customer.person.address[1].type",
    "customer.person.address[2].address_line1",
    "customer.person.address[2].address_line2",
    "customer.person.address[2].country",
    "customer.person.address[2].country_subdivision",
    "customer.person.address[2].postal_code",
    "customer.person.address[2].town_name",
    "customer.person.address[2].type",
    "customer.person.contact_information.email_address[1]",
    "customer.person.contact_information.email_address[2]",
    "customer.person.contact_information.fax_number[1]",
    "customer.person.contact_information.fax_number[2]",
    "customer.person.contact_information.phone_number[1]",
    "customer.person.contact_information.url[1]",

    "customer.person.country_of_birth",
    "customer.person.date_of_birth.day",
    "customer.person.date_of_birth.month",
    "customer.person.date_of_birth.year",
    "customer.person.nationality[1]",
    "customer.person.nationality[2]",

    "customer.person.personal_identification[1].date_of_expiry.day",
    "customer.person.personal_identification[1].date_of_expiry.month",
    "customer.person.personal_identification[1].date_of_expiry.year",
    "customer.person.personal_identification[1].date_of_issue.day",
    "customer.person.personal_identification[1].date_of_issue.month",
    "customer.person.personal_identification[1].date_of_issue.year",
    "customer.person.personal_identification[1].document_identifier",
    "customer.person.personal_identification[1].issuing_country",
    "customer.person.personal_identification[1].type",

    "customer.person.personal_identification[2].date_of_expiry.day",
    "customer.person.personal_identification[2].date_of_expiry.month",
    "customer.person.personal_identification[2].date_of_expiry.year",
    "customer.person.personal_identification[2].date_of_issue.day",
    "customer.person.personal_identification[2].date_of_issue.month",
    "customer.person.personal_identification[2].date_of_issue.year",
    "customer.person.personal_identification[2].document_identifier",
    "customer.person.personal_identification[2].issuing_country",
    "customer.person.personal_identification[2].type",

    "customer.person.profession[1]",
    "customer.person.profession[2]",

    "customer.person.residential_information[1].country_of_residence",
    "customer.person.residential_information[1].residential_status",
    "customer.person.residential_information[2].country_of_residence",
    "customer.person.residential_information[2].residential_status",

    "customer.person.salary.amount.high",
    "customer.person.salary.amount.low",
    "customer.person.salary.currency",
    "customer.person.industry",
    "customer.person.net_worth.amount",
    "customer.person.net_worth.currency",
    "customer.person.source_of_income",
]

# ---------------------------------------------------------
# Dynamic product headers (full AML schema; we fill only some)
# ---------------------------------------------------------
PRODUCT_FIELD_HEADERS: List[str] = [
    "name",
    "status",
    "bank_account.account_number",
    "bank_account.sort_code",
    "bank_account.iban",
    "bank_account.bban",
    "bank_account.bank.bic",
    "crypto_wallet.wallet_id",
    "crypto_wallet.managing_exchange",
    "currency",
    "monthly_payment_amount",
    "monthly_received_amount",
    "monthly_transaction_count",
    "purpose",
    "onboarding_channel.online.ip_address",
    "onboarding_channel.online.device_identifier",
    "onboarding_channel.online.device_type",
    "onboarding_channel.online.ip_format",
    "onboarding_channel.in_branch.branch_identifier",
]

# mapping from query keys -> product field suffix
PRODUCT_VALUE_MAP = {
    "product_name": "name",
    "product_status": "status",
    "product_currency": "currency",
    "product_monthly_payment": "monthly_payment_amount",
    "product_monthly_received_amount": "monthly_received_amount",
    "product_monthly_transaction_count": "monthly_transaction_count",
    "product_onboarding_channel_in_branch_branch_identifier": "onboarding_channel.in_branch.branch_identifier",
}


def build_headers(max_products: int) -> List[str]:
    headers = BASE_HEADERS.copy()
    for i in range(1, max_products + 1):
        for f in PRODUCT_FIELD_HEADERS:
            headers.append(f"product[{i}].{f}")
    return headers


def _get_max_products() -> int:
    with informix_cursor() as cur:
        cur.execute(SQL_MAX_PRODUCTS_FIZICKI)
        v = cur.fetchone()
        # v[0] can be None
        return int(v[0] or 0)


def _build_xlsx_customer_plus_products(out_path: str, fetch_size: int = 5000):
    """
    Blocking job: builds XLSX with 1 row per customer_person_id1_document_identifier + dynamic product[*] columns.
    Low RAM (write_only) + streaming/pivot for products.
    """
    max_products = _get_max_products()
    if max_products < 1:
        max_products = 1  # keep schema stable even if no products returned

    headers = build_headers(max_products)

    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet(title="AML_Fizicki")

    # Styled header (write_only needs WriteOnlyCell)
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    header_row = []
    for h in headers:
        c = WriteOnlyCell(ws, value=h)
        c.font = bold
        c.alignment = center
        c.fill = fill
        header_row.append(c)
    ws.append(header_row)

    # ---------------------------------------------------------
    # 1) Load BASE customers into dict: doc_id -> base_values (without key)
    # ---------------------------------------------------------
    base_map: Dict[str, List[Any]] = {}
    with informix_cursor() as cur:
        cur.execute(SQL_CUSTOMER_BASE_FIZICKI)
        while True:
            batch = cur.fetchmany(fetch_size)
            if not batch:
                break
            for r in batch:
                if not r or r[0] is None:
                    continue
                doc_id = str(r[0]).strip()
                if not doc_id:
                    continue
                # r[0] is key; rest are base columns
                base_map[doc_id] = list(r)[1:]

    # ---------------------------------------------------------
    # 2) Stream products ordered by doc_id,row_num and pivot into row
    # ---------------------------------------------------------
    product_cols_count = max_products * len(PRODUCT_FIELD_HEADERS)
    base_len = len(BASE_HEADERS)

    def make_out_row(doc_id: str) -> List[Any]:
        base = base_map.get(doc_id)
        if base is None:
            # product exists for someone not in base query
            base = [""] * base_len
        return base + [""] * product_cols_count

    # offset inside output row
    def product_offset(slot: int, field_name: str) -> int:
        j = PRODUCT_FIELD_HEADERS.index(field_name)
        return base_len + (slot - 1) * len(PRODUCT_FIELD_HEADERS) + j

    current_doc: Optional[str] = None
    out_row: Optional[List[Any]] = None

    with informix_cursor() as cur:
        cur.execute(SQL_PRODUCT_ROWS_FIZICKI)

        while True:
            batch = cur.fetchmany(fetch_size)
            if not batch:
                break

            for row in batch:
                # expected order:
                # 0 doc_id, 1 row_num, 2 name, 3 status, 4 currency,
                # 5 monthly_payment, 6 monthly_received, 7 txn_count, 8 branch_identifier
                if not row or row[0] is None:
                    continue

                doc_id = str(row[0]).strip()
                if not doc_id:
                    continue

                if row[1] is None:
                    continue
                try:
                    row_num = int(row[1])
                except Exception:
                    continue

                if current_doc != doc_id:
                    # flush previous
                    if out_row is not None:
                        ws.append(out_row)

                    current_doc = doc_id
                    out_row = make_out_row(doc_id)

                if row_num < 1 or row_num > max_products:
                    continue

                values_by_key = {
                    "product_name": row[2],
                    "product_status": row[3],
                    "product_currency": row[4],
                    "product_monthly_payment": row[5],
                    "product_monthly_received_amount": row[6],
                    "product_monthly_transaction_count": row[7],
                    "product_onboarding_channel_in_branch_branch_identifier": row[8],
                }

                for k, field_suffix in PRODUCT_VALUE_MAP.items():
                    v = values_by_key.get(k)
                    col_idx = product_offset(row_num, field_suffix)
                    out_row[col_idx] = "" if v is None else v

    # flush last
    if out_row is not None:
        ws.append(out_row)

    wb.save(out_path)


def _run_job_fizicki(job_id: str, filename: str):
    try:
        out_path = os.path.join(EXPORT_DIR, f"{job_id}_{filename}")
        _build_xlsx_customer_plus_products(out_path, fetch_size=5000)

        with EXPORT_LOCK:
            EXPORT_JOBS[job_id]["status"] = "done"
            EXPORT_JOBS[job_id]["path"] = out_path

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[AML EXPORT ERROR] job_id={job_id}\n{tb}")

        with EXPORT_LOCK:
            EXPORT_JOBS[job_id]["status"] = "error"
            EXPORT_JOBS[job_id]["error"] = str(e)


# =========================
# 1) START ASYNC EXPORT
# =========================
@router.post("/AML/export-fizicki/start")
async def aml_export_fizicki_start(request: Request, user=Depends(get_current_user)):
    _cleanup_old_jobs()

    job_id = str(uuid.uuid4())

    with EXPORT_LOCK:
        EXPORT_JOBS[job_id] = {"status": "running", "path": None, "error": None, "created": time.time()}

    t = threading.Thread(
        target=_run_job_fizicki,
        args=(job_id, "AML_fizicki.xlsx"),
        daemon=True
    )
    t.start()

    return JSONResponse({
        "job_id": job_id,
        "status_url": f"/siglife-report/AML/export-fizicki/status/{job_id}",
        "download_url": f"/siglife-report/AML/export-fizicki/download/{job_id}"
    })


# =========================
# 2) CHECK STATUS
# =========================
@router.get("/AML/export-fizicki/status/{job_id}")
async def aml_export_fizicki_status(request: Request, job_id: str, user=Depends(get_current_user)):
    with EXPORT_LOCK:
        job = EXPORT_JOBS.get(job_id)

    if not job:
        return JSONResponse({"status": "not_found"}, status_code=404)

    resp = {"status": job["status"]}
    if job["status"] == "error":
        resp["error"] = job.get("error")
    return JSONResponse(resp)


# =========================
# 3) DOWNLOAD WHEN READY
# =========================
@router.get("/AML/export-fizicki/download/{job_id}")
async def aml_export_fizicki_download(request: Request, job_id: str, user=Depends(get_current_user)):
    with EXPORT_LOCK:
        job = EXPORT_JOBS.get(job_id)

    if not job:
        return JSONResponse({"detail": "job not found"}, status_code=404)

    if job["status"] == "running":
        return JSONResponse({"detail": "not ready"}, status_code=202)

    if job["status"] == "error":
        return JSONResponse({"detail": job.get("error", "unknown error")}, status_code=500)

    path = job.get("path")
    if not path or not os.path.exists(path):
        return JSONResponse({"detail": "file missing"}, status_code=404)

    def file_iter():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=AML_fizicki.xlsx"}
    )




# =======================
# SIMPLE IN-MEM JOB STORE
# =======================
# job_id -> {"status": "running|done|error", "path": "...", "error": "...", "created": epoch}
EXPORT_JOBS = {}
EXPORT_LOCK = threading.Lock()

EXPORT_DIR = "/tmp/siglife_exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def _cleanup_old_jobs(ttl_seconds: int = 3600):
    now = time.time()
    with EXPORT_LOCK:
        old = [jid for jid, j in EXPORT_JOBS.items() if now - j.get("created", now) > ttl_seconds]
        for jid in old:
            path = EXPORT_JOBS[jid].get("path")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
            EXPORT_JOBS.pop(jid, None)


# =========================================================
# PRAVNI - HEADERS (base + product[1] + product[2])
# =========================================================
BASE_HEADERS_PRAVNI = [
    "customer.configuration.screening_configuration_identifier",
    "customer.monitoring.entity_screening.enabled",
    "customer.acquisition_source",
    "customer.customer_since.day",
    "customer.customer_since.month",
    "customer.customer_since.year",
    "customer.external_identifier",
    "customer.company.legal_name",
    "customer.company.company_type",
    "customer.company.alias[1]",
    "customer.company.status_summary",
    "customer.company.place_of_registration",
    "customer.company.registration_authority_identification",
    "customer.company.incorporation_date.day",
    "customer.company.incorporation_date.month",
    "customer.company.incorporation_date.year",
    "customer.company.address[1].address_line1",
    "customer.company.address[1].address_line2",
    "customer.company.address[1].country",
    "customer.company.address[1].country_subdivision",
    "customer.company.address[1].postal_code",
    "customer.company.address[1].town_name",
    "customer.company.address[1].type",
    "customer.company.address[2].address_line1",
    "customer.company.address[2].address_line2",
    "customer.company.address[2].country",
    "customer.company.address[2].country_subdivision",
    "customer.company.address[2].postal_code",
    "customer.company.address[2].town_name",
    "customer.company.address[2].type",
    "customer.company.industry",
    "customer.company.source_of_income",
]

PRODUCT_FIELD_HEADERS = [
    "name",
    "status",
    "bank_account.account_number",
    "bank_account.sort_code",
    "bank_account.iban",
    "bank_account.bban",
    "bank_account.bank.bic",
    "crypto_wallet.wallet_id",
    "crypto_wallet.managing_exchange",
    "currency",
    "monthly_payment_amount",
    "monthly_received_amount",
    "monthly_transaction_count",
    "purpose",
    "onboarding_channel.online.ip_address",
    "onboarding_channel.online.device_identifier",
    "onboarding_channel.online.device_type",
    "onboarding_channel.online.ip_format",
    "onboarding_channel.in_branch.branch_identifier",
]

# mapping: query column -> product[*].field
PRODUCT_VALUE_MAP = {
    "product_name": "name",
    "product_status": "status",
    "product_currency": "currency",
    "product_monthly_payment": "monthly_payment_amount",
    "product_monthly_received_amount": "monthly_received_amount",
    "product_monthly_transaction_count": "monthly_transaction_count",
    "product_onboarding_channel_in_branch_branch_identifier": "onboarding_channel.in_branch.branch_identifier",
}

def build_headers_pravni(max_products: int) -> list[str]:
    h = BASE_HEADERS_PRAVNI.copy()
    for i in range(1, max_products + 1):
        for f in PRODUCT_FIELD_HEADERS:
            h.append(f"product[{i}].{f}")
    return h


# =========================================================
# PRAVNI - SQL: BASE (1 row per company) - MUST RETURN EDB AS FIRST COLUMN
# Join key: EDB = customer.company.registration_authority_identification
# =========================================================
SQL_CUSTOMER_BASE_PRAVNI = """
SELECT
    TRIM(c.par_client) AS registration_id,   -- <-- KEY (EDB)

    '01997a80-9aad-7db6-9896-dc44e61464a5' AS customer_configuration_screening_configuration_identifier,
    'TRUE' AS customer_monitoring_entity_screening_enabled,
    'OSIS' AS customer_acquisition_source,

    DAY(c.datecreated) AS customer_customer_since_day,
    MONTH(c.datecreated) AS customer_customer_since_month,
    YEAR(c.datecreated) AS customer_customer_since_year,

    'MK-LIFE-' || NVL(c.edb,'') AS customer_external_identifier,

    TRIM(c.desc) AS customer_company_legal_name,
    '' AS customer_company_company_type,
    '' AS customer_company_alias1,
    '' AS customer_company_status_summary,
    'MK' AS customer_company_place_of_registration,

    TRIM(c.edb) AS customer_company_registration_authority_identification,

    CAST(NULL AS INTEGER) AS customer_company_incorporation_day,
    CAST(NULL AS INTEGER) AS customer_company_incorporation_month,
    CAST(NULL AS INTEGER) AS customer_company_incorporation_year,

    TRIM(c.adresa_ulica) AS customer_company_address1_line1,
    TRIM(c.adresa_broj)  AS customer_company_address1_line2,
    'MK' AS customer_company_address1_country,
    TRIM(c.adresa_mesto) AS customer_company_address1_country_subdivision,
    (SELECT pmu_transakciskaujp FROM par_municipality m WHERE m.par_municipalityid = c.par_municipalityid)
        AS customer_company_address1_postal_code,
    (SELECT desc_mk FROM par_town t WHERE t.par_townid = c.izvest_par_townid)
        AS customer_company_address1_town_name,
    'BUSINESS_ADDRESS' AS customer_company_address1_type,

    TRIM(c.adresa_izvest_ulica) AS customer_company_address2_line1,
    TRIM(c.adresa_izvest_mesto) AS customer_company_address2_line2,
    'MK' AS customer_company_address2_country,
    TRIM(c.adresa_izvest_mesto) AS customer_company_address2_country_subdivision,
    '' AS customer_company_address2_postal_code,
    (SELECT desc_mk FROM par_town t2 WHERE t2.par_townid = c.izvest_par_townid)
        AS customer_company_address2_town_name,
    'BUSINESS_ADDRESS' AS customer_company_address2_type,

    '' AS customer_company_industry,
    '' AS customer_company_source_of_income

FROM par_client c
WHERE c.client_tip_pf = 'P'
  AND c.par_statusid IN (1, 3)
  AND NVL(c.edb,'') <> '';
"""

# =========================================================
# PRAVNI - SQL: PRODUCTS (rows) -> registration_id, row_num, product fields...
# IMPORTANT: registration_id MUST be first column.
# Here we derive EDB from osigurenik_par_client -> vrati_client_id(...) -> par_client.edb
# =========================================================
SQL_PRODUCT_ROWS_PRAVNI = """
WITH cte_polisa AS (
    SELECT
        p.os_ponudaid,

         vrati_client_id(p.dogovoruvac_par_client) AS registration_id,

        (SELECT desc_en FROM os_tipprodukt WHERE os_tipproduktid=pr.os_tipproduktid) AS product_name,
        CASE WHEN po.status_polisa='K' THEN 'ACTIVE' ELSE 'NOACTIVE' END AS product_status,
        case when vrati_valuta_ponuda(p.os_ponudaid)='Евро' then 'EUR' else vrati_valuta_ponuda(p.os_ponudaid) end AS product_currency,
        vrati_br_rati(p.os_produkt_uplataid) AS product_monthly_transaction_count,
        (SELECT korporativen_opis FROM par_prod_kanal kk WHERE kk.par_prod_kanalid=p.par_prod_kanalid)
            AS product_onboarding_channel_in_branch_branch_identifier,
        polisa_broj_cel,nvl(p.br_osig_lica,1) br_osig_lica, p.skadenca_datum_od
    FROM os_ponuda p, os_produkt pr, os_polisa po
    WHERE p.os_produktid=pr.os_produktid
      AND p.os_ponudaid=po.os_ponudaid
      AND po.polisa_pod_broj=vratipodbrojpolisa(po.polisa_broj,p.os_produktid)
      AND p.par_statusid IN (17,18) and vrati_client_pf(p.dogovoruvac_par_client)='P'
),
cte_polisa_clean AS (
    SELECT * FROM cte_polisa WHERE NVL(registration_id,'') <> ''
),
cte_polisa_rn AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY registration_id ORDER BY polisa_broj_cel DESC) AS row_num
    FROM cte_polisa_clean
),
cte_avans AS (
    SELECT p.polisa_broj_cel AS polisa_broj, SUM(f.naplata) AS naplata
    FROM cte_polisa_rn p, report_fakturi f
    WHERE p.polisa_broj_cel=f.polisa_broj
      AND f.data_faktura>=TODAY
    GROUP BY 1
),
cte_premija AS (
    SELECT a.polisa_broj_cel, SUM(b.iznos_premija) AS premija
    FROM cte_polisa_rn a, os_ponuda_detail b
    WHERE a.os_ponudaid=b.os_ponudaid
    GROUP BY 1
),
final AS (
    SELECT
        a.registration_id,
        a.row_num,
        a.product_name,
        a.product_status,
        a.product_currency,
        case when product_currency='EUR' then 
        ROUND((c.premija*br_osig_lica) / a.product_monthly_transaction_count)
        else 
        case when vrati_kurs(skadenca_datum_od,'EUR')=0 then 
	    ROUND(((c.premija*br_osig_lica) / a.product_monthly_transaction_count)/61.8) else  
        ROUND(((c.premija*br_osig_lica) / a.product_monthly_transaction_count)/vrati_kurs(skadenca_datum_od,'EUR')) end 
        end  AS product_monthly_payment,
        case when product_currency='EUR' then 
        NVL(b.naplata, 0)
        else 
        case when vrati_kurs(skadenca_datum_od,'EUR')=0 then 
	    ROUND(NVL(b.naplata, 0)/61.8) else  
        ROUND(NVL(b.naplata, 0)/vrati_kurs(skadenca_datum_od,'EUR')) end end
         AS product_monthly_received_amount,
        a.product_monthly_transaction_count,
        a.product_onboarding_channel_in_branch_branch_identifier
    FROM cte_polisa_rn a
    LEFT JOIN cte_avans b ON a.polisa_broj_cel=b.polisa_broj
    LEFT JOIN cte_premija c ON a.polisa_broj_cel=c.polisa_broj_cel
)
SELECT *
FROM final
WHERE row_num <= 2
ORDER BY registration_id, row_num;
"""

# =========================================================
# If you ever want dynamic max_products, use this.
# For now: fixed 2 products (as you asked earlier).
# =========================================================
SQL_MAX_PRODUCTS_PRAVNI = """
WITH cte_polisa AS (
    SELECT
       vrati_client_id(p.dogovoruvac_par_client) AS registration_id,
        polisa_broj_cel
    FROM os_ponuda p, os_produkt pr, os_polisa po
    WHERE p.os_produktid = pr.os_produktid
      AND p.os_ponudaid = po.os_ponudaid
      AND po.polisa_pod_broj = vratipodbrojpolisa(po.polisa_broj, p.os_produktid)
      AND p.par_statusid IN (17,18) and vrati_client_pf(p.dogovoruvac_par_client)='P'
),
cte_clean AS (
    SELECT * FROM cte_polisa WHERE NVL(registration_id,'') <> ''
),
cte_rn AS (
    SELECT
        registration_id,
        ROW_NUMBER() OVER (PARTITION BY registration_id ORDER BY polisa_broj_cel DESC) AS row_num
    FROM cte_clean
)
SELECT MAX(row_num) AS max_products
FROM cte_rn;
"""

def _get_max_products_pravni(default: int = 2) -> int:
    # FIXED = 2 (as per your screenshot/header), but keep this safe
    try:
        with informix_cursor() as cur:
            cur.execute(SQL_MAX_PRODUCTS_PRAVNI)
            v = cur.fetchone()
            m = int(v[0] or 0)
            return max(1, min(m, 10)) if m > 0 else default
    except:
        return default


# =========================================================
# XLSX BUILDER: 1 row per registration_id (EDB) + product[1..2]
# =========================================================
def _build_xlsx_pravni(out_path: str, fetch_size: int = 5000, max_products: int = 2):
    max_products = int(max_products or 2)
    headers = build_headers_pravni(max_products)

    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet(title="AML_Pravni")

    # Header style
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    header_row = []
    for h in headers:
        cell = WriteOnlyCell(ws, value=h)
        cell.font = bold
        cell.alignment = center
        cell.fill = fill
        header_row.append(cell)
    ws.append(header_row)

    # base columns count
    base_len = len(BASE_HEADERS_PRAVNI)
    product_cols_count = max_products * len(PRODUCT_FIELD_HEADERS)

    def product_offset(slot: int, field_name: str) -> int:
        j = PRODUCT_FIELD_HEADERS.index(field_name)
        return base_len + (slot - 1) * len(PRODUCT_FIELD_HEADERS) + j

    # 1) Load BASE companies into dict: registration_id -> base values (WITHOUT key col)
    # SQL returns: [registration_id] + base fields in same order as BASE_HEADERS_PRAVNI
    base_map = {}
    with informix_cursor() as cur:
        cur.execute(SQL_CUSTOMER_BASE_PRAVNI)
        while True:
            batch = cur.fetchmany(fetch_size)
            if not batch:
                break
            for r in batch:
                reg_id = r[0]
                if not reg_id:
                    continue
                base_map[str(reg_id)] = list(r[1:])  # drop key column

    def make_out_row(reg_id: str):
        base = base_map.get(reg_id)
        if base is None:
            base = [""] * base_len
            # try to at least fill registration id field if possible:
            # find index of "customer.company.registration_authority_identification"
            try:
                idx = BASE_HEADERS_PRAVNI.index("customer.company.registration_authority_identification")
                base[idx] = reg_id
            except:
                pass
        return base + [""] * product_cols_count

    # 2) Stream products sorted by registration_id,row_num
    current_reg = None
    out_row = None

    with informix_cursor() as cur:
        cur.execute(SQL_PRODUCT_ROWS_PRAVNI)

        while True:
            batch = cur.fetchmany(fetch_size)
            if not batch:
                break

            for row in batch:
                # row order:
                # registration_id, row_num, product_name, product_status, product_currency,
                # product_monthly_payment, product_monthly_received_amount,
                # product_monthly_transaction_count, product_onboarding...
                reg_id = row[0]
                if not reg_id:
                    continue
                reg_id = str(reg_id)

                rn = row[1]
                if rn is None:
                    continue
                try:
                    rn = int(rn)
                except:
                    continue

                if current_reg != reg_id:
                    if out_row is not None:
                        ws.append(out_row)
                    current_reg = reg_id
                    out_row = make_out_row(reg_id)

                if rn < 1 or rn > max_products:
                    continue

                values_by_key = {
                    "product_name": row[2],
                    "product_status": row[3],
                    "product_currency": row[4],
                    "product_monthly_payment": row[5],
                    "product_monthly_received_amount": row[6],
                    "product_monthly_transaction_count": row[7],
                    "product_onboarding_channel_in_branch_branch_identifier": row[8],
                }

                for k, header_suffix in PRODUCT_VALUE_MAP.items():
                    v = values_by_key.get(k)
                    col_idx = product_offset(rn, header_suffix)
                    out_row[col_idx] = "" if v is None else v

        if out_row is not None:
            ws.append(out_row)

    wb.save(out_path)


# =========================================================
# BACKGROUND JOB
# =========================================================
def _run_job_pravni(job_id: str, filename: str):
    try:
        out_path = os.path.join(EXPORT_DIR, f"{job_id}_{filename}")

        # fixed 2 products (as your header shows)
        _build_xlsx_pravni(out_path, fetch_size=5000, max_products=2)

        with EXPORT_LOCK:
            EXPORT_JOBS[job_id]["status"] = "done"
            EXPORT_JOBS[job_id]["path"] = out_path

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[AML PRAVNI EXPORT ERROR] job_id={job_id}\n{tb}")

        with EXPORT_LOCK:
            EXPORT_JOBS[job_id]["status"] = "error"
            EXPORT_JOBS[job_id]["error"] = str(e)


# =========================================================
# 1) START ASYNC EXPORT
# =========================================================
@router.post("/AML/export-pravni/start")
async def aml_export_pravni_start(request: Request, user=Depends(get_current_user)):
    _cleanup_old_jobs()

    job_id = str(uuid.uuid4())

    with EXPORT_LOCK:
        EXPORT_JOBS[job_id] = {"status": "running", "path": None, "error": None, "created": time.time()}

    t = threading.Thread(
        target=_run_job_pravni,
        args=(job_id, "AML_pravni.xlsx"),
        daemon=True
    )
    t.start()

    return JSONResponse({
        "job_id": job_id,
        "status_url": f"/siglife-report/AML/export-pravni/status/{job_id}",
        "download_url": f"/siglife-report/AML/export-pravni/download/{job_id}"
    })


# =========================================================
# 2) STATUS
# =========================================================
@router.get("/AML/export-pravni/status/{job_id}")
async def aml_export_pravni_status(request: Request, job_id: str, user=Depends(get_current_user)):
    with EXPORT_LOCK:
        job = EXPORT_JOBS.get(job_id)

    if not job:
        return JSONResponse({"status": "not_found"}, status_code=404)

    resp = {"status": job["status"]}
    if job["status"] == "error":
        resp["error"] = job.get("error")
    return JSONResponse(resp)


# =========================================================
# 3) DOWNLOAD
# =========================================================
@router.get("/AML/export-pravni/download/{job_id}")
async def aml_export_pravni_download(request: Request, job_id: str, user=Depends(get_current_user)):
    with EXPORT_LOCK:
        job = EXPORT_JOBS.get(job_id)

    if not job:
        return JSONResponse({"detail": "job not found"}, status_code=404)

    if job["status"] == "running":
        return JSONResponse({"detail": "not ready"}, status_code=202)

    if job["status"] == "error":
        return JSONResponse({"detail": job.get("error", "unknown error")}, status_code=500)

    path = job.get("path")
    if not path or not os.path.exists(path):
        return JSONResponse({"detail": "file missing"}, status_code=404)

    def file_iter():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=AML_pravni.xlsx"}
    )



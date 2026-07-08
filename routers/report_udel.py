from fastapi import APIRouter, Request, Form, Query, Depends
from fastapi.responses import StreamingResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime, date
import os

from db_ifx import informix_cursor
import re
import unicodedata


router = APIRouter()

# ---------------------------
# Templates
# ---------------------------
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

# ---------------------------
# Session check
# ---------------------------
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)
    return user

# ---------------------------
# Page route
# ---------------------------
@router.get("/ReportUdel")
async def report_udel_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "report_udel.html",
        {
            "request": request,
            "user": user,
            "active": "ReportUdel",
            "selected_date": date.today().isoformat(),  # default date in input
            "dogovoruvac": ""
        }
    )
def safe_ascii_filename(name: str) -> str:
    # Convert to closest ASCII (drops unsupported chars)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # Replace anything unsafe for filenames/headers
    name = re.sub(r'[^A-Za-z0-9._-]+', "_", name).strip("._")
    return name or "report"
# ---------------------------
# Export route (GET + POST)
# ---------------------------
@router.api_route("/ReportUdel/export", methods=["GET", "POST"])
async def export_report_udel(
    request: Request,
    # GET params (optional)
    export_date: str = Query(None),        # YYYY-MM-DD
    dogovoruvac: str = Query(""),
    format: str = Query("excel"),

    # POST form params (optional)
    export_date_form: str = Form(None),    # YYYY-MM-DD
    dogovoruvac_form: str = Form(""),
    format_form: str = Form(None)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    # Prefer POST form values when present
    export_date = export_date_form or export_date
    dogovoruvac = (dogovoruvac_form if dogovoruvac_form is not None else dogovoruvac) or ""
    format = format_form or format

    if not export_date:
        return Response(content="Date is required", status_code=400)

    if (format or "").lower() != "excel":
        return Response(content="Only Excel export is supported", status_code=400)

    # Parse date from HTML input => YYYY-MM-DD
    try:
        d = datetime.strptime(export_date, "%Y-%m-%d").date()
    except ValueError:
        return Response(content="Invalid date format. Use YYYY-MM-DD.", status_code=400)

    cutoff_date = d.strftime("%d.%m.%Y")  # Informix DATE('DD.MM.YYYY')
    dog = dogovoruvac.strip()

    cutoff_day = d.day
    cutoff_month = d.month
    cutoff_year = d.year

    # Escape single quotes for SQL literal safety
    dog_esc = dog.replace("'", "''")

    dog_filter_sql = ""
    if dog_esc:
        dog_filter_sql = f"AND UPPER(dogovoruvac) LIKE '%' || UPPER('{dog_esc}') || '%'"

    sql = f"""
WITH max_d AS (
    SELECT
        b.os_produkt_invest_fondid,
        MAX(a.datum) AS max_datum
    FROM os_udel_upload a
    JOIN os_produkt_invest_fond b
        ON UPPER(TRIM(a.invrest_fond)) = UPPER(b.invest_fond)
    WHERE a.datum <= MDY({cutoff_month}, {cutoff_day}, {cutoff_year})
    GROUP BY
        b.os_produkt_invest_fondid
),
ceni AS (
    SELECT distinct
        md.os_produkt_invest_fondid,
        a.cena_udel_eur,
        a.datum
    FROM max_d md
    JOIN os_produkt_invest_fond b
        ON b.os_produkt_invest_fondid = md.os_produkt_invest_fondid
    JOIN os_udel_upload a
        ON a.datum = md.max_datum
       AND UPPER(TRIM(a.invrest_fond)) = UPPER(b.invest_fond)
),
polisa_max AS (
    SELECT
        a.polisa_broj_cel,
        MAX(a.polisa_pod_broj) AS max_polisa_pod_broj
    FROM os_polisa a
    GROUP BY a.polisa_broj_cel
),
polisa_info AS (
    SELECT
        a.polisa_broj_cel,
        NVL(a.polisa_zamena, a.polisa_broj_cel) AS polisa_zamena,
        a.polisa_pod_broj,
        vrati_client_NAME(b.dogovoruvac_par_client) AS dogovoruvac,
        vrati_status(b.par_statusid) AS ponuda_status,
        CASE WHEN a.status_polisa='K' THEN 'Активна' ELSE 'Неактивна' END AS polisa_status
    FROM os_polisa a
    JOIN polisa_max pm
        ON pm.polisa_broj_cel = a.polisa_broj_cel
       AND pm.max_polisa_pod_broj = a.polisa_pod_broj
    JOIN os_ponuda b
        ON a.os_ponudaid = b.os_ponudaid
),
polisa_udel AS (
    SELECT
        u.polisa_broj,
        pi.polisa_zamena,
        vrati_ponuda_broj(u.os_ponudaid) AS ponuda_broj,
        pi.dogovoruvac,
        pi.ponuda_status,
        pi.polisa_status,
        SUM(CASE WHEN (u.premija_invest < 0 )  THEN u.br_udel  WHEN (u.par_clientid = 80 )  THEN (-1 * u.br_udel )  ELSE u.br_udel END) AS udeli,
        ROUND(SUM(NVL(c.cena_udel_eur, 0) * CASE WHEN (u.premija_invest < 0 )  THEN u.br_udel  WHEN (u.par_clientid = 80 )  THEN (-1 * u.br_udel )  ELSE u.br_udel END), 2) AS Vrednost_na_portfolio
    FROM os_udel_kupi u
    JOIN os_ponuda p
        ON u.os_ponudaid = p.os_ponudaid
    LEFT JOIN ceni c
        ON c.os_produkt_invest_fondid = u.os_produkt_invest_fondid
    LEFT JOIN polisa_info pi
        ON pi.polisa_broj_cel = u.polisa_broj
    GROUP BY
        1,2,3,4,5,6
)
SELECT
    polisa_zamena AS polisa_broj_zamena,
    polisa_broj,
    CASE WHEN polisa_zamena = polisa_broj THEN 1 ELSE 2 END AS dali_zamena,
    ponuda_broj,
    dogovoruvac,
    ponuda_status,
    polisa_status,
    udeli,
    vrednost_na_portfolio
FROM polisa_udel
WHERE 1=1
{dog_filter_sql}
ORDER BY polisa_broj;
"""

    # Execute and fetch
    with informix_cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    # Build Excel
    return _build_excel_report_udel(rows, d, dog)

# ---------------------------
# Excel builder
# ---------------------------
def _build_excel_report_udel(rows, export_date: date, dogovoruvac: str):
    columns = [
        "polisa_broj_zamena",
        "polisa_broj",
        "dali_zamena",
        "ponuda_broj",
        "dogovoruvac",
        "ponuda_status",
        "polisa_status",
        "udeli",
        "vrednost_na_portfolio"
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"ReportUdel_{export_date.strftime('%Y_%m_%d')}"
    ws.append(columns)

    # Write rows
    for r in rows:
        ws.append(list(r))

    # Basic formatting (widths + numeric formats)
    for i, col_name in enumerate(columns, start=1):
        ws.column_dimensions[get_column_letter(i)].width = max(16, len(col_name) + 2)

    # Numeric formats for last columns
    # udeli -> integer/number, vrednost -> 2 decimals
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        # udeli col index = 8
        if row[7].value is not None:
            row[7].number_format = "#,##0.00"
        # vrednost col index = 9
        if row[8].value is not None:
            row[8].number_format = "#,##0.00"

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    dog_part = ""


    dog_part = ""
    if dogovoruvac and dogovoruvac.strip():
        dog_part = "_" + dogovoruvac.strip().replace(" ", "_")[:40]

    filename_raw = f"ReportUdel_{export_date.isoformat()}{dog_part}.xlsx"
    filename = safe_ascii_filename(filename_raw)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

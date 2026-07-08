from fastapi import APIRouter, Request, Form, Query, Depends
from fastapi.responses import StreamingResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO
import openpyxl
from db_ifx import informix_cursor
from datetime import datetime
import os

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
# Page route (NEW)
# ---------------------------
@router.get("/MatematickaRezerva")
async def matematicka_rezerva_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "MatematickaRezerva.html",
        {"request": request, "user": user, "active": "matematicka_rezerva"}
    )

# ---------------------------
# Export route (GET + POST)
# ---------------------------
@router.api_route("/MatematickaRezerva/export", methods=["GET", "POST"])
async def export_data(
    request: Request,
    month: int = Query(None),  # for GET requests
    year: int = Query(None),
    format: str = Query("excel"),  # excel or soap_xml
    month_form: int = Form(None),  # for POST requests
    year_form: int = Form(None),
    format_form: str = Form(None)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    # Use POST form values if available
    if month_form: month = month_form
    if year_form: year = year_form
    if format_form: format = format_form

    if not month or not year:
        return Response(content="Month and year are required", status_code=400)

    # Fetch data from Informix
    with informix_cursor() as cursor:
        cursor.execute("call get_policy_data_report(?, ?)", (month, year))
        rows = cursor.fetchall()

    if format.lower() == "soap_xml":
        # Build SOAP XML
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/">\n'
        xml += '  <soap11env:Body>\n'
        xml += '    <Policies>\n'
        for row in rows:
            xml += "      <Policy>\n"
            for i, value in enumerate(row):
                value_str = "" if value is None else str(value)
                xml += f"        <Field{i}>{value_str}</Field{i}>\n"
            xml += "      </Policy>\n"
        xml += '    </Policies>\n'
        xml += '  </soap11env:Body>\n'
        xml += '</soap11env:Envelope>'
        return Response(content=xml, media_type="application/xml")

    # Default: build Excel
    return _build_excel(rows, month, year)


# ---------------------------
# Excel builder
# ---------------------------
def _build_excel(rows, month, year):
    columns = [
        "x", "gender", "policy", "zamenska_polisa", "issueDate", "beginDate",
        "n", "m", "frequency", "endDate", "installmentFrom", "installmentTo", "SI",
        "annualPremium", "accSI", "accAnnualPremium", "hlthPremium", "tbsPremium",
        "status", "produkt", "OsigSumaT", "OsugSumaTplus1", "status_polisa",
        "produkt_name", "par_statusid", "polisa_pod_broj", "datum_polisa"
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Rezerva_{month:02d}_{year}"
    ws.append(columns)

    # Determine date columns
    date_fields = {"issueDate", "beginDate", "endDate", "installmentFrom", "installmentTo", "datum_polisa"}
    date_col_indexes = [i + 1 for i, col in enumerate(columns) if col in date_fields]

    for row in rows:
        ws.append(list(row))

    # Apply date formatting
    for row_cells in ws.iter_rows(min_row=2):
        for col_idx in date_col_indexes:
            cell = row_cells[col_idx - 1]
            if isinstance(cell.value, str):
                try:
                    parsed_date = datetime.fromisoformat(cell.value[:10])
                    cell.value = parsed_date
                except Exception:
                    continue
            cell.number_format = "DD/MM/YYYY"

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"MatRezerva_{month:02d}_{year}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

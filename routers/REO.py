from fastapi import APIRouter, Request, Form, Query, Depends
from fastapi.responses import StreamingResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO
import openpyxl
from db_ifx import informix_cursor
from datetime import datetime, date, timedelta
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
# Page route
# ---------------------------
@router.get("/REO")
async def reo_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "REO.html",
        {"request": request, "user": user, "active": "REO"}
    )

# ---------------------------
# Helper: last day of month
# ---------------------------
def last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return next_month - timedelta(days=1)

# ---------------------------
# Export route (GET + POST)
# ---------------------------
@router.api_route("/REO/export", methods=["GET", "POST"])
async def export_data(
    request: Request,
    month: int = Query(None),
    year: int = Query(None),
    limit: float = Query(75000),
    format: str = Query("excel"),
    month_form: int = Form(None),
    year_form: int = Form(None),
    limit_form: float = Form(None),
    format_form: str = Form(None)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    # Use POST form values if available
    month = month_form or month
    year = year_form or year
    limit = limit_form or limit
    format = format_form or format

    if not month or not year:
        return Response(content="Month and year are required", status_code=400)

    # Construct last day of month
    export_date = last_day_of_month(year, month)

    # Fetch data from Informix using procedure
    with informix_cursor() as cursor:
        cursor.execute(
            "CALL get_high_value_policies(MDY(?, ?, ?), ?)",
            (export_date.month, export_date.day, export_date.year, limit)
        )
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



    def __call__(self, *args, **kwargs):
        raise NotImplementedError

# ---------------------------
# Excel builder
# ---------------------------
def _build_excel(rows, month, year):
    columns = [
        "No.", "UW Company", "Type of Business", "Credit Life / Term Life", "Benefit Code",
        "Date of Policy Transaction", "Policy No.", "ID Number", "First Name", "Last Name",
        "Birthdate", "Gender", "Sum insured at inception EUR", "Sum insured at inception MKD",
        "Sum insured at expiry EUR", "Sum insured at expiry MKD","Sum insured", "Valid from", "Valid To"
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"REO_{month:02d}_{year}"
    ws.append(columns)

    date_fields = {"Date of Policy Transaction", "Birthdate","Valid from", "Valid To"}
    date_col_indexes = [i + 1 for i, col in enumerate(columns) if col in date_fields]

    for idx, row in enumerate(rows, start=1):
        eur_inception = row[7] or 0
        eur_expiry = row[8] or 0
        mkd_inception = round(eur_inception * 61.5, 0)
        mkd_expiry = round(eur_expiry * 61.5, 0)

        ws.append([
            idx,
            "SIGAL Life AD Skopje",
            "Individual",
            "Credit Life" if idx % 2 == 0 else "Term Life",
            "BD",
            row[5],  # Date of Policy Transaction
            row[4],  # Policy No.
            row[0],  # ID Number
            row[1].split()[0],  # First Name
            " ".join(row[1].split()[1:]),  # Last Name
            row[2],  # Birthdate
            row[3],  # Gender
            eur_inception,
            mkd_inception,
            eur_expiry,
            mkd_expiry,
            row[6], 
            row[10],
            row[11]

        ])

    # Форматирање на датуми
    for row_cells in ws.iter_rows(min_row=2):
        for col_idx in date_col_indexes:
            cell = row_cells[col_idx - 1]
            if isinstance(cell.value, str):
                try:
                    parsed_date = datetime.fromisoformat(cell.value[:10])
                    cell.value = parsed_date
                except:
                    continue
            cell.number_format = "DD/MM/YYYY"

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"REO_{month:02d}_{year}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

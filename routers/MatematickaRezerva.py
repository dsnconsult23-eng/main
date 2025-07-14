from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO
import openpyxl
from db_ifx import informix_cursor

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/MatematickaRezerva", response_class=HTMLResponse)
async def matematicka_rezerva(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("MatematickaRezerva.html", {
        "request": request,
        "user": user,
        "month": "05",
        "year": 2025,
        "message": None,
        "data": []
    })


@router.post("/MatematickaRezerva/export")
async def export_excel(request: Request, month: str = Form(...), year: int = Form(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    stream, filename = _build_excel(int(month), year)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _build_excel(month: int, year: int):
    from openpyxl.styles import numbers

    with informix_cursor() as cursor:
        cursor.execute("call get_policy_data_report(?, ?)", (month, year))
        rows = cursor.fetchall()

    # Column headers as received from your DB or fixed
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

    # Determine column indexes (1-based) of date fields
    date_fields = {"issueDate", "beginDate", "endDate", "installmentFrom", "installmentTo", "datum_polisa"}
    date_col_indexes = [i + 1 for i, col in enumerate(columns) if col in date_fields]

    for row in rows:
        ws.append(list(row))

    # Apply date formatting
    for row in ws.iter_rows(min_row=2):  # skip header row
        for col_idx in date_col_indexes:
            cell = row[col_idx - 1]
            if isinstance(cell.value, (str,)):  # try to parse if it's a string
                try:
                    from datetime import datetime
                    parsed_date = datetime.fromisoformat(cell.value[:10])
                    cell.value = parsed_date
                except Exception:
                    continue
            cell.number_format = "DD/MM/YYYY"

    # Save to stream
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    filename = f"MatRezerva_{month:02d}_{year}.xlsx"
    return stream, filename


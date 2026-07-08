from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.responses import (
    Response, RedirectResponse, JSONResponse, FileResponse
)
from fastapi.templating import Jinja2Templates
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime, date
import os
import re
import unicodedata
import asyncio
import uuid
import time
import json

from db_ifx import informix_cursor

router = APIRouter()

# ---------------------------
# Templates
# ---------------------------
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

EXPORT_DIR = "/opt/siglife-reporting/exports/finansii"
JOB_DIR = "/opt/siglife-reporting/exports/finansii/jobs"

# ---------------------------
# Session check
# ---------------------------
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)
    return user

def safe_ascii_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "report"

# ---------------------------
# Job JSON store on disk
# ---------------------------
def _job_path(job_id: str) -> str:
    os.makedirs(JOB_DIR, exist_ok=True)
    return os.path.join(JOB_DIR, f"{job_id}.json")

def _write_job(job_id: str, payload: dict):
    p = _job_path(job_id)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, p)

def _read_job(job_id: str):
    p = _job_path(job_id)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------
# GET page
# ---------------------------
@router.get("/Finansii")
async def finansii_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "Finansii.html",
        {
            "request": request,
            "user": user,
            "active": "Finansii",
            "selected_date": date.today().isoformat(),
            "message": ""
        }
    )

# ============================================================
# 1) SALDIRANJE (PROCEDURE ONLY)  <-- button "Салдирање"
# Stored as job JSON (disk) to avoid RAM issues
# ============================================================
def _run_saldiranje_procedure(d: date) -> str:
    with informix_cursor() as cursor:
        sql = (
            f"EXECUTE PROCEDURE appuser.sp_saldiranje_dokument("
            f"MDY({d.month},{d.day},{d.year})"
            f");"
        )
        cursor.execute(sql)
        result = cursor.fetchone()  # (status, message)

    status = None
    msg = "OK"
    if result:
        status = int(result[0]) if result[0] is not None else None
        msg = str(result[1]) if len(result) > 1 and result[1] is not None else msg

    # Adjust success codes if needed (commonly 0)
    if status in (0, -1):
        return msg

    raise Exception(f"Грешка при салдирање: {msg} (status={status})")

def _run_job_runner_file(job_id: str, d: date):
    job = _read_job(job_id) or {}
    try:
        _write_job(job_id, {**job, "status": "running"})
        msg = _run_saldiranje_procedure(d)
        job2 = _read_job(job_id) or {}
        _write_job(job_id, {
            **job2,
            "status": "success",
            "message": f"Салдирањето е успешно извршено. ({msg})",
            "finished_at": time.time()
        })
    except Exception as e:
        job2 = _read_job(job_id) or {}
        _write_job(job_id, {
            **job2,
            "status": "error",
            "message": str(e),
            "finished_at": time.time()
        })

@router.post("/Finansii/run-async")
async def finansii_run_async(
    request: Request,
    background_tasks: BackgroundTasks,
    export_date_form: str = Form(...),
    user=Depends(get_current_user)
):
    try:
        d = datetime.strptime(export_date_form, "%Y-%m-%d").date()
    except ValueError:
        return JSONResponse({"ok": False, "error": "Invalid date format. Use YYYY-MM-DD."}, status_code=400)

    job_id = str(uuid.uuid4())
    _write_job(job_id, {
        "ok": True,
        "type": "run",
        "status": "queued",
        "message": "",
        "started_at": time.time(),
        "finished_at": None
    })

    background_tasks.add_task(_run_job_runner_file, job_id, d)
    return JSONResponse({"ok": True, "job_id": job_id})

@router.get("/Finansii/job/{job_id}")
async def finansii_run_job_status(job_id: str, user=Depends(get_current_user)):
    job = _read_job(job_id)
    if not job:
        return JSONResponse({"ok": False, "error": "Job not found"}, status_code=404)
    return JSONResponse(job)

# ============================================================
# 2) EXPORT (EXCEL ONLY - NO PROCEDURE) <-- button "Салдирање – експорт"
# Also stored as job JSON (disk)
# ============================================================
def _fetch_saldiranje_rows(d: date):
    sql = f"""
SELECT
    konto,
    komitent,
    dokument,
    dok_opis,
    NVL(SUM(iznos_d), 0) AS iznos_d,
    NVL(SUM(iznos_p), 0) AS iznos_p,
    NVL(SUM(dev_iznos_d), 0) AS dev_iznos_d,
    NVL(SUM(dev_iznos_p), 0) AS dev_iznos_p
FROM stavka
WHERE godina = {d.year}
  AND konto LIKE '1200%'
  AND dat_nalog <= MDY({d.month},{d.day},{d.year})
GROUP BY 1,2,3,4
HAVING (
    ABS(NVL(SUM(iznos_d),0) - NVL(SUM(iznos_p),0)) < 5
 OR ABS(NVL(SUM(dev_iznos_d),0) - NVL(SUM(dev_iznos_p),0)) < 1
);
"""
    with informix_cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()

def _build_excel_to_server(rows, export_date: date) -> str:
    columns = [
        "konto", "komitent", "dokument", "dok_opis",
        "iznos_d", "iznos_p", "dev_iznos_d", "dev_iznos_p",
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Saldiranje_{export_date.strftime('%Y_%m_%d')}"
    ws.append(columns)

    for r in rows:
        ws.append(list(r))

    for i, col_name in enumerate(columns, start=1):
        ws.column_dimensions[get_column_letter(i)].width = max(16, len(col_name) + 2)

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=5, max_col=8):
        for cell in row:
            if cell.value is not None:
                cell.number_format = "#,##0.00"

    os.makedirs(EXPORT_DIR, exist_ok=True)
    filename = safe_ascii_filename(f"Saldiranje_{export_date.isoformat()}.xlsx")
    file_path = os.path.join(EXPORT_DIR, filename)

    wb.save(file_path)
    return file_path

def _export_job_runner_file(job_id: str, d: date):
    job = _read_job(job_id) or {}
    try:
        _write_job(job_id, {**job, "status": "running"})

        rows = _fetch_saldiranje_rows(d)
        file_path = _build_excel_to_server(rows, d)

        job2 = _read_job(job_id) or {}
        _write_job(job_id, {
            **job2,
            "status": "success",
            "message": "Експортот е успешен. Excel е снимен на сервер.",
            "file_path": file_path,
            "download_url": f"/siglife-report/Finansii/download/{job_id}",
            "finished_at": time.time()
        })
    except Exception as e:
        job2 = _read_job(job_id) or {}
        _write_job(job_id, {
            **job2,
            "status": "error",
            "message": f"Грешка при експорт: {str(e)}",
            "file_path": None,
            "download_url": None,
            "finished_at": time.time()
        })

@router.post("/Finansii/export-async")
async def finansii_export_async(
    request: Request,
    background_tasks: BackgroundTasks,
    export_date_form: str = Form(...),
    user=Depends(get_current_user)
):
    try:
        d = datetime.strptime(export_date_form, "%Y-%m-%d").date()
    except ValueError:
        return JSONResponse({"ok": False, "error": "Invalid date format. Use YYYY-MM-DD."}, status_code=400)

    job_id = str(uuid.uuid4())
    _write_job(job_id, {
        "ok": True,
        "type": "export",
        "status": "queued",
        "message": "",
        "file_path": None,
        "download_url": None,
        "started_at": time.time(),
        "finished_at": None
    })

    background_tasks.add_task(_export_job_runner_file, job_id, d)
    return JSONResponse({"ok": True, "job_id": job_id})

@router.get("/Finansii/export-job/{job_id}")
async def finansii_export_job_status(job_id: str, user=Depends(get_current_user)):
    job = _read_job(job_id)
    if not job:
        return JSONResponse({"ok": False, "error": "Job not found"}, status_code=404)
    return JSONResponse(job)

@router.get("/Finansii/download/{job_id}")
async def finansii_download(job_id: str, user=Depends(get_current_user)):
    job = _read_job(job_id)
    if not job or job.get("status") != "success":
        return Response("File not ready", status_code=404)

    file_path = job.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return Response("File missing on server", status_code=404)

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(file_path),
    )

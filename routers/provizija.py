from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse,Response
from pydantic import BaseModel, Field
from datetime import datetime
from io import BytesIO
import os
import zipfile
import shutil
import tempfile
import uuid
import json
from typing import List, Optional
import math
from db_ifx import informix_cursor

import InkasoProvizijaBroker
from routers import InkasoProvizijaAgent
import routers.Connection as Connection
from SendMailAgent import send_email_with_pdf, send_email_with_pdf_odg_lice
from services.pdf_service import GenerirajPdf
from routers.SendMailBroker import send_mail_broker,generate_excels_broker
from auth.role_utils import has_any_role
from services.ai_excel_insights import generate_commentary, append_commentary_sheet
import asyncio
import pandas as pd
from io import BytesIO
from collections import defaultdict
from pydantic import BaseModel
from fastapi import Request
import io


MONTH_NAMES_MK = {
    1: "Januari",
    2: "Fevruari",
    3: "Mart",
    4: "April",
    5: "Maj",
    6: "Juni",
    7: "Juli",
    8: "Avgust",
    9: "Septemvri",
    10: "Oktomvri",
    11: "Noemvri",
    12: "Dekemvri",
}

LIFE_VISION_NAME_PARTS = (
    "LAJF VIZION",
    "LAJF VISION",
    "LIFE VISION",
    "ЛАЈФ ВИЗИОН",
)


router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))


@router.get("/provizia/multilevel-dashboard")
async def multilevel_dashboard_page(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=303,
            detail="Redirect",
            headers={"Location": "/siglife-report/login"},
        )
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403, detail="Access denied")
    return templates.TemplateResponse(
        "multilevel_dashboard.html",
        {"request": request, "user": user, "active": "provizia"},
    )

# -----------------------------
#   Pydantic Models
# -----------------------------
# -------------------------------
# LONG commission jobs tracking
# -------------------------------
prov_jobs = {}
multilevel_jobs = {}
pdf_jobs = {}


def _pdf_job_status_path(job_id: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"pdf_job_{job_id}.json")


def _write_pdf_job(job_id: str, data: dict):
    current = pdf_jobs.get(job_id, {}).copy()
    current.update(data)
    pdf_jobs[job_id] = current
    with open(_pdf_job_status_path(job_id), "w", encoding="utf-8") as f:
        json.dump(current, f)


def _read_pdf_job(job_id: str) -> Optional[dict]:
    job = pdf_jobs.get(job_id)
    if job:
        return job
    status_path = _pdf_job_status_path(job_id)
    if not os.path.exists(status_path):
        return None
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            job = json.load(f)
        pdf_jobs[job_id] = job
        return job
    except Exception:
        return None


def _multilevel_job_status_path(job_id: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"multilevel_job_{job_id}.json")


def _write_multilevel_job(job_id: str, data: dict):
    current = multilevel_jobs.get(job_id, {}).copy()
    current.update(data)
    multilevel_jobs[job_id] = current
    with open(_multilevel_job_status_path(job_id), "w", encoding="utf-8") as f:
        json.dump(current, f)


def _read_multilevel_job(job_id: str) -> Optional[dict]:
    job = multilevel_jobs.get(job_id)
    if job:
        return job
    status_path = _multilevel_job_status_path(job_id)
    if not os.path.exists(status_path):
        return None
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            job = json.load(f)
        multilevel_jobs[job_id] = job
        return job
    except Exception:
        return None

# -------------------------------
# 🔧 Commission worker (LONG)
# -------------------------------
def run_prov_promotori_job(job_id: str, mesec: str, godina: str, user_id: int):
    try:
        prov_jobs[job_id]["status"] = "running"

        # ✔️ твој Connection wrapper
        results, OK = Connection.OSISinit()

        if not OK:
            raise Exception("Database connection failed")

        print(f"[PROV] Start calculation {mesec}/{godina} user={user_id}")

        sql = "EXECUTE PROCEDURE presmetka_prov_promotori(?, ?, ?)"
        results.execute(sql, (mesec, godina, user_id))

        # ✔️ ако commit не е automatic
        try:
            results.connection.commit()
        except:
            pass

        prov_jobs[job_id]["status"] = "ready"
        prov_jobs[job_id]["message"] = "OK"

        print(f"[PROV ✅] Finished")

    except Exception as e:
        prov_jobs[job_id]["status"] = "error"
        prov_jobs[job_id]["message"] = str(e)

        print(f"[PROV ❌] Error: {e}")

class ProvPromotoriRequest(BaseModel):
    mesec: str
    godina: str

class MailRequest(BaseModel):
    month: int
    year: int
    broker: Optional[str] = None

class InkasoBrokerRequest(BaseModel):
    """
    Request body for Inkaso Broker endpoint.
    Validates month, year and broker_id.
    """
    month: int = Field(..., ge=1, le=12, description="Месец (1–12)")
    year: int = Field(..., ge=2000, description="Година, пример: 2025")
    broker_id: int = Field(..., gt=0, description="ID на брокер (позитивен број)")


# ---------- Helper to fetch from database ----------
def fetch_query(sql):
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        return None, False
    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows, True
    finally:
        cursor.close()
        conn.close()


def _safe_download_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in (" ", "-", "_", ".") else "_" for ch in str(value or ""))
    safe = " ".join(safe.split()).strip(" ._")
    return safe or "broker"


def _get_broker_download_name(broker_id: int) -> str:
    sql = f"""
        SELECT TRIM(a.desc)
        FROM par_client a
        WHERE a.par_clientid = {int(broker_id)}
    """
    rows, ok = fetch_query(sql)
    if ok and rows:
        return str(rows[0][0] or "").strip()
    return str(broker_id)


def _is_life_vision_name(value: str) -> bool:
    normalized = " ".join(str(value or "").upper().split())
    return any(part in normalized for part in LIFE_VISION_NAME_PARTS)


def _is_life_vision_broker(broker_id: int) -> bool:
    return _is_life_vision_name(_get_broker_download_name(broker_id))


def _broker_excel_download_filename(month: int, year: int, broker_id: int) -> str:
    broker_name = _safe_download_filename(_get_broker_download_name(broker_id))
    month_name = MONTH_NAMES_MK.get(int(month), str(month).zfill(2))
    return f"Provizija na brokeri - {broker_name} - {month_name} {year}.xlsx"

# ---------- Static data endpoints ----------
@router.get("/api/months")
async def get_months():
    return [{"value": str(m).zfill(2)} for m in range(1, 13)]

@router.get("/api/years")
async def get_years():
    current_year = datetime.now().year
    return [{"value": y} for y in range(current_year - 5, current_year + 2)]

@router.get("/api/regions")
async def get_regions():
    sql = "SELECT par_regionuid, desc_mk name FROM par_regionu ORDER BY desc_mk"
    rows, ok = fetch_query(sql)
    if not ok or rows is None:
        return JSONResponse(content=[], status_code=500)
    return [{"id": r[0], "name": r[1]} for r in rows]

@router.get("/api/teams")
async def get_teams():
    sql = "SELECT par_teamid, desc_mk name FROM par_team ORDER BY desc_mk"
    rows, ok = fetch_query(sql)
    if not ok or rows is None:
        return JSONResponse(content=[], status_code=500)
    return [{"id": r[0], "name": r[1]} for r in rows]



@router.get("/api/agents")
async def get_agents(
    region_id: Optional[int] = Query(None),
    team_id:   Optional[int] = Query(None)
):
    # Base SELECT
    base_sql = """
        SELECT a.par_agentid, a.desc AS name
        FROM par_agent a
    """

    # --- Build WHERE dynamically ---
    where_clauses = []
    if region_id:
        where_clauses.append(f"""
            a.par_agentid IN (
                SELECT p.par_agentid
                FROM Par_Agent_Pripadnost p
                JOIN par_regionu_filijala f ON p.par_regionu_filijalaid = f.par_regionu_filijalaid
                WHERE TODAY BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,2099))
                  AND f.par_regionuid = {region_id}
            )
        """)
    if team_id:
        where_clauses.append(f"""
              a.par_agentid IN (
                SELECT s.par_agentid
                 FROM Par_Agent_Pripadnost s
                    WHERE today BETWEEN s.datum_od AND nvl(s.datum_do,  mdy(12,31,2099))
                    AND s.par_teamid  = {team_id}
            )
        """)

    if where_clauses:
        base_sql += " WHERE " + " AND ".join(where_clauses)

    base_sql += " ORDER BY a.desc"

    rows, ok = fetch_query(base_sql)
    if not ok or rows is None:
        return JSONResponse(content=[], status_code=500)

    print(f"[Agents] Found {len(rows)} rows for region {region_id} team {team_id}")

    return [{"id": r[0], "name": r[1]} for r in rows]



@router.get("/api/brokers")
async def get_brokers():
    sql = """
        SELECT par_clientid,
               TRIM(a.desc) || '  -  ' || TRIM(c.desc_mk) AS name
        FROM par_client a
        JOIN par_prod_kanal c ON a.par_prod_kanalid = c.par_prod_kanalid
        WHERE par_tip = 'Ind'
    """
    rows, ok = fetch_query(sql)
    if not ok or rows is None:
        return []

    return [
        {
            "broker": str(r[0]),   # value
            "name": r[1]           # текст
        }
        for r in rows
        if not _is_life_vision_name(r[1])
    ]


# ---------- Background PDF generation ----------

BASE_PATH = "/opt/siglife-reporting/Pregledi"

def run_pdf_job(job_id: str, month: str, year: int,
                team_id: Optional[int],
                region_id: Optional[int],
                agent_id: Optional[int]):
    """Heavy PDF generation in the background."""
    try:
        _write_pdf_job(job_id, {"status": "running", "message": "Генерирањето е во тек..."})
        ok, rez = GenerirajPdf(
            mesec=month,
            godina=year,
            par_teamid=team_id,
            par_regionuid=region_id,
            par_agentid=agent_id,
            result_label=None
        )
        if ok:
            _write_pdf_job(job_id, {"status": "ready", "message": f"Генерирањето заврши. {rez or ''}".strip()})
        else:
            print(f"PDF generation failed: {rez}")
            _write_pdf_job(job_id, {"status": "error", "message": str(rez) or "Генерирањето не успеа."})
    except Exception as e:
        print(f"PDF generation exception: {e}")
        _write_pdf_job(job_id, {"status": "error", "message": str(e)})

@router.post("/api/generate_pdf")
async def generate_pdf(payload: dict, background_tasks: BackgroundTasks):
    """
    Start PDF generation in the background.
    * month and year are mandatory
    * target folder is deleted and recreated before generation
    """
    month = payload.get("month")
    year = payload.get("year")

    if not month or not year:
        raise HTTPException(status_code=400,
                            detail="Потребно е да се внесат и месец и година.")
    try:
        year = int(year)
    except ValueError:
        raise HTTPException(status_code=400,
                            detail="Годината мора да биде број.")

    target_folder = os.path.join(BASE_PATH, f"{month}_{year}")

    # ---- Remove old folder ----
    if os.path.exists(target_folder):
        try:
            shutil.rmtree(target_folder)
            print(f"Deleted folder: {target_folder}")
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Не може да се избрише {target_folder}: {e}")

    # ---- Recreate folder ----
    try:
        os.makedirs(target_folder)
        print(f"Created folder: {target_folder}")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Не може да се креира {target_folder}: {e}")

    # ---- Queue background job ----
    job_id = uuid.uuid4().hex
    _write_pdf_job(job_id, {"status": "running", "message": "Генерирањето започна во позадина..."})
    background_tasks.add_task(run_pdf_job,
                              job_id,
                              month, year,
                              payload.get("team_id"),
                              payload.get("region_id"),
                              payload.get("agent_id"))

    return {
        "success": True,
        "job_id": job_id,
        "message": (
            f"Папката {target_folder} е избришана и креирана одново. "
            f"Генерирањето на PDF за {month}/{year} започна во позадина."
        ),
    }


@router.get("/api/generate_pdf/status/{job_id}")
async def generate_pdf_status(job_id: str):
    job = _read_pdf_job(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Job not found"})
    return job

# ---------- Download ZIP of all PDFs ----------
@router.get("/download_all_pdfs/")
def download_all_pdfs(month: str = Query(...), year: int = Query(...)):
    folder_path = f"/opt/siglife-reporting/Pregledi/{month}_{year}"
    if not os.path.exists(folder_path):
        return {"success": False, "message": "Папката не постои"}

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for file in os.listdir(folder_path):
            if file.lower().endswith(".pdf"):
                zipf.write(os.path.join(folder_path, file), arcname=file)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=Provizii_{month}_{year}.zip"}
    )

# ---------- Mail endpoints ----------
@router.post("/api/mail_all")
async def mail_all(
    payload: dict,
    background_tasks: BackgroundTasks
):
    """
    Generate and e-mail a PDF to each matching agent.
    month and year are mandatory.
    Optional filters: team_id, region_id, agent_id.
    """
    month = payload.get("month")
    year  = payload.get("year")
    if not month or not year:
        raise HTTPException(status_code=400,
                            detail="Потребно е да се внесат месец и година.")

    # queue the heavy work
    background_tasks.add_task(
        send_email_with_pdf,
        month,
        int(year),
        payload.get("team_id"),
        payload.get("region_id"),
        payload.get("agent_id")
    )

    return {"success": True,
            "message": f"Испраќањето на индивидуални мејлови за {month}/{year} започна во позадина."}


@router.post("/api/mail_resp")
async def mail_resp(
    payload: dict,
    background_tasks: BackgroundTasks
):
    """
    Generate PDFs for all matching agents and send **one** e-mail
    to the responsible person with every PDF attached.
    """
    month = payload.get("month")
    year  = payload.get("year")
    if not month or not year:
        raise HTTPException(status_code=400,
                            detail="Потребно е да се внесат месец и година.")

    background_tasks.add_task(
        send_email_with_pdf_odg_lice,
        month,
        int(year),
        payload.get("team_id"),
        payload.get("region_id"),
        payload.get("agent_id")
    )

    return {"success": True,
            "message": f"Испраќањето на еден мејл со сите прилози за {month}/{year} започна во позадина."}

# ---------- Broker Inkaso ----------
# -----------------------------
#   Inkaso Broker Endpoint
# -----------------------------
import logging
logger = logging.getLogger(__name__)
@router.post("/api/inkaso_brokeri")
async def inkaso_brokeri_download(payload: InkasoBrokerRequest):
    try:
        logger.info(f"Request received: {payload}")

        if _is_life_vision_broker(payload.broker_id):
            raise HTTPException(
                status_code=400,
                detail="ЛАЈФ ВИЗИОН е исклучен од книжење, генерирање пресметки и испраќање маил."
            )

        # Run inkaso calculation
        status, msg = InkasoProvizijaBroker.inkaso_prov_brokeri(
            payload.month,
            payload.year,
            payload.broker_id
        )

        if status != "OK":
            logger.error(f"Error from inkaso_prov_brokeri: {msg}")
            raise HTTPException(status_code=500, detail=f"Processing error: {msg}")

        # Resolve directory
        ok_dir, inputDIR = InkasoProvizijaBroker.Directories1(payload.month, payload.year)

        if not ok_dir or not inputDIR:
            logger.error("Directory resolution failed.")
            raise HTTPException(status_code=500, detail="Directory resolution failed.")

        # Excel output file path
        output_file = os.path.join(inputDIR, "inkaso_brokeri.xlsx")

        if not os.path.exists(output_file):
            logger.error(f"Excel file not found at path: {output_file}")
            raise HTTPException(status_code=404, detail="Excel file not found")

        logger.info(f"Returning Excel file: {output_file}")

        return FileResponse(
            path=output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=_broker_excel_download_filename(payload.month, payload.year, payload.broker_id)
        )

    except HTTPException:
        raise  # Re-throw HTTP exceptions as they are

    except Exception as e:
        logger.exception("Unexpected error in inkaso_brokeri_download")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ---------- Inkaso Agent Endpoint ----------
class InkasoAgentRequest(BaseModel):
    agent_id: int = Field(..., gt=0, description="ID на агент (позитивен број)")

# Route



# --- Track job status in memory ---
inkaso_status = {}  # { agent_id: "pending" | "ready" | "error" }

class InkasoAgentRequest(BaseModel):
    agent_id: int = Field(..., gt=0, description="ID на агент (позитивен број)")

# -------------------------------
# 🔧 Background worker
# -------------------------------
def run_inkaso_job(agent_id: int):
    try:
        inkaso_status[agent_id] = "pending"
        status, msg, file_path = InkasoProvizijaAgent.inkaso_prov_agent(agent_id)

        if status == "OK" and os.path.exists(file_path):
            inkaso_status[agent_id] = "ready"
            print(f"[INKASO ✅] File ready: {file_path}")
        else:
            inkaso_status[agent_id] = "error"
            print(f"[INKASO ❌] Error: {msg}")

    except Exception as e:
        inkaso_status[agent_id] = "error"
        print(f"[INKASO EXCEPTION] {e}")

# -------------------------------
# 🚀 Start background export
# -------------------------------
@router.post("/api/inkaso_agent")
async def inkaso_agent(payload: InkasoAgentRequest, background_tasks: BackgroundTasks):
    """
    Започнува позадинско генерирање на Excel за даден агент.
    """
    agent_id = payload.agent_id
    inkaso_status[agent_id] = "pending"

    background_tasks.add_task(run_inkaso_job, agent_id)

    return {
        "success": True,
        "message": f"✅ Генерирањето на Excel за агент {agent_id} започна во позадина.",
    }

# -------------------------------
# 📊 Check job status
# -------------------------------
@router.get("/api/inkaso_status/{agent_id}")
async def inkaso_agent_status(agent_id: int):
    """
    Проверува дали Excel фајлот е готов.
    """
    status = inkaso_status.get(agent_id)
    if not status:
        return {"status": "unknown", "message": "⏳ Нема податок за статусот."}
    return {"status": status}

# -------------------------------
# 📥 Download generated file
# -------------------------------
@router.get("/api/inkaso_download/{agent_id}")
async def inkaso_agent_download(agent_id: int):
    """
    Го симнува Excel фајлот ако е подготвен.
    """
    folder = f"/opt/siglife-reporting/Provizija/{agent_id}"
    file_path = os.path.join(folder, f"Provizija_Agent_{agent_id}.xlsx")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Excel фајлот не е пронајден")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(file_path),
    )

# ---------- Export Eksel Endpoint ----------
# -------------------------------
# Request model for export Excel (month + year only)
# -------------------------------
class ExportEkselRequest(BaseModel):
    month: int = Field(..., ge=1, le=12, description="Месец (1–12)")
    year: int = Field(..., ge=2000, description="Година (пример 2025)")

# -------------------------------
# Endpoint
# -------------------------------
class MultilevelPreglediRequest(BaseModel):
    month: Optional[int] = Field(None, ge=1, le=12, description="Month")
    year: Optional[int] = Field(None, ge=2000, description="Year")
    polisa_broj: Optional[str] = None
    agent_id: Optional[int] = Field(None, gt=0, description="Agent ID")
    region_id: Optional[int] = Field(None, gt=0, description="Region ID")
    team_id: Optional[int] = Field(None, gt=0, description="Team ID")


class CommissionRecordUpdate(BaseModel):
    iznos_provizija: float = Field(..., ge=-999999999.99, le=999999999.99)


class CommissionRecordRef(BaseModel):
    source: str
    record_id: int = Field(..., gt=0)


class CommissionBulkUpdate(BaseModel):
    records: List[CommissionRecordRef] = Field(..., min_length=1, max_length=1000)
    iznos_provizija: float = Field(..., ge=-999999999.99, le=999999999.99)


class CommissionBulkDelete(BaseModel):
    records: List[CommissionRecordRef] = Field(..., min_length=1, max_length=1000)


_COMMISSION_TABLES = {
    "agent": ("lc_provizija_agent_presmetka", "lc_provizija_agent_presmetkaid"),
    "promoter": ("provizija_promotori_presmetka", "provizija_promotori_presmetkaid"),
}


def _require_commission_access(request: Request):
    user = request.session.get("user", {})
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403, detail="Немате пристап за промена на провизија.")


def _commission_table(source: str):
    table = _COMMISSION_TABLES.get(source)
    if not table:
        raise HTTPException(status_code=400, detail="Невалиден извор на провизија.")
    return table


@router.get("/api/commission-records")
async def commission_records(
    request: Request,
    polisa_broj: Optional[str] = Query(None, max_length=50),
    agent_id: Optional[int] = Query(None, gt=0),
    faktura: Optional[str] = Query(None, max_length=50),
    godina: Optional[int] = Query(None, ge=0, le=100),
    rata: Optional[int] = Query(None, ge=0, le=1000),
):
    """Return editable commission rows for the selected policy and/or agent."""
    _require_commission_access(request)
    polisa_broj = (polisa_broj or "").strip()
    faktura = (faktura or "").strip()
    if not polisa_broj and not agent_id and not faktura and godina is None and rata is None:
        raise HTTPException(status_code=422, detail="Внесете барем еден критериум за пребарување.")

    filters = []
    params = []
    if polisa_broj:
        filters.append("TRIM(pol.polisa_broj_cel) LIKE ?")
        params.append(f"{polisa_broj}%")
    if agent_id:
        filters.append("pa.par_agentid = ?")
        params.append(agent_id)
    if faktura:
        filters.append("TRIM(an.os_aneks || '/' || vesna.vrati_godina(an.par_yearid) || '-' || af.rata) LIKE ?")
        params.append(f"{faktura}%")
    if godina is not None:
        filters.append("cp.koja_godina = ?")
        params.append(godina)
    if rata is not None:
        filters.append("cp.rata = ?")
        params.append(rata)
    where_sql = " AND ".join(filters)

    selects = []
    for source, (table, pk) in _COMMISSION_TABLES.items():
        points_table = (
            "lc_provizija_agent_bodovi"
            if source == "agent"
            else "provizija_promotori_bodovi"
        )
        points_extra = (
            f"""NVL((SELECT CASE WHEN NVL(SUM(b.br_bodovi), 0) = 0 THEN 0
                                  ELSE SUM(b.iznos_bod) / SUM(b.br_bodovi) END
                          FROM {points_table} b
                         WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                           AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec), 0) AS osnovica_bod, """
            "CAST(NULL AS DECIMAL(18,4)) AS duplirani_bodovi, "
            "CAST(NULL AS DECIMAL(18,4)) AS storno_bodovi"
            if source == "agent"
            else f"""
                NVL((SELECT MAX(b.bod) FROM {points_table} b
                     WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                       AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec), 0) AS osnovica_bod,
                NVL((SELECT SUM(b.duplirani_bodovi) FROM {points_table} b
                     WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                       AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec), 0) AS duplirani_bodovi,
                NVL((SELECT SUM(b.storno_bodovi) FROM {points_table} b
                     WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                       AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec), 0) AS storno_bodovi
            """
        )
        selects.append(f"""
            SELECT
                '{source}' AS source,
                cp.{pk} AS record_id,
                TRIM(pol.polisa_broj_cel) AS polisa_broj,
                TRIM(an.os_aneks || '/' || vesna.vrati_godina(an.par_yearid) || '-' || af.rata) AS faktura,
                cp.koja_godina AS godina,
                cp.rata,
                cp.dat_naplata,
                cp.naplata AS iznos_naplata,
                cp.iznos_provizija,
                TRIM(vesna.vrati_tip_knizi(af.par_tip_kniziid)) AS tip_knizenje,
                pa.par_agentid AS agent_id,
                TRIM(vesna.vrati_agent_name(pa.par_agentid)) AS agent_name,
                (SELECT COUNT(*) FROM {points_table} b
                 WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                   AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec) AS broj_bodovni_zapisi,
                NVL((SELECT SUM(b.br_bodovi) FROM {points_table} b
                     WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                       AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec), 0) AS br_bodovi,
                NVL((SELECT SUM(b.iznos_bod) FROM {points_table} b
                     WHERE b.os_polisaid = pol.os_polisaid AND b.par_agentid = pa.par_agentid
                       AND b.par_yearid = cp.par_yearid AND b.mesec = cp.mesec), 0) AS iznos_bod,
                {points_extra}
            FROM {table} cp
            JOIN provizija_agent pa ON pa.par_provizija_agentid = cp.provizija_agentid
            JOIN os_aneks_faktura af ON af.os_aneks_fakturaid = cp.os_aneks_fakturaid
            JOIN os_aneks an ON an.os_aneksid = af.os_aneksid
            JOIN os_polisa pol ON pol.os_polisaid = an.os_polisaid
            WHERE {where_sql}
        """)

    # Do not sort the full commission/points result in Informix. The correlated
    # point summaries make that exceed the reverse-proxy timeout for agent rows;
    # the modal sorts the capped result in the browser instead.
    sql = "SELECT FIRST 1000 * FROM (" + " UNION ALL ".join(selects) + ") commission_rows"
    query_params = tuple(params + params)
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise HTTPException(status_code=503, detail="Нема конекција со базата.")
    try:
        cursor.execute(sql, query_params)
        columns = [str(c[0]).lower() for c in cursor.description]
        rows = []
        for db_row in cursor.fetchall():
            row = dict(zip(columns, db_row))
            row["source"] = str(row.get("source") or "").strip()
            row["record_id"] = int(row["record_id"])
            row["iznos_provizija"] = float(row["iznos_provizija"] or 0)
            row["iznos_naplata"] = float(row["iznos_naplata"] or 0)
            for numeric_key in (
                "br_bodovi", "iznos_bod", "osnovica_bod",
                "duplirani_bodovi", "storno_bodovi",
            ):
                if row.get(numeric_key) is not None:
                    row[numeric_key] = float(row[numeric_key])
            rows.append(row)
        rows.sort(key=lambda row: (
            str(row.get("polisa_broj") or ""),
            int(row.get("godina") or 0),
            int(row.get("rata") or 0),
            str(row.get("source") or ""),
            int(row.get("record_id") or 0),
        ))
        return {
            "success": True,
            "rows": rows,
            "count": len(rows),
            "total_commission": round(sum(row["iznos_provizija"] for row in rows), 2),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Грешка при вчитување: {exc}")
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


@router.get("/api/commission-records-export")
async def export_commission_records(
    request: Request,
    polisa_broj: Optional[str] = Query(None, max_length=50),
    agent_id: Optional[int] = Query(None, gt=0),
    faktura: Optional[str] = Query(None, max_length=50),
    godina: Optional[int] = Query(None, ge=0, le=100),
    rata: Optional[int] = Query(None, ge=0, le=1000),
):
    """Export the same commission and point-calculation rows shown in the modal."""
    data = await commission_records(request, polisa_broj, agent_id, faktura, godina, rata)
    rows = data["rows"]
    if not rows:
        raise HTTPException(status_code=404, detail="Нема записи за Excel export.")

    columns = {
        "source": "Извор",
        "record_id": "ID запис",
        "agent_id": "ID агент",
        "agent_name": "Агент",
        "polisa_broj": "Број на полиса",
        "faktura": "Фактура",
        "godina": "Година",
        "rata": "Рата",
        "dat_naplata": "Датум на наплата",
        "iznos_naplata": "Износ на наплата",
        "iznos_provizija": "Износ на провизија",
        "tip_knizenje": "Тип книжење",
        "broj_bodovni_zapisi": "Број бодовни записи",
        "br_bodovi": "Пресметани бодови",
        "iznos_bod": "Износ од бодови",
        "osnovica_bod": "Основица за бод",
        "duplirani_bodovi": "Дуплирани бодови",
        "storno_bodovi": "Сторно бодови",
    }
    frame = pd.DataFrame(rows).reindex(columns=list(columns)).rename(columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Провизија и бодови")
        sheet = writer.sheets["Провизија и бодови"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cells in sheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in cells) + 2, 42)
            sheet.column_dimensions[cells[0].column_letter].width = width
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=promena_provizija_bodovi.xlsx"},
    )


def _unique_commission_refs(records):
    refs = []
    seen = set()
    for record in records:
        record.source = record.source.strip()
        _commission_table(record.source)
        key = (record.source, record.record_id)
        if key not in seen:
            seen.add(key)
            refs.append(record)
    return refs


def _begin_commission_transaction(conn):
    """Disable JDBC autocommit so a bulk operation is atomic."""
    jconn = getattr(conn, "jconn", None)
    if jconn is not None:
        jconn.setAutoCommit(False)


def _safe_commission_rollback(conn):
    """Do not let an Informix 'Not in transaction' error mask the real error."""
    try:
        conn.rollback()
    except Exception:
        pass


@router.put("/api/commission-records-bulk")
async def update_commission_records_bulk(payload: CommissionBulkUpdate, request: Request):
    _require_commission_access(request)
    records = _unique_commission_refs(payload.records)
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise HTTPException(status_code=503, detail="Нема конекција со базата.")
    try:
        _begin_commission_transaction(conn)
        changed = 0
        for record in records:
            table, pk = _commission_table(record.source)
            cursor.execute(
                f"UPDATE {table} SET iznos_provizija = ?, version = NVL(version, 0) + 1 WHERE {pk} = ?",
                (payload.iznos_provizija, record.record_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Еден или повеќе записи не се пронајдени. Ништо не е променето.")
            changed += 1
        conn.commit()
        return {"success": True, "count": changed, "message": f"Успешно се променети {changed} записи."}
    except HTTPException:
        _safe_commission_rollback(conn)
        raise
    except Exception as exc:
        _safe_commission_rollback(conn)
        raise HTTPException(status_code=500, detail=f"Групната промена не успеа: {exc}")
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


@router.post("/api/commission-records-bulk-delete")
async def delete_commission_records_bulk(payload: CommissionBulkDelete, request: Request):
    _require_commission_access(request)
    records = _unique_commission_refs(payload.records)
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise HTTPException(status_code=503, detail="Нема конекција со базата.")
    try:
        _begin_commission_transaction(conn)
        changed = 0
        for record in records:
            table, pk = _commission_table(record.source)
            cursor.execute(f"DELETE FROM {table} WHERE {pk} = ?", (record.record_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Еден или повеќе записи не се пронајдени. Ништо не е избришано.")
            changed += 1
        conn.commit()
        return {"success": True, "count": changed, "message": f"Успешно се избришани {changed} записи."}
    except HTTPException:
        _safe_commission_rollback(conn)
        raise
    except Exception as exc:
        _safe_commission_rollback(conn)
        raise HTTPException(status_code=500, detail=f"Групното бришење не успеа: {exc}")
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


@router.put("/api/commission-records/{source}/{record_id}")
async def update_commission_record(
    source: str, record_id: int, payload: CommissionRecordUpdate, request: Request
):
    _require_commission_access(request)
    table, pk = _commission_table(source)
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise HTTPException(status_code=503, detail="Нема конекција со базата.")
    try:
        cursor.execute(
            f"UPDATE {table} SET iznos_provizija = ?, version = NVL(version, 0) + 1 WHERE {pk} = ?",
            (payload.iznos_provizija, record_id),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Записот не е пронајден.")
        conn.commit()
        return {"success": True, "message": "Провизијата е успешно променета."}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Промената не успеа: {exc}")
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


@router.delete("/api/commission-records/{source}/{record_id}")
async def delete_commission_record(source: str, record_id: int, request: Request):
    _require_commission_access(request)
    table, pk = _commission_table(source)
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise HTTPException(status_code=503, detail="Нема конекција со базата.")
    try:
        cursor.execute(f"DELETE FROM {table} WHERE {pk} = ?", (record_id,))
        if cursor.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Записот не е пронајден.")
        conn.commit()
        return {"success": True, "message": "Записот е успешно избришан."}
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Бришењето не успеа: {exc}")
    finally:
        try:
            cursor.close()
        finally:
            conn.close()


def _sql_text(value: str) -> str:
    return str(value).replace("'", "''").strip()


def _fetch_multilevel_provizija(
    month: Optional[int],
    year: Optional[int],
    polisa_broj: Optional[str] = None,
    agent_id: Optional[int] = None,
    region_id: Optional[int] = None,
    team_id: Optional[int] = None,
    dashboard_only: bool = False,
) -> pd.DataFrame:
    where_clauses = []
    if month is not None:
        m_pad = str(month).zfill(2)
        where_clauses.append(f"mesec IN ('{month}', '{m_pad}')")
    if year is not None:
        where_clauses.append(f"godina = '{year}'")
    if polisa_broj:
        where_clauses.append(f"polisa_broj = '{_sql_text(polisa_broj)}'")
    if agent_id:
        where_clauses.append(f"par_agentid = {agent_id}")
    if region_id:
        ref_year = year if year is not None else datetime.now().year
        ref_month = month if month is not None else datetime.now().month
        where_clauses.append(f"""
            par_agentid IN (
                SELECT p.par_agentid
                FROM par_agent_pripadnost p
                JOIN par_regionu_filijala f ON p.par_regionu_filijalaid = f.par_regionu_filijalaid
                WHERE MDY({ref_month}, 1, {ref_year}) BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,3000))
                  AND f.par_regionuid = {region_id}
            )
        """)
    if team_id:
        ref_year = year if year is not None else datetime.now().year
        ref_month = month if month is not None else datetime.now().month
        where_clauses.append(f"""
            par_agentid IN (
                SELECT p.par_agentid
                FROM par_agent_pripadnost p
                WHERE MDY({ref_month}, 1, {ref_year}) BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,3000))
                  AND p.par_teamid = {team_id}
            )
        """)

    dashboard_columns = """
            agent_name,
            polisa_broj,
            faktura,
            naplata,
            iznos_provizija,
            os_aneks_fakturaid,
            naplata_fak,
            par_agentid,
            nacin_provizija,
            br_bodovi,
            mesec
    """
    detail_columns = """
            agent_name,
            polisa_broj,
            faktura,
            tip_knizi,
            koja_godina,
            br_rati,
            rata,
            naplata,
            proc_prov,
            iznos_provizija,
            os_aneks_fakturaid,
            naplata_fak,
            par_agentid,
            nacin_provizija,
            provizija,
            br_bodovi,
            iznos_bod,
            par_client,
            dat_naplata,
            dogovoruvac_name,
            skadenca_datum_od,
            period_osig,
            skadenca_datum_do,
            premija_zivot,
            premija_nezgoda,
            premija_zdravstveno,
            premija_tbs,
            sap_risk_business,
            mesec,
            par_yearid,
            godina,
            bod,
            agent_nivo,
            agent_tim,
            bod_presmetka
    """
    selected_columns = dashboard_columns if dashboard_only else detail_columns
    sql = f"""
        SELECT
            {selected_columns}
        FROM prov_promotori_tp_ex
    """
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise Exception("Database connection failed")

    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _fetch_report_naplata(
    month: Optional[int],
    year: Optional[int],
    polisa_broj: Optional[str] = None,
    agent_id: Optional[int] = None,
    region_id: Optional[int] = None,
    team_id: Optional[int] = None,
) -> pd.DataFrame:
    if month is not None and year is not None:
        period_end_sql = f"LAST_DAY(MDY({month}, 1, {year}))"
    elif year is not None:
        period_end_sql = f"MDY(12, 31, {year})"
    else:
        period_end_sql = "TODAY"

    where_clauses = [
        "x0.os_polisaid = x2.os_polisaid",
        "x2.os_ponudaid = x3.os_ponudaid",
        "x7.os_aneks_fakturaid = x0.os_aneks_fakturaid",
        "x8.os_aneksid = x7.os_aneksid",
        "x0.datum <= TODAY",
        "NVL(x0.f_rs, 'R') != 'N'",
        "x0.par_tip_dokumentid = 285",
        "x3.broker_par_client IS NULL",
        "x0.iznos_p IS NOT NULL",
        # par_tip_kniziid=286 nikogas ne se smeta kako naplata za presmetka na provizija.
        "x0.par_tip_kniziid != 286",
        # Naplata e validna samo za prvite 4 godini od polisata (za SITE par_tip_kniziid,
        # ne samo 285): godina na fakturata - godina na skadenca_datum_od + 1 <= 4.
        # os_polisa.datum_polisa NE se koristi bidejki edna polisa_broj_cel moze da ima
        # poveke os_polisaid verzii niz vreme (zameni/kapitalizacii) so nepouzdan
        # datum_polisa po verzija — x3.skadenca_datum_od (os_ponuda) e pobaraniot izvor.
        # Godinata na fakturata se zema od x7.data_faktura (os_aneks_faktura).
        "(YEAR(x7.data_faktura) - YEAR(x3.skadenca_datum_od) + 1) <= 4",
    ]
    if month is not None and year is not None:
        where_clauses.append(f"x0.datum >= MDY({month}, 1, {year})")
        where_clauses.append(f"x0.datum <= LAST_DAY(MDY({month}, 1, {year}))")
    elif year is not None:
        where_clauses.append(f"x0.datum >= MDY(1, 1, {year})")
        where_clauses.append(f"x0.datum <= MDY(12, 31, {year})")
    if polisa_broj:
        where_clauses.append(f"TRIM(x2.polisa_broj_cel) = '{_sql_text(polisa_broj)}'")
    if agent_id:
        where_clauses.append(f"x0.par_agent_id = {agent_id}")
    if region_id:
        ref_year = year if year is not None else datetime.now().year
        ref_month = month if month is not None else datetime.now().month
        where_clauses.append(f"""
            x0.par_agent_id IN (
                SELECT p.par_agentid
                FROM par_agent_pripadnost p
                JOIN par_regionu_filijala f ON p.par_regionu_filijalaid = f.par_regionu_filijalaid
                WHERE MDY({ref_month}, 1, {ref_year}) BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,3000))
                  AND f.par_regionuid = {region_id}
            )
        """)
    if team_id:
        ref_year = year if year is not None else datetime.now().year
        ref_month = month if month is not None else datetime.now().month
        where_clauses.append(f"""
            x0.par_agent_id IN (
                SELECT p.par_agentid
                FROM par_agent_pripadnost p
                WHERE MDY({ref_month}, 1, {ref_year}) BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,3000))
                  AND p.par_teamid = {team_id}
            )
        """)

    # vrati_naplata() e "tesok" UDF (isto kako vo kontrola_polisi.py) — mora da se
    # presmeta TOCNO EDNAS po os_aneks_fakturaid, ne po fin_stavkaid red. Zatoa
    # vnatresen subquery prvo agregira (GROUP BY, bez UDF) po fakturaid, a duri
    # nadvoresniot join go presmetuva vrati_naplata()/go zema iznos-ot na fakturata
    # eden pat po VEKE-agregiranata faktura.
    inner_sql = f"""
        SELECT
            x0.os_aneks_fakturaid,
            x0.os_polisaid,
            x2.polisa_broj_cel AS polisa,
            "vesna".vrati_faktura_broj(x0.os_aneks_fakturaid) AS faktura,
            "vesna".vrati_faktura_brojint(x0.os_aneks_fakturaid) AS fakturaint,
            x0.par_agent_id,
            "vesna".vrati_agent_name(x0.par_agent_id) AS agent_naziv,
            x0.par_clientid,
            "vesna".vrati_client_id(x0.par_clientid) AS client_id,
            "vesna".vrati_client_name(x0.par_clientid) AS client_naziv,
            SUM(x0.iznos_d)     AS iznos_d,
            SUM(x0.iznos_d_den) AS iznos_d_den,
            SUM(x0.iznos_p)     AS iznos_p,
            SUM(x0.iznos_p_den) AS iznos_p_den
        FROM "viki".fin_stavka x0,
             "viki".os_polisa x2,
             "viki".os_ponuda x3,
             "viki".os_aneks_faktura x7,
             "viki".os_aneks x8
    """
    inner_sql += " WHERE " + " AND ".join(where_clauses)
    inner_sql += " GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10"

    sql = f"""
        SELECT
            m.os_aneks_fakturaid, m.os_polisaid, m.polisa, m.faktura, m.fakturaint,
            m.par_agent_id, m.agent_naziv, m.par_clientid, m.client_id, m.client_naziv,
            m.iznos_d, m.iznos_d_den, m.iznos_p, m.iznos_p_den,
            f9.iznos AS faktura_iznos,
            NVL(vrati_naplata(m.os_aneks_fakturaid), 0) AS faktura_naplata_vkupno,
            NVL((
                SELECT SUM(NVL(fp.iznos_p, 0))
                FROM "viki".fin_stavka fp
                WHERE fp.os_aneks_fakturaid = m.os_aneks_fakturaid
                  AND fp.par_tip_dokumentid = 285
                  AND fp.iznos_p IS NOT NULL
                  AND fp.datum <= {period_end_sql}
            ), 0) AS faktura_naplata_do_period,
            (SELECT COUNT(*) FROM lc_provizija_agent_bodovi lb
             WHERE lb.os_polisaid=m.os_polisaid) AS lc_bodovi_count,
            NVL((SELECT SUM(ABS(lb.iznos_bod)) FROM lc_provizija_agent_bodovi lb
                 WHERE lb.os_polisaid=m.os_polisaid), 0) AS lc_iznos_bod,
            (SELECT COUNT(*) FROM provizija_promotori_bodovi pb
             WHERE pb.os_polisaid=m.os_polisaid) AS promoter_bodovi_count,
            (SELECT COUNT(*) FROM lc_provizija_agent_presmetka lp
             WHERE lp.os_aneks_fakturaid=m.os_aneks_fakturaid) AS lc_presmetki_count,
            (SELECT COUNT(*) FROM provizija_promotori_presmetka pp
             WHERE pp.os_aneks_fakturaid=m.os_aneks_fakturaid) AS promoter_presmetki_count
            ,NVL((SELECT pa.par_status_aktiven
                  FROM os_polisa px, os_ponuda ox, par_agent pa
                  WHERE px.os_polisaid=m.os_polisaid
                    AND ox.os_ponudaid=px.os_ponudaid
                    AND pa.par_agentid=ox.par_agentid), 'A') AS agent_status
            ,(SELECT ox.par_agentid
              FROM os_polisa px, os_ponuda ox
              WHERE px.os_polisaid=m.os_polisaid
                AND ox.os_ponudaid=px.os_ponudaid) AS prov_agentid
            ,(SELECT vrati_agent_name(ox.par_agentid)
              FROM os_polisa px, os_ponuda ox
              WHERE px.os_polisaid=m.os_polisaid
                AND ox.os_ponudaid=px.os_ponudaid) AS prov_agent_naziv
            ,(SELECT COUNT(*)
              FROM os_polisa px, os_ponuda ox, provizija_agent pva,
                   par_provizijadef pvd, par_provizijatip pvt
              WHERE px.os_polisaid=m.os_polisaid
                AND ox.os_ponudaid=px.os_ponudaid
                AND pva.par_agentid=ox.par_agentid
                AND pvd.par_provizijadefid=pva.par_provizijadefid
                AND pvt.par_provizijatipid=pvd.par_provizijatipid
                AND pvt.tip_provizija='P'
                AND ((ox.datum_ponuda BETWEEN pva.pag_datumod AND pva.pag_datumdo)
                     OR (ox.datum_ponuda>=pva.pag_datumod AND pva.pag_datumdo IS NULL))
             ) AS prov_agent_config_count
        FROM ({inner_sql}) m,
             "viki".os_aneks_faktura f9
        WHERE f9.os_aneks_fakturaid = m.os_aneks_fakturaid
    """

    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise Exception("Database connection failed")

    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _fetch_agent_structure(month: int, year: int) -> pd.DataFrame:
    sql = f"""
        SELECT
            a.par_agentid,
            vrati_agent_name(a.par_agentid) AS agent_name,
            a.par_nadreden_agentid,
            vrati_agent_name(a.par_nadreden_agentid) AS nadreden_agent_name,
            d.desc_mk AS filijala,
            e.desc_mk AS region,
            t.desc_mk AS team,
            pa.email,
            pa.par_status_aktiven AS aktiven,
            vrati_agent_pozicija(a.par_agentid, {month}, {year}) AS agent_nivo
        FROM par_agent_st a
        LEFT JOIN par_agent_pripadnost b ON a.par_agentid = b.par_agentid
         AND MDY({month}, 1, {year}) BETWEEN b.datum_od AND NVL(b.datum_do, MDY(12,31,3000))
        LEFT JOIN par_regionu_filijala c ON b.par_regionu_filijalaid = c.par_regionu_filijalaid
        LEFT JOIN par_filijala d ON c.par_filijalaid = d.par_filijalaid
        LEFT JOIN par_regionu e ON c.par_regionuid = e.par_regionuid
        LEFT JOIN par_team t ON b.par_teamid = t.par_teamid
        JOIN par_agent pa ON a.par_agentid = pa.par_agentid
        WHERE MDY({month}, 1, {year}) BETWEEN a.pas_datumod AND NVL(a.pas_datumdo, MDY(12,31,3000))
    """

    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise Exception("Database connection failed")

    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _fetch_promotori_zbiren(
    month: Optional[int],
    year: Optional[int],
    agent_id: Optional[int] = None,
    region_id: Optional[int] = None,
    team_id: Optional[int] = None,
) -> pd.DataFrame:
    where_clauses = []
    if month is not None:
        where_clauses.append(f"z.mesec = '{str(month).zfill(2)}'")
    if year is not None:
        where_clauses.append(f"vrati_godina(z.par_yearid) = '{year}'")
    if agent_id:
        where_clauses.append(f"z.par_agentid = {agent_id}")

    ref_year = year if year is not None else datetime.now().year
    ref_month = month if month is not None else datetime.now().month
    if region_id:
        where_clauses.append(f"""
            z.par_agentid IN (
                SELECT p.par_agentid
                FROM par_agent_pripadnost p
                JOIN par_regionu_filijala f ON p.par_regionu_filijalaid = f.par_regionu_filijalaid
                WHERE MDY({ref_month}, 1, {ref_year}) BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,3000))
                  AND f.par_regionuid = {region_id}
            )
        """)
    if team_id:
        where_clauses.append(f"""
            z.par_agentid IN (
                SELECT p.par_agentid
                FROM par_agent_pripadnost p
                WHERE MDY({ref_month}, 1, {ref_year}) BETWEEN p.datum_od AND NVL(p.datum_do, MDY(12,31,3000))
                  AND p.par_teamid = {team_id}
            )
        """)

    sql = """
        SELECT
            z.mesec,
            vrati_godina(z.par_yearid) godina,
            z.par_agentid,
            vrati_agent_name(z.par_agentid) agent_name,
            z.bodovi_licna_prod,
            z.novi_polisi_prov_lp,
            z.bodovi_timska_prod,
            z.novi_polisi_prov_tp,
            z.bodovi_sl_pozicija_lp,
            z.bodovi_sl_pozicija_tp,
            z.storno_polisi_prov_lp,
            z.novi_storno_bodovi_lp,
            z.storno_polisi_prov_tp,
            z.novi_storno_bodovi_tp,
            z.bodovi_period,
            z.novi_polisi_prov,
            z.novi_storno_bodovi,
            z.storno_polisi_prov,
            z.bruto_provizija,
            z.novi_polisi_inkaso_lp,
            z.novi_polisi_inkaso_tp,
            z.novi_inkaso_prov,
            z.rolling_vk,
            z.bonus_inkaso_prov
        FROM provizija_promotori_zbiren z
    """
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise Exception("Database connection failed")

    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _fetch_dosegasni_bodovi(
    month: int,
    year: int,
    polisa_broj: Optional[str] = None,
    agent_id: Optional[int] = None,
) -> pd.DataFrame:
    month_str = str(month).zfill(2)
    bodovi_filter = ""
    provizija_filter = ""
    if agent_id:
        bodovi_filter += f"\n              AND par_agentid = {agent_id}"
        provizija_filter += f"\n              AND par_agentid = {agent_id}"
    if polisa_broj:
        polisa = _sql_text(polisa_broj)
        bodovi_filter += f"\n              AND TRIM(vrati_polisa(os_polisaid)) = '{polisa}'"
        provizija_filter += f"\n              AND TRIM(polisa_broj) = '{polisa}'"
    sql = f"""
        SELECT
            par_agentid,
            '1' tip_produkcija,
            mesec,
            godina,
            SUM(bodovi_tekoven_mesec_l) bodovi_tekoven_mesec_l,
            SUM(iznos_bodovi_tekoven_mesec_l) iznos_bodovi_tekoven_mesec_l,
            SUM(bodovi_tekoven_mesec_t) bodovi_tekoven_mesec_t,
            SUM(iznos_bodovi_tekoven_mesec_t) iznos_bodovi_tekoven_mesec_t,
            SUM(provizija_tekoven_mesec_l) provizija_tekoven_mesec_l,
            SUM(provizija_tekoven_mesec_t) provizija_tekoven_mesec_t
        FROM (
            SELECT
                par_agentid,
                tip_produkcija,
                mesec,
                vrati_godina(par_yearid) godina,
                SUM(br_bodovi) bodovi_tekoven_mesec_l,
                SUM(iznos_bod) iznos_bodovi_tekoven_mesec_l,
                0 bodovi_tekoven_mesec_t,
                0 iznos_bodovi_tekoven_mesec_t,
                0 provizija_tekoven_mesec_l,
                0 provizija_tekoven_mesec_t
            FROM provizija_promotori_bodovi
            WHERE tip_produkcija = 1
              AND mesec = '{month_str}'
              AND vrati_godina(par_yearid) = '{year}'
              {bodovi_filter}
            GROUP BY 1,2,3,4

            UNION ALL

            SELECT
                par_agentid,
                tip_produkcija,
                mesec,
                vrati_godina(par_yearid) godina,
                SUM(br_bodovi),
                SUM(iznos_bod),
                0,
                0,
                0,
                0
            FROM lc_provizija_agent_bodovi
            WHERE tip_produkcija = 1
              AND par_statusid = 1
              AND mesec = '{month_str}'
              AND vrati_godina(par_yearid) = '{year}'
              {bodovi_filter}
            GROUP BY 1,2,3,4

            UNION ALL

            SELECT
                par_agentid,
                tip_produkcija,
                mesec,
                vrati_godina(par_yearid) godina,
                0,
                0,
                SUM(br_bodovi) bodovi_tekoven_mesec_t,
                SUM(iznos_bod) iznos_bodovi_tekoven_mesec_t,
                0,
                0
            FROM provizija_promotori_bodovi
            WHERE tip_produkcija = 2
              AND mesec = '{month_str}'
              AND vrati_godina(par_yearid) = '{year}'
              {bodovi_filter}
            GROUP BY 1,2,3,4

            UNION ALL

            SELECT
                par_agentid,
                tip_produkcija,
                mesec,
                vrati_godina(par_yearid) godina,
                0,
                0,
                SUM(br_bodovi),
                SUM(iznos_bod),
                0,
                0
            FROM lc_provizija_agent_bodovi
            WHERE tip_produkcija = 2
              AND par_statusid = 1
              AND mesec = '{month_str}'
              AND vrati_godina(par_yearid) = '{year}'
              {bodovi_filter}
            GROUP BY 1,2,3,4

            UNION ALL

            SELECT
                par_agentid,
                '1' tip_produkcija,
                mesec,
                godina,
                0,
                0,
                0,
                0,
                SUM(iznos_provizija) provizija_tekoven_mesec_l,
                0
            FROM agenti_provizija1
            WHERE tip_provizija = 'Лична'
              AND mesec = '{month_str}'
              AND godina = '{year}'
              {provizija_filter}
            GROUP BY 1,2,3,4

            UNION ALL

            SELECT
                par_agentid,
                '2' tip_produkcija,
                mesec,
                godina,
                0,
                0,
                0,
                0,
                0,
                SUM(iznos_provizija) provizija_tekoven_mesec_t
            FROM agenti_provizija1
            WHERE tip_provizija = 'Тимска'
              AND mesec = '{month_str}'
              AND godina = '{year}'
              {provizija_filter}
            GROUP BY 1,2,3,4
        ) x
        GROUP BY 1,2,3,4
    """

    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        raise Exception("Database connection failed")

    try:
        print("Executing SQL:", sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _find_col(df: pd.DataFrame, name: str) -> Optional[str]:
    wanted = name.lower()
    for col in df.columns:
        if str(col).lower() == wanted:
            return col
    return None


def _series_text(df: pd.DataFrame, name: str) -> pd.Series:
    col = _find_col(df, name)
    if col is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[col].fillna("").astype(str).str.strip()


def _series_num(df: pd.DataFrame, name: str) -> pd.Series:
    col = _find_col(df, name)
    if col is None:
        return pd.Series([0] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def _write_sheet(writer, df: pd.DataFrame, sheet_name: str):
    df.to_excel(writer, index=False, sheet_name=sheet_name)
    worksheet = writer.sheets[sheet_name]
    workbook = writer.book
    header_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#176B5D",
        "border": 1
    })
    alert_fmt = workbook.add_format({
        "bg_color": "#FFE2E2",
        "font_color": "#9C0006",
        "border": 1
    })

    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(0, col_idx, col_name, header_fmt)
        values = df[col_name].fillna("").astype(str).head(300).tolist() if not df.empty else []
        max_len = max([len(str(col_name))] + [len(v) for v in values])
        worksheet.set_column(col_idx, col_idx, min(max(max_len + 2, 12), 42))

    if sheet_name == "Nepresmetani_Fakturi" and len(df) > 0 and "status_sporedba" in df.columns:
        # Vo Multilevel Excel kontrolata ne se site redovi greski. Crveno se
        # samo statusite sto baraat korekcija; ocekuvanite delovni sostojbi
        # (zatvoren agent, nema definicija, necelosna naplata, nula bodovi)
        # ostanuvaat bez crvena pozadina.
        from xlsxwriter.utility import xl_col_to_name
        status_col = xl_col_to_name(df.columns.get_loc("status_sporedba"))
        error_formula = (
            f'=OR(${status_col}2="NAPLATENA_NE_PRESMETANA",'
            f'${status_col}2="LC_BODOVI_NO_NEMA_PRESMETKA",'
            f'${status_col}2="PROMOTOR_BODOVI_NO_NEMA_PRESMETKA")'
        )
        worksheet.conditional_format(
            1, 0, len(df), max(len(df.columns) - 1, 0),
            {"type": "formula", "criteria": error_formula, "format": alert_fmt}
        )
    elif sheet_name in ("Kontrola_Dupli", "Negativno_Saldo", "Sporedba_Fakturi", "Sporedba_Bodovi") and len(df) > 0:
        worksheet.conditional_format(
            1, 0, len(df), max(len(df.columns) - 1, 0),
            {"type": "no_errors", "format": alert_fmt}
        )

    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, len(df), max(len(df.columns) - 1, 0))


def _build_grid_results(df: pd.DataFrame) -> pd.DataFrame:
    """Return the legacy SQL-grid layout used by the monthly prov_*.xls report."""
    source = df.copy()
    source_by_name = {str(col).lower(): col for col in source.columns}

    def text_column(name: str) -> pd.Series:
        column = source_by_name.get(name.lower())
        if column is None:
            return pd.Series([""] * len(source), index=source.index, dtype="object")
        return source[column].fillna("").astype(str)

    tip_provizija = text_column("tip_provizija")
    if tip_provizija.str.strip().eq("").all():
        tip_provizija = text_column("nacin_provizija")

    control_key = (
        text_column("agent_name").str.strip()
        + text_column("polisa_broj").str.strip()
        + text_column("faktura").str.strip()
        + text_column("tip_knizi").str.strip()
        + tip_provizija.str.strip()
        + text_column("provizija").str.strip()
    )

    grid_columns = [
        "agent_name", "polisa_broj", "faktura", "tip_knizi", "koja_godina",
        "br_rati", "rata", "naplata", "proc_prov", "iznos_provizija",
        "os_aneks_fakturaid", "naplata_fak", "par_agentid", "tip_provizija",
        "provizija", "br_bodovi", "iznos_bod", "par_client", "dat_naplata",
        "dogovoruvac_name", "skadenca_datum_od", "period_osig",
        "skadenca_datum_do", "premija_zivot", "premija_nezgoda",
        "premija_zdravstveno", "premija_tbs", "sap_risk_business", "mesec",
        "par_yearid", "godina", "bod",
    ]

    result = pd.DataFrame(index=source.index)
    result["контрола за дупли"] = control_key
    for name in grid_columns:
        if name == "tip_provizija":
            result[name] = tip_provizija
        else:
            column = source_by_name.get(name.lower())
            result[name] = source[column] if column is not None else ""
    return result


def _prep_sporedba_work(df: pd.DataFrame) -> pd.DataFrame:
    """Minimalna podgotovka na prov_promotori_tp_ex redovi potrebna za
    sporedba naplata vs presmetana provizija (vidi _compute_sporedba_fakturi)."""
    work = df.copy()
    work["_par_agentid"] = _series_text(work, "par_agentid")
    work["_polisa_broj"] = _series_text(work, "polisa_broj")
    work["_faktura"] = _series_text(work, "faktura")
    work["_os_aneks_fakturaid"] = _series_text(work, "os_aneks_fakturaid")
    work["_iznos_provizija"] = _series_num(work, "iznos_provizija")
    work["_naplata"] = _series_num(work, "naplata")
    work["_faktura_key"] = work["_faktura"].str.upper()
    work["_sporedba_key"] = work["_os_aneks_fakturaid"].where(
        work["_os_aneks_fakturaid"] != "",
        work["_faktura_key"],
    )
    return work


def _compute_sporedba_fakturi(work: pd.DataFrame, naplata_df: pd.DataFrame):
    """
    Sporeduva naplata (report_fakturi naplata za dadeniot mesec, _fetch_report_naplata)
    so presmetana provizija (prov_promotori_tp_ex) po faktura/os_aneks_fakturaid.

    `work` mora da ima kolonite _polisa_broj, _faktura, _os_aneks_fakturaid,
    _sporedba_key, _par_agentid, _iznos_provizija, _naplata (vidi _prep_sporedba_work).

    Vraca (naplata_zbiren, naplata_po_polisa, sporedba_fakturi, kontrola_fakturi, nepresmetani_fakturi).
    nepresmetani_fakturi = naplateni fakturi (vo dadeniot mesec) za koi nema pronajdena presmetka.
    """
    naplata_work = naplata_df.copy()
    if not naplata_work.empty:
        naplata_work["_polisa"] = _series_text(naplata_work, "polisa")
        naplata_work["_faktura"] = _series_text(naplata_work, "faktura")
        naplata_work["_os_aneks_fakturaid"] = _series_text(naplata_work, "os_aneks_fakturaid")
        naplata_work["_faktura_key"] = naplata_work["_faktura"].str.upper()
        naplata_work["_sporedba_key"] = naplata_work["_os_aneks_fakturaid"].where(
            naplata_work["_os_aneks_fakturaid"] != "",
            naplata_work["_faktura_key"],
        )
        naplata_work["_client_naziv"] = _series_text(naplata_work, "client_naziv")
        naplata_work["_agent_naziv"] = _series_text(naplata_work, "agent_naziv")
        naplata_work["_par_agentid"] = _series_text(naplata_work, "par_agent_id")
        naplata_work["_iznos_p"] = _series_num(naplata_work, "iznos_p")
        naplata_work["_iznos_p_den"] = _series_num(naplata_work, "iznos_p_den")
        naplata_work["_iznos_d"] = _series_num(naplata_work, "iznos_d")
        naplata_work["_iznos_d_den"] = _series_num(naplata_work, "iznos_d_den")
        naplata_work["_faktura_iznos"] = _series_num(naplata_work, "faktura_iznos")
        naplata_work["_faktura_naplata_vkupno"] = _series_num(naplata_work, "faktura_naplata_vkupno")
        naplata_work["_faktura_naplata_do_period"] = _series_num(naplata_work, "faktura_naplata_do_period")
        naplata_work["_lc_bodovi_count"] = _series_num(naplata_work, "lc_bodovi_count")
        naplata_work["_lc_iznos_bod"] = _series_num(naplata_work, "lc_iznos_bod")
        naplata_work["_promoter_bodovi_count"] = _series_num(naplata_work, "promoter_bodovi_count")
        naplata_work["_lc_presmetki_count"] = _series_num(naplata_work, "lc_presmetki_count")
        naplata_work["_promoter_presmetki_count"] = _series_num(naplata_work, "promoter_presmetki_count")
        naplata_work["_agent_status"] = _series_text(naplata_work, "agent_status").str.upper()
        naplata_work["_prov_agentid"] = _series_text(naplata_work, "prov_agentid")
        naplata_work["_prov_agent_naziv"] = _series_text(naplata_work, "prov_agent_naziv")
        naplata_work["_prov_agent_config_count"] = _series_num(naplata_work, "prov_agent_config_count")

        naplata_zbiren = naplata_work.groupby(["_polisa", "_faktura", "_os_aneks_fakturaid", "_sporedba_key"], dropna=False).agg(
            client_naziv=("_client_naziv", "first"),
            agent_naziv=("_agent_naziv", "first"),
            agentid=("_par_agentid", "first"),
            broj_naplati=("_sporedba_key", "size"),
            vk_iznos_p=("_iznos_p", "sum"),
            vk_iznos_p_den=("_iznos_p_den", "sum"),
            vk_iznos_d=("_iznos_d", "sum"),
            vk_iznos_d_den=("_iznos_d_den", "sum"),
            # Vkupen iznos na fakturata i kumulativna naplata (vrati_naplata UDF) niz SITE
            # meseci — ne samo za izbraniot period — za da moze pravilno da se oceni dali
            # fakturata e CELOSNO naplatena (mesecno-skopiraniot vk_iznos_p/vk_iznos_d
            # gore ne e dovolen, bidejki naplata/dolgot mozat da se knizat vo razlicni meseci).
            faktura_iznos=("_faktura_iznos", "first"),
            faktura_naplata_vkupno=("_faktura_naplata_vkupno", "first"),
            faktura_naplata_do_period=("_faktura_naplata_do_period", "first"),
            lc_bodovi_count=("_lc_bodovi_count", "first"),
            lc_iznos_bod=("_lc_iznos_bod", "first"),
            promoter_bodovi_count=("_promoter_bodovi_count", "first"),
            lc_presmetki_count=("_lc_presmetki_count", "first"),
            promoter_presmetki_count=("_promoter_presmetki_count", "first"),
            agent_status=("_agent_status", "first"),
            prov_agentid=("_prov_agentid", "first"),
            prov_agent_naziv=("_prov_agent_naziv", "first"),
            prov_agent_config_count=("_prov_agent_config_count", "first"),
        ).reset_index().rename(columns={
            "_polisa": "polisa",
            "_faktura": "faktura",
            "_os_aneks_fakturaid": "os_aneks_fakturaid",
        })
        naplata_po_polisa = naplata_work.groupby(["_polisa"], dropna=False).agg(
            broj_fakturi=("_faktura", "nunique"),
            broj_aneksi=("_os_aneks_fakturaid", "nunique"),
            broj_naplati=("_polisa", "size"),
            client_naziv=("_client_naziv", "first"),
            agent_naziv=("_agent_naziv", "first"),
            vk_iznos_p=("_iznos_p", "sum"),
            vk_iznos_p_den=("_iznos_p_den", "sum"),
            vk_iznos_d=("_iznos_d", "sum"),
            vk_iznos_d_den=("_iznos_d_den", "sum"),
        ).reset_index().rename(columns={"_polisa": "polisa"})
    else:
        naplata_zbiren = pd.DataFrame(columns=[
            "polisa", "faktura", "os_aneks_fakturaid", "_sporedba_key", "client_naziv", "agent_naziv", "agentid",
            "broj_naplati", "vk_iznos_p", "vk_iznos_p_den", "vk_iznos_d", "vk_iznos_d_den",
            "faktura_iznos", "faktura_naplata_vkupno", "faktura_naplata_do_period",
            "lc_bodovi_count", "lc_iznos_bod", "promoter_bodovi_count",
            "lc_presmetki_count", "promoter_presmetki_count"
            , "agent_status", "prov_agentid", "prov_agent_naziv", "prov_agent_config_count"
        ])
        naplata_po_polisa = pd.DataFrame(columns=[
            "polisa", "broj_fakturi", "broj_aneksi", "broj_naplati", "client_naziv", "agent_naziv",
            "vk_iznos_p", "vk_iznos_p_den", "vk_iznos_d", "vk_iznos_d_den"
        ])

    presmetka_fakturi_work = work[work["_sporedba_key"] != ""]
    presmetani_fakturi = presmetka_fakturi_work.groupby("_sporedba_key", dropna=False).agg(
        presmetka_polisa=("_polisa_broj", "first"),
        presmetka_faktura=("_faktura", "first"),
        presmetka_os_aneks_fakturaid=("_os_aneks_fakturaid", "first"),
        broj_presmetki=("_sporedba_key", "size"),
        broj_agenti=("_par_agentid", "nunique"),
        presmetana_provizija=("_iznos_provizija", "sum"),
        presmetana_naplata=("_naplata", "sum"),
    ).reset_index()

    sporedba_fakturi = naplata_zbiren.merge(
        presmetani_fakturi,
        on="_sporedba_key",
        how="outer",
        indicator=True,
    )
    if not sporedba_fakturi.empty:
        for col in ["broj_naplati", "vk_iznos_p", "vk_iznos_p_den", "vk_iznos_d", "vk_iznos_d_den",
                    "broj_presmetki", "broj_agenti", "presmetana_provizija", "presmetana_naplata",
                    "faktura_iznos", "faktura_naplata_vkupno", "faktura_naplata_do_period",
                    "lc_bodovi_count", "lc_iznos_bod", "promoter_bodovi_count",
                    "lc_presmetki_count", "promoter_presmetki_count", "prov_agent_config_count"]:
            sporedba_fakturi[col] = pd.to_numeric(sporedba_fakturi[col], errors="coerce").fillna(0)

        sporedba_fakturi["faktura_sporedba"] = sporedba_fakturi["faktura"].fillna(sporedba_fakturi["presmetka_faktura"])
        sporedba_fakturi["polisa_sporedba"] = sporedba_fakturi["polisa"].fillna(sporedba_fakturi["presmetka_polisa"])
        sporedba_fakturi["os_aneks_fakturaid_sporedba"] = sporedba_fakturi["os_aneks_fakturaid"].fillna(
            sporedba_fakturi["presmetka_os_aneks_fakturaid"]
        )
        sporedba_fakturi["razlika_naplata"] = sporedba_fakturi["vk_iznos_p"] - sporedba_fakturi["presmetana_naplata"]
        # prov_promotori_tp_ex/agenti_provizija ne gi vrakja TBS fakturite
        # (faktura tip 2974, bodovi tip 285/1128) poradi strogiot join po
        # par_tip_kniziid. Osnovnite presmetkovni tabeli se avtoritativni:
        # ako fakturata postoi tamu, taa e presmetana i ne smee povtorno da se
        # prijavi kako NAPLATENA_NE_PRESMETANA.
        ima_presmetka_vo_base = (
            sporedba_fakturi["lc_presmetki_count"].gt(0)
            | sporedba_fakturi["promoter_presmetki_count"].gt(0)
        )
        ima_bilo_kakva_presmetka = sporedba_fakturi["broj_presmetki"].gt(0) | ima_presmetka_vo_base
        sporedba_fakturi["presmetana"] = ima_bilo_kakva_presmetka.map({True: "DA", False: "NE"})
        sporedba_fakturi["ima_naplata"] = sporedba_fakturi["broj_naplati"].gt(0).map({True: "DA", False: "NE"})

        sporedba_fakturi["status_sporedba"] = "OK"
        sporedba_fakturi.loc[sporedba_fakturi["_merge"] == "left_only", "status_sporedba"] = "NAPLATENA_NE_PRESMETANA"
        sporedba_fakturi.loc[
            (sporedba_fakturi["_merge"] == "left_only") & ima_presmetka_vo_base,
            "status_sporedba",
        ] = "PRESMETANA_VO_BASE_NEVIDLIVA_VO_VIEW"
        # Proveri ja naplatata do posledniot den od izbraniot period. vrati_naplata()
        # ne e dovolna tuka, bidejki vklucuva i naplati od podocnezhni meseci.
        polisa_za_status = sporedba_fakturi["polisa_sporedba"].fillna("").astype(str)
        specijalen_prefiks = polisa_za_status.str.startswith("19/") | polisa_za_status.str.startswith("25/")
        celosna_do_period = sporedba_fakturi["faktura_naplata_do_period"] >= (
            sporedba_fakturi["faktura_iznos"] - 0.01
        )
        sporedba_fakturi.loc[
            (sporedba_fakturi["_merge"] == "left_only")
            & ~ima_presmetka_vo_base
            & ~specijalen_prefiks
            & ~celosna_do_period,
            "status_sporedba",
        ] = "NECELOSNO_NAPLATENA_ZA_PERIOD"
        missing_and_paid = (
            (sporedba_fakturi["_merge"] == "left_only")
            & ~ima_presmetka_vo_base
            & celosna_do_period
        )
        no_points = sporedba_fakturi["lc_bodovi_count"].eq(0) & sporedba_fakturi["promoter_bodovi_count"].eq(0)
        lc_zero = sporedba_fakturi["lc_bodovi_count"].gt(0) & sporedba_fakturi["lc_iznos_bod"].abs().le(0.01)
        sporedba_fakturi.loc[missing_and_paid & no_points, "status_sporedba"] = "NEMA_BODOVI"
        sporedba_fakturi.loc[missing_and_paid & lc_zero, "status_sporedba"] = "LC_IZNOS_BOD_NULA"
        sporedba_fakturi.loc[
            missing_and_paid & sporedba_fakturi["lc_bodovi_count"].gt(0) & ~lc_zero,
            "status_sporedba",
        ] = "LC_BODOVI_NO_NEMA_PRESMETKA"
        sporedba_fakturi.loc[
            missing_and_paid
            & sporedba_fakturi["lc_bodovi_count"].eq(0)
            & sporedba_fakturi["promoter_bodovi_count"].gt(0),
            "status_sporedba",
        ] = "PROMOTOR_BODOVI_NO_NEMA_PRESMETKA"
        nema_prov_config = sporedba_fakturi["prov_agent_config_count"].eq(0)
        sporedba_fakturi.loc[
            missing_and_paid & nema_prov_config,
            "status_sporedba",
        ] = "AGENT_NEMA_DEFINIRANA_PROVIZIJA"
        # Status Z e ocekuvana delovna blokada, a ne greska vo presmetkata.
        # Ovaa proverka e posledna za missing+paid za da ima prednost nad
        # generickite LC/promoter statusi pogore.
        zatvoren_agent = sporedba_fakturi["agent_status"].fillna("").astype(str).str.upper().eq("Z")
        sporedba_fakturi.loc[missing_and_paid & zatvoren_agent, "status_sporedba"] = "AGENT_ZATVOREN"
        sporedba_fakturi.loc[sporedba_fakturi["_merge"] == "right_only", "status_sporedba"] = "PRESMETANA_NE_NAPLATENA"
        sporedba_fakturi.loc[
            (sporedba_fakturi["_merge"] == "both") & (sporedba_fakturi["razlika_naplata"].abs() > 0.01),
            "status_sporedba"
        ] = "RAZLIKA_NAPLATA"

        sporedba_fakturi["komentar"] = sporedba_fakturi["status_sporedba"].map({
            "OK": "naplata i presmetka se poklopuvaat po os_aneks_fakturaid/faktura",
            "NAPLATENA_NE_PRESMETANA": "naplatena faktura ne e pronajdena vo prov_promotori_tp_ex",
            "NECELOSNO_NAPLATENA_ZA_PERIOD": "fakturata ne e celosno naplatena do krajot na izbraniot mesec",
            "NEMA_BODOVI": "nema bodovi ni vo LC ni vo promoter presmetkata",
            "LC_IZNOS_BOD_NULA": "postojat LC bodovi, no iznos_bod e nula",
            "LC_BODOVI_NO_NEMA_PRESMETKA": "postojat LC bodovi, no nema LC presmetka za fakturata",
            "PROMOTOR_BODOVI_NO_NEMA_PRESMETKA": "postojat promoter bodovi, no nema promoter presmetka za fakturata",
            "AGENT_NEMA_DEFINIRANA_PROVIZIJA": "agentot nema vazhechka definicija vo provizija_agent; za toj agent ne se presmetuva provizija",
            "AGENT_ZATVOREN": "agentot e zatvoren (status=Z); ponatamosna provizija ne se presmetuva",
            "PRESMETANA_VO_BASE_NEVIDLIVA_VO_VIEW": "presmetkata postoi vo osnovnata tabela, no staroto view ne ja prikazuva poradi tipot na knizenje",
            "PRESMETANA_NE_NAPLATENA": "presmetana faktura ne e pronajdena vo naplata",
            "RAZLIKA_NAPLATA": "postoi razlika pomegju naplata i presmetana naplata"
        })
        zatvoren_mask = sporedba_fakturi["status_sporedba"].eq("AGENT_ZATVOREN")
        sporedba_fakturi.loc[zatvoren_mask, "komentar"] = (
            "Agent "
            + sporedba_fakturi.loc[zatvoren_mask, "prov_agentid"].fillna("").astype(str)
            + " e zatvoren (status=Z)."
        )
        nema_config_mask = sporedba_fakturi["status_sporedba"].eq("AGENT_NEMA_DEFINIRANA_PROVIZIJA")
        sporedba_fakturi.loc[nema_config_mask, "komentar"] = (
            "Za agent "
            + sporedba_fakturi.loc[nema_config_mask, "prov_agentid"].fillna("").astype(str)
            + " ne se presmetuva provizija bidejki ne e definiran vo provizija_agent."
        )
        sporedba_fakturi = sporedba_fakturi[[
            "status_sporedba", "polisa_sporedba", "faktura_sporedba", "os_aneks_fakturaid_sporedba",
            "polisa", "faktura", "os_aneks_fakturaid", "client_naziv", "agent_naziv", "agentid",
            "broj_naplati", "vk_iznos_p", "vk_iznos_p_den", "vk_iznos_d", "vk_iznos_d_den",
            "faktura_iznos", "faktura_naplata_vkupno", "faktura_naplata_do_period",
            "lc_bodovi_count", "lc_iznos_bod", "promoter_bodovi_count",
            "lc_presmetki_count", "promoter_presmetki_count",
            "agent_status",
            "prov_agentid", "prov_agent_naziv", "prov_agent_config_count",
            "presmetka_polisa", "presmetka_faktura", "presmetka_os_aneks_fakturaid", "broj_presmetki", "broj_agenti",
            "presmetana_provizija", "presmetana_naplata", "razlika_naplata",
            "ima_naplata", "presmetana", "komentar"
        ]]
        kontrola_fakturi = sporedba_fakturi[sporedba_fakturi["ima_naplata"] == "DA"].copy()
    else:
        sporedba_fakturi = pd.DataFrame(columns=[
            "status_sporedba", "polisa_sporedba", "faktura_sporedba", "os_aneks_fakturaid_sporedba",
            "polisa", "faktura", "os_aneks_fakturaid", "client_naziv", "agent_naziv", "agentid",
            "broj_naplati", "vk_iznos_p", "vk_iznos_p_den", "vk_iznos_d", "vk_iznos_d_den",
            "faktura_iznos", "faktura_naplata_vkupno", "faktura_naplata_do_period",
            "lc_bodovi_count", "lc_iznos_bod", "promoter_bodovi_count",
            "lc_presmetki_count", "promoter_presmetki_count",
            "agent_status",
            "prov_agentid", "prov_agent_naziv", "prov_agent_config_count",
            "presmetka_polisa", "presmetka_faktura", "presmetka_os_aneks_fakturaid", "broj_presmetki", "broj_agenti",
            "presmetana_provizija", "presmetana_naplata", "razlika_naplata",
            "ima_naplata", "presmetana", "komentar"
        ])
        kontrola_fakturi = pd.DataFrame(columns=[
            "polisa", "faktura", "os_aneks_fakturaid", "client_naziv", "agent_naziv", "agentid", "broj_naplati",
            "vk_iznos_p", "vk_iznos_p_den", "vk_iznos_d", "vk_iznos_d_den",
            "faktura_iznos", "faktura_naplata_vkupno", "faktura_naplata_do_period",
            "lc_bodovi_count", "lc_iznos_bod", "promoter_bodovi_count",
            "lc_presmetki_count", "promoter_presmetki_count",
            "presmetka_polisa", "presmetka_faktura", "presmetka_os_aneks_fakturaid", "broj_presmetki", "broj_agenti",
            "presmetana_provizija", "presmetana_naplata", "razlika_naplata",
            "ima_naplata", "presmetana", "komentar"
        ])

    nepresmetani_fakturi = kontrola_fakturi[kontrola_fakturi["presmetana"] == "NE"].copy() if "presmetana" in kontrola_fakturi.columns else kontrola_fakturi.copy()

    # Za polisi BEZ prefiks "19/" ili "25/" flagiraj kako nepresmetana samo ako
    # naplatata e celosna (vk_iznos_p >= vk_iznos_d) — dodeka naplatata e
    # delumna, ocekuvano e presmetkata na provizija da uste ne postoi.
    # Polisite so prefiks "19/"/"25/" ne podlezat na ova ogranicuvanje
    # (ista logika kako "19/" isklucuvanjeto vo kontrola_polisi.py).
    if not nepresmetani_fakturi.empty and "polisa_sporedba" in nepresmetani_fakturi.columns:
        polisa_txt = nepresmetani_fakturi["polisa_sporedba"].fillna("").astype(str)
        ima_specijalen_prefiks = polisa_txt.str.startswith("19/") | polisa_txt.str.startswith("25/")
        # Sporeduva vkupniot iznos na fakturata (os_aneks_faktura.iznos) so KUMULATIVNATA
        # naplata (vrati_naplata UDF, site meseci) — ne mesecno-skopiraniot vk_iznos_p/
        # vk_iznos_d, bidejki dolgot i naplatata mozat da bidat knizeni vo razlicni meseci.
        celosna_naplata = nepresmetani_fakturi["faktura_naplata_vkupno"] >= (
            nepresmetani_fakturi["faktura_iznos"] - 0.01
        )
        # Ne gi otfrlaj necelosno naplatenite: statusot pogore ja objasnuva pricinata
        # i korisnikot treba da gi vidi vo pregledot za izbraniot mesec.

    return naplata_zbiren, naplata_po_polisa, sporedba_fakturi, kontrola_fakturi, nepresmetani_fakturi


def _build_multilevel_workbook(
    df: pd.DataFrame,
    naplata_df: pd.DataFrame,
    agent_structure_df: pd.DataFrame,
    dosegasni_bodovi_df: pd.DataFrame,
    zbiren_df: pd.DataFrame,
    month: Optional[int],
    year: Optional[int]
) -> BytesIO:
    work = df.copy()
    grid_results = _build_grid_results(df)
    work["_par_agentid"] = _series_text(work, "par_agentid")
    work["_agent_name"] = _series_text(work, "agent_name")
    work["_polisa_broj"] = _series_text(work, "polisa_broj")
    work["_faktura"] = _series_text(work, "faktura")
    work["_os_aneks_fakturaid"] = _series_text(work, "os_aneks_fakturaid")
    work["_rata"] = _series_text(work, "rata")
    work["_nacin_provizija"] = _series_text(work, "nacin_provizija")
    if work["_nacin_provizija"].eq("").all():
        work["_nacin_provizija"] = _series_text(work, "tip_provizija")
    work["_dogovoruvac_name"] = _series_text(work, "dogovoruvac_name")
    work["_iznos_provizija"] = _series_num(work, "iznos_provizija")
    work["_br_bodovi"] = _series_num(work, "br_bodovi")
    work["_iznos_bod"] = _series_num(work, "iznos_bod")
    work["_naplata"] = _series_num(work, "naplata")
    work["_faktura_key"] = work["_faktura"].str.upper()
    work["_sporedba_key"] = work["_os_aneks_fakturaid"].where(
        work["_os_aneks_fakturaid"] != "",
        work["_faktura_key"],
    )

    agent_zbiren = work.groupby(["_par_agentid", "_agent_name"], dropna=False).agg(
        broj_polisi=("_polisa_broj", "nunique"),
        broj_zapisi=("_polisa_broj", "size"),
        vkupno_bodovi=("_br_bodovi", "sum"),
    ).reset_index().rename(columns={"_par_agentid": "par_agentid", "_agent_name": "agent_name"})
    licna = work[work["_nacin_provizija"] == "Лична"].groupby("_par_agentid")["_iznos_provizija"].sum()
    timska = work[work["_nacin_provizija"] == "Тимска"].groupby("_par_agentid")["_iznos_provizija"].sum()
    nedefinirana = work[~work["_nacin_provizija"].isin(["Лична", "Тимска"])].groupby("_par_agentid")["_iznos_provizija"].sum()
    agent_zbiren["licna_provizija"] = agent_zbiren["par_agentid"].map(licna).fillna(0)
    agent_zbiren["timska_provizija"] = agent_zbiren["par_agentid"].map(timska).fillna(0)
    agent_zbiren["nedefinirana_provizija"] = agent_zbiren["par_agentid"].map(nedefinirana).fillna(0)
    agent_zbiren["vkupna_provizija"] = (
        agent_zbiren["licna_provizija"] + agent_zbiren["timska_provizija"] + agent_zbiren["nedefinirana_provizija"]
    )

    current_bodovi = work.assign(
        _is_licna=work["_nacin_provizija"].str.contains("Лична|Licna", case=False, na=False),
        _is_timska=work["_nacin_provizija"].str.contains("Тимска|Timska", case=False, na=False),
    )
    current_bodovi = current_bodovi.groupby(["_par_agentid"], dropna=False).agg(
        tekovno_bodovi_l=("_br_bodovi", lambda s: s[current_bodovi.loc[s.index, "_is_licna"]].sum()),
        tekovno_iznos_bodovi_l=("_iznos_bod", lambda s: s[current_bodovi.loc[s.index, "_is_licna"]].sum()),
        tekovno_bodovi_t=("_br_bodovi", lambda s: s[current_bodovi.loc[s.index, "_is_timska"]].sum()),
        tekovno_iznos_bodovi_t=("_iznos_bod", lambda s: s[current_bodovi.loc[s.index, "_is_timska"]].sum()),
        tekovno_provizija_l=("_iznos_provizija", lambda s: s[current_bodovi.loc[s.index, "_is_licna"]].sum()),
        tekovno_provizija_t=("_iznos_provizija", lambda s: s[current_bodovi.loc[s.index, "_is_timska"]].sum()),
    ).reset_index().rename(columns={"_par_agentid": "par_agentid"})

    dosegasni_work = dosegasni_bodovi_df.copy()
    if not dosegasni_work.empty:
        dosegasni_work.columns = [str(c).lower() for c in dosegasni_work.columns]
        dosegasni_work["par_agentid"] = _series_text(dosegasni_work, "par_agentid")
        for col in [
            "bodovi_tekoven_mesec_l", "iznos_bodovi_tekoven_mesec_l",
            "bodovi_tekoven_mesec_t", "iznos_bodovi_tekoven_mesec_t",
            "provizija_tekoven_mesec_l", "provizija_tekoven_mesec_t"
        ]:
            dosegasni_work[col] = _series_num(dosegasni_work, col)
    else:
        dosegasni_work = pd.DataFrame(columns=[
            "par_agentid", "bodovi_tekoven_mesec_l", "iznos_bodovi_tekoven_mesec_l",
            "bodovi_tekoven_mesec_t", "iznos_bodovi_tekoven_mesec_t",
            "provizija_tekoven_mesec_l", "provizija_tekoven_mesec_t"
        ])

    sporedba_bodovi = current_bodovi.merge(
        dosegasni_work,
        on="par_agentid",
        how="outer",
    )
    for col in [
        "tekovno_bodovi_l", "tekovno_iznos_bodovi_l", "tekovno_bodovi_t", "tekovno_iznos_bodovi_t",
        "tekovno_provizija_l", "tekovno_provizija_t",
        "bodovi_tekoven_mesec_l", "iznos_bodovi_tekoven_mesec_l",
        "bodovi_tekoven_mesec_t", "iznos_bodovi_tekoven_mesec_t",
        "provizija_tekoven_mesec_l", "provizija_tekoven_mesec_t"
    ]:
        sporedba_bodovi[col] = pd.to_numeric(sporedba_bodovi[col], errors="coerce").fillna(0)

    agent_names = work.groupby("_par_agentid")["_agent_name"].first()
    sporedba_bodovi["agent_name"] = sporedba_bodovi["par_agentid"].map(agent_names).fillna("")
    sporedba_bodovi["diff_bodovi_l"] = sporedba_bodovi["tekovno_bodovi_l"] - sporedba_bodovi["bodovi_tekoven_mesec_l"]
    sporedba_bodovi["diff_iznos_bodovi_l"] = sporedba_bodovi["tekovno_iznos_bodovi_l"] - sporedba_bodovi["iznos_bodovi_tekoven_mesec_l"]
    sporedba_bodovi["diff_bodovi_t"] = sporedba_bodovi["tekovno_bodovi_t"] - sporedba_bodovi["bodovi_tekoven_mesec_t"]
    sporedba_bodovi["diff_iznos_bodovi_t"] = sporedba_bodovi["tekovno_iznos_bodovi_t"] - sporedba_bodovi["iznos_bodovi_tekoven_mesec_t"]
    sporedba_bodovi["diff_provizija_l"] = sporedba_bodovi["tekovno_provizija_l"] - sporedba_bodovi["provizija_tekoven_mesec_l"]
    sporedba_bodovi["diff_provizija_t"] = sporedba_bodovi["tekovno_provizija_t"] - sporedba_bodovi["provizija_tekoven_mesec_t"]
    diff_cols = ["diff_bodovi_l", "diff_iznos_bodovi_l", "diff_bodovi_t", "diff_iznos_bodovi_t", "diff_provizija_l", "diff_provizija_t"]
    sporedba_bodovi["status_sporedba"] = sporedba_bodovi[diff_cols].abs().gt(0.01).any(axis=1).map({True: "RAZLIKA", False: "OK"})
    sporedba_bodovi = sporedba_bodovi[[
        "status_sporedba", "par_agentid", "agent_name",
        "tekovno_bodovi_l", "bodovi_tekoven_mesec_l", "diff_bodovi_l",
        "tekovno_iznos_bodovi_l", "iznos_bodovi_tekoven_mesec_l", "diff_iznos_bodovi_l",
        "tekovno_bodovi_t", "bodovi_tekoven_mesec_t", "diff_bodovi_t",
        "tekovno_iznos_bodovi_t", "iznos_bodovi_tekoven_mesec_t", "diff_iznos_bodovi_t",
        "tekovno_provizija_l", "provizija_tekoven_mesec_l", "diff_provizija_l",
        "tekovno_provizija_t", "provizija_tekoven_mesec_t", "diff_provizija_t",
    ]]
    neusoglaseni_bodovi = sporedba_bodovi[sporedba_bodovi["status_sporedba"] != "OK"].copy()
    if month is None or year is None:
        sporedba_bodovi = pd.DataFrame(columns=[
            "status_sporedba", "par_agentid", "agent_name",
            "tekovno_bodovi_l", "bodovi_tekoven_mesec_l", "diff_bodovi_l",
            "tekovno_iznos_bodovi_l", "iznos_bodovi_tekoven_mesec_l", "diff_iznos_bodovi_l",
            "tekovno_bodovi_t", "bodovi_tekoven_mesec_t", "diff_bodovi_t",
            "tekovno_iznos_bodovi_t", "iznos_bodovi_tekoven_mesec_t", "diff_iznos_bodovi_t",
            "tekovno_provizija_l", "provizija_tekoven_mesec_l", "diff_provizija_l",
            "tekovno_provizija_t", "provizija_tekoven_mesec_t", "diff_provizija_t",
        ])
        neusoglaseni_bodovi = sporedba_bodovi.copy()

    polisa_zbiren = work.groupby(
        ["_polisa_broj", "_dogovoruvac_name", "_faktura", "_os_aneks_fakturaid", "_rata"],
        dropna=False
    ).agg(
        broj_agenti=("_par_agentid", "nunique"),
        broj_zapisi=("_par_agentid", "size"),
        vk_naplata=("_naplata", "sum"),
    ).reset_index().rename(columns={
        "_polisa_broj": "polisa_broj",
        "_dogovoruvac_name": "dogovoruvac_name",
        "_faktura": "faktura",
        "_os_aneks_fakturaid": "os_aneks_fakturaid",
        "_rata": "rata",
    })

    naplata_zbiren, naplata_po_polisa, sporedba_fakturi, kontrola_fakturi, nepresmetani_fakturi = _compute_sporedba_fakturi(work, naplata_df)
    neusoglaseni_fakturi = sporedba_fakturi[sporedba_fakturi["status_sporedba"] != "OK"].copy() if "status_sporedba" in sporedba_fakturi.columns else sporedba_fakturi.copy()

    zbirna_provizija = zbiren_df.copy()
    if not zbirna_provizija.empty:
        zbirna_provizija.columns = [str(c).lower() for c in zbirna_provizija.columns]
        zbirna_provizija["_par_agentid"] = _series_text(zbirna_provizija, "par_agentid")
        for col in ["bodovi_period", "novi_polisi_prov", "bruto_provizija", "novi_inkaso_prov", "bonus_inkaso_prov"]:
            zbirna_provizija[col] = _series_num(zbirna_provizija, col)
        zbirna_agent = zbirna_provizija.groupby("_par_agentid", dropna=False).agg(
            z_bodovi_period=("bodovi_period", "sum"),
            z_novi_polisi_prov=("novi_polisi_prov", "sum"),
            z_bruto_provizija=("bruto_provizija", "sum"),
            z_novi_inkaso_prov=("novi_inkaso_prov", "sum"),
            z_bonus_inkaso_prov=("bonus_inkaso_prov", "sum"),
        ).reset_index().rename(columns={"_par_agentid": "par_agentid"})
        sporedba_zbirna = agent_zbiren.merge(zbirna_agent, on="par_agentid", how="outer")
        for col in ["vkupno_bodovi", "vkupna_provizija", "z_bodovi_period", "z_bruto_provizija"]:
            sporedba_zbirna[col] = pd.to_numeric(sporedba_zbirna[col], errors="coerce").fillna(0)
        sporedba_zbirna["diff_bodovi"] = sporedba_zbirna["vkupno_bodovi"] - sporedba_zbirna["z_bodovi_period"]
        sporedba_zbirna["diff_provizija"] = sporedba_zbirna["vkupna_provizija"] - sporedba_zbirna["z_bruto_provizija"]
        sporedba_zbirna["status_sporedba"] = (
            sporedba_zbirna[["diff_bodovi", "diff_provizija"]].abs().gt(0.01).any(axis=1)
            .map({True: "RAZLIKA", False: "OK"})
        )
    else:
        zbirna_provizija = pd.DataFrame()
        sporedba_zbirna = pd.DataFrame(columns=[
            "status_sporedba", "par_agentid", "agent_name", "vkupno_bodovi", "z_bodovi_period",
            "diff_bodovi", "vkupna_provizija", "z_bruto_provizija", "diff_provizija"
        ])
    neusoglaseni_zbirna = sporedba_zbirna[sporedba_zbirna["status_sporedba"] != "OK"].copy() if "status_sporedba" in sporedba_zbirna.columns else sporedba_zbirna.copy()

    dup_key = ["_par_agentid", "_polisa_broj", "_faktura", "_os_aneks_fakturaid", "_nacin_provizija", "_iznos_provizija"]
    dup_counts = work.groupby(dup_key, dropna=False).size().reset_index(name="broj_dupli")
    dup_counts = dup_counts[dup_counts["broj_dupli"] > 1]
    kontrola_dupli = work.merge(dup_counts, on=dup_key, how="inner")
    kontrola_dupli["komentar"] = "same agent/policy/faktura/aneks/type/amount"
    kontrola_dupli = kontrola_dupli.drop(columns=[c for c in kontrola_dupli.columns if c.startswith("_")])

    if not dup_counts.empty:
        negativno_saldo = work.merge(dup_counts, on=dup_key, how="inner")
        negativno_saldo = negativno_saldo.groupby(dup_key, dropna=False).agg(
            agent_name=("_agent_name", "first"),
            presmetana_provizija=("_iznos_provizija", "first"),
            isplatena_provizija=("_iznos_provizija", "sum"),
            broj_dupli=("_iznos_provizija", "size"),
        ).reset_index()
        negativno_saldo["saldo"] = negativno_saldo["presmetana_provizija"] - negativno_saldo["isplatena_provizija"]
        negativno_saldo["komentar"] = "duplicate commission posting"
        negativno_saldo = negativno_saldo.rename(columns={
            "_par_agentid": "par_agentid",
            "_polisa_broj": "polisa_broj",
            "_faktura": "faktura",
            "_os_aneks_fakturaid": "os_aneks_fakturaid",
            "_nacin_provizija": "nacin_provizija",
            "_iznos_provizija": "iznos_provizija",
        })
    else:
        negativno_saldo = pd.DataFrame(columns=[
            "par_agentid", "agent_name", "polisa_broj", "faktura", "os_aneks_fakturaid",
            "nacin_provizija", "presmetana_provizija", "isplatena_provizija", "saldo", "komentar"
        ])

    struktura = agent_zbiren[[
        "par_agentid", "agent_name", "licna_provizija", "timska_provizija", "vkupna_provizija"
    ]].copy()
    structure_work = agent_structure_df.copy()
    if not structure_work.empty:
        structure_work.columns = [str(c).lower() for c in structure_work.columns]
        structure_work["_par_agentid"] = _series_text(structure_work, "par_agentid")
        structure_cols = [
            "_par_agentid", "par_nadreden_agentid", "nadreden_agent_name",
            "region", "filijala", "team", "email", "aktiven", "agent_nivo"
        ]
        structure_work = structure_work[[c for c in structure_cols if c in structure_work.columns]]
        structure_work = structure_work.drop_duplicates(subset=["_par_agentid"])
        struktura = struktura.merge(
            structure_work,
            left_on="par_agentid",
            right_on="_par_agentid",
            how="left",
        ).drop(columns=["_par_agentid"], errors="ignore")
    else:
        struktura.insert(2, "par_nadreden_agentid", "")
        struktura.insert(3, "nadreden_agent_name", "")
        struktura.insert(4, "region", "")
        struktura.insert(5, "filijala", "")
        struktura.insert(6, "team", "")
        struktura.insert(7, "email", "")
        struktura.insert(8, "aktiven", "")
        struktura.insert(9, "agent_nivo", "")

    summary = pd.DataFrame([
        ["Period", f"{str(month).zfill(2)}/{year}" if month is not None and year is not None else str(year) if year is not None else "ALL"],
        ["Source", "prov_promotori_tp_ex"],
        ["Detail rows", len(df)],
        ["Agents count", work["_par_agentid"].nunique()],
        ["Policies count", work["_polisa_broj"].nunique()],
        ["Total personal commission", agent_zbiren["licna_provizija"].sum() if not agent_zbiren.empty else 0],
        ["Total team commission", agent_zbiren["timska_provizija"].sum() if not agent_zbiren.empty else 0],
        ["Total commission", agent_zbiren["vkupna_provizija"].sum() if not agent_zbiren.empty else 0],
        ["Naplata rows", len(naplata_df)],
        ["Naplata fakturi", len(naplata_zbiren)],
        ["Nepresmetani naplateni fakturi", len(nepresmetani_fakturi)],
        ["Neusoglaseni fakturi", len(neusoglaseni_fakturi)],
        ["Neusoglaseni bodovi", len(neusoglaseni_bodovi)],
        ["Neusoglaseni zbirna provizija", len(neusoglaseni_zbirna)],
        ["Duplicate groups", len(dup_counts)],
        ["Rows in duplicate groups", len(kontrola_dupli)],
        ["Negative balances", len(negativno_saldo)],
    ], columns=["Metric", "Value"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Aktivni sheetovi (po dogovor):
        _write_sheet(writer, df, "Detalno")
        _write_sheet(writer, summary, "Summary")
        _write_sheet(writer, struktura, "Struktura")
        _write_sheet(writer, naplata_df, "Naplata")
        _write_sheet(writer, nepresmetani_fakturi, "Nepresmetani_Fakturi")

        # Sokrieni za sega (presmetkata ostanuva, samo ne se pisuvaat vo Excel) —
        # otkomentiraj po potreba:
        # _write_sheet(writer, grid_results, "Grid Results")
        # _write_sheet(writer, agent_zbiren, "Agent_Zbiren")
        # _write_sheet(writer, naplata_po_polisa, "Naplata_Po_Polisa")
        # _write_sheet(writer, sporedba_fakturi, "Sporedba_Fakturi")
        # _write_sheet(writer, kontrola_dupli, "Kontrola_Dupli")
        # _write_sheet(writer, negativno_saldo, "Negativno_Saldo")
        # _write_sheet(writer, zbirna_provizija, "Zbirna_Provizija")
        # _write_sheet(writer, sporedba_zbirna, "Sporedba_Zbirna")
        # _write_sheet(writer, polisa_zbiren, "Polisa_Zbiren")
        # _write_sheet(writer, naplata_zbiren.drop(columns=["_sporedba_key"], errors="ignore"), "Naplata_Zbiren")
        # _write_sheet(writer, kontrola_fakturi, "Kontrola_Fakturi")
        # _write_sheet(writer, sporedba_bodovi, "Sporedba_Bodovi")
        # _write_sheet(writer, dosegasni_bodovi_df, "Dosegasni_Bodovi")
    output.seek(0)

    try:
        period = f"{str(month).zfill(2)}/{year}" if month is not None and year is not None else str(year) if year is not None else "ALL"
        commentary = generate_commentary(
            summary.to_dict("records"),
            context=f"Multilevel извештај за провизии на агенти, период {period}",
        )
        output = append_commentary_sheet(output, commentary)
    except Exception:
        logger.exception("AI commentary generation failed for multilevel workbook; continuing without it")

    return output


def _build_zbiren_workbook(
    zbiren_df: pd.DataFrame,
    agent_structure_df: pd.DataFrame,
    month: Optional[int],
    year: Optional[int]
) -> BytesIO:
    work = zbiren_df.copy()
    work.columns = [str(c).lower() for c in work.columns]
    work["_par_agentid"] = _series_text(work, "par_agentid")
    work["_agent_name"] = _series_text(work, "agent_name")

    for col in [
        "bodovi_licna_prod", "novi_polisi_prov_lp", "bodovi_timska_prod", "novi_polisi_prov_tp",
        "bodovi_sl_pozicija_lp", "bodovi_sl_pozicija_tp", "bodovi_period", "novi_polisi_prov",
        "bruto_provizija", "novi_inkaso_prov", "bonus_inkaso_prov", "rolling_vk"
    ]:
        work[col] = _series_num(work, col)

    agent_zbiren = work.groupby(["_par_agentid", "_agent_name"], dropna=False).agg(
        bodovi_licna_prod=("bodovi_licna_prod", "sum"),
        novi_polisi_prov_lp=("novi_polisi_prov_lp", "sum"),
        bodovi_timska_prod=("bodovi_timska_prod", "sum"),
        novi_polisi_prov_tp=("novi_polisi_prov_tp", "sum"),
        bodovi_period=("bodovi_period", "sum"),
        novi_polisi_prov=("novi_polisi_prov", "sum"),
        bruto_provizija=("bruto_provizija", "sum"),
        novi_inkaso_prov=("novi_inkaso_prov", "sum"),
        bonus_inkaso_prov=("bonus_inkaso_prov", "sum"),
        rolling_vk=("rolling_vk", "sum"),
    ).reset_index().rename(columns={"_par_agentid": "par_agentid", "_agent_name": "agent_name"})

    detalno = work.drop(columns=[c for c in work.columns if c.startswith("_")], errors="ignore")

    polisa_zbiren = pd.DataFrame([{
        "komentar": "provizija_promotori_zbiren e agregat po agent/mesec i nema polisa/faktura nivo. Za polisa detal izberi konkretna polisa vo filterot.",
        "source": "provizija_promotori_zbiren",
        "broj_zapisi": len(work),
        "broj_agenti": work["_par_agentid"].nunique(),
        "vkupno_bodovi": agent_zbiren["bodovi_period"].sum() if not agent_zbiren.empty else 0,
        "vkupno_bruto_provizija": agent_zbiren["bruto_provizija"].sum() if not agent_zbiren.empty else 0,
    }])

    dup_key = ["mesec", "godina", "par_agentid"]
    dup_source = work[[c for c in dup_key if c in work.columns]].copy()
    if len(dup_source.columns) == len(dup_key):
        dup_counts = dup_source.groupby(dup_key, dropna=False).size().reset_index(name="broj_dupli")
        dup_counts = dup_counts[dup_counts["broj_dupli"] > 1]
        kontrola_dupli = detalno.merge(dup_counts, on=dup_key, how="inner") if not dup_counts.empty else pd.DataFrame(columns=list(detalno.columns) + ["broj_dupli", "komentar"])
        if not kontrola_dupli.empty:
            kontrola_dupli["komentar"] = "duplicate row for same mesec/godina/agent in provizija_promotori_zbiren"
    else:
        kontrola_dupli = pd.DataFrame(columns=list(detalno.columns) + ["broj_dupli", "komentar"])

    negativno_cols = [
        "bodovi_licna_prod", "novi_polisi_prov_lp", "bodovi_timska_prod", "novi_polisi_prov_tp",
        "bodovi_period", "novi_polisi_prov", "bruto_provizija", "novi_inkaso_prov", "bonus_inkaso_prov"
    ]
    existing_neg_cols = [c for c in negativno_cols if c in work.columns]
    if existing_neg_cols:
        neg_mask = work[existing_neg_cols].lt(0).any(axis=1)
        negativno_saldo = detalno.loc[neg_mask].copy()
        if not negativno_saldo.empty:
            negativno_saldo["komentar"] = "negative value in zbiren control column"
    else:
        negativno_saldo = pd.DataFrame(columns=list(detalno.columns) + ["komentar"])

    struktura = agent_zbiren[["par_agentid", "agent_name", "bruto_provizija", "novi_inkaso_prov", "bodovi_period"]].copy()
    structure_work = agent_structure_df.copy()
    if not structure_work.empty:
        structure_work.columns = [str(c).lower() for c in structure_work.columns]
        structure_work["_par_agentid"] = _series_text(structure_work, "par_agentid")
        structure_cols = [
            "_par_agentid", "par_nadreden_agentid", "nadreden_agent_name",
            "region", "filijala", "team", "email", "aktiven", "agent_nivo"
        ]
        structure_work = structure_work[[c for c in structure_cols if c in structure_work.columns]]
        structure_work = structure_work.drop_duplicates(subset=["_par_agentid"])
        struktura = struktura.merge(
            structure_work,
            left_on="par_agentid",
            right_on="_par_agentid",
            how="left",
        ).drop(columns=["_par_agentid"], errors="ignore")

    summary = pd.DataFrame([
        ["Period", f"{str(month).zfill(2)}/{year}" if month is not None and year is not None else str(year) if year is not None else "ALL"],
        ["Source", "provizija_promotori_zbiren"],
        ["Rows", len(work)],
        ["Agents count", work["_par_agentid"].nunique()],
        ["Total points", agent_zbiren["bodovi_period"].sum() if not agent_zbiren.empty else 0],
        ["Total new policy commission", agent_zbiren["novi_polisi_prov"].sum() if not agent_zbiren.empty else 0],
        ["Total gross commission", agent_zbiren["bruto_provizija"].sum() if not agent_zbiren.empty else 0],
        ["Total inkaso commission", agent_zbiren["novi_inkaso_prov"].sum() if not agent_zbiren.empty else 0],
        ["Total bonus inkaso", agent_zbiren["bonus_inkaso_prov"].sum() if not agent_zbiren.empty else 0],
        ["Duplicate groups", len(kontrola_dupli)],
        ["Negative balance rows", len(negativno_saldo)],
    ], columns=["Metric", "Value"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        _write_sheet(writer, summary, "Summary")
        _write_sheet(writer, agent_zbiren, "Agent_Zbiren")
        _write_sheet(writer, polisa_zbiren, "Polisa_Zbiren")
        _write_sheet(writer, detalno, "Detalno")
        _write_sheet(writer, kontrola_dupli, "Kontrola_Dupli")
        _write_sheet(writer, negativno_saldo, "Negativno_Saldo")
        _write_sheet(writer, struktura, "Struktura")
    output.seek(0)
    return output


def _validate_multilevel_payload(payload: MultilevelPreglediRequest) -> bool:
    has_period = payload.month is not None and payload.year is not None
    if payload.month is not None and payload.year is None:
        raise HTTPException(status_code=400, detail="Year must be provided when month is selected.")
    if payload.year is None and not payload.polisa_broj and not payload.agent_id:
        raise HTTPException(status_code=400, detail="Provide year, polisa_broj, or agent_id.")
    return has_period


def _multilevel_filename(payload: MultilevelPreglediRequest, has_period: bool) -> str:
    filename_parts = ["multilevel_pregledi"]
    if has_period:
        filename_parts.extend([str(payload.month).zfill(2), str(payload.year)])
    elif payload.year is not None:
        filename_parts.append(str(payload.year))
    if payload.polisa_broj:
        filename_parts.append(_sql_text(payload.polisa_broj).replace("/", "_").replace("\\", "_"))
    if payload.agent_id:
        filename_parts.append(f"agent_{payload.agent_id}")
    return "_".join(filename_parts) + ".xlsx"


def _generate_multilevel_file(payload: MultilevelPreglediRequest) -> tuple[str, str]:
    has_period = _validate_multilevel_payload(payload)
    now = datetime.now()
    structure_year = payload.year if payload.year is not None else now.year
    structure_month = payload.month if payload.month is not None else now.month if structure_year == now.year else 12
    agent_structure_df = _fetch_agent_structure(structure_month, structure_year)

    df = _fetch_multilevel_provizija(
        payload.month,
        payload.year,
        payload.polisa_broj,
        payload.agent_id,
        payload.region_id,
        payload.team_id,
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="No data for selected filters.")

    naplata_df = _fetch_report_naplata(
        payload.month,
        payload.year,
        payload.polisa_broj,
        payload.agent_id,
        payload.region_id,
        payload.team_id,
    )
    dosegasni_bodovi_df = (
        _fetch_dosegasni_bodovi(payload.month, payload.year, payload.polisa_broj, payload.agent_id)
        if has_period
        else pd.DataFrame()
    )
    zbiren_df = _fetch_promotori_zbiren(
        payload.month,
        payload.year,
        payload.agent_id,
        payload.region_id,
        payload.team_id,
    ) if not payload.polisa_broj else pd.DataFrame()
    output = _build_multilevel_workbook(
        df,
        naplata_df,
        agent_structure_df,
        dosegasni_bodovi_df,
        zbiren_df,
        payload.month,
        payload.year
    )
    filename = _multilevel_filename(payload, has_period)
    file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}_{filename}")
    with open(file_path, "wb") as f:
        f.write(output.getvalue())
    return file_path, filename


def run_multilevel_job(job_id: str, payload: MultilevelPreglediRequest):
    try:
        _write_multilevel_job(job_id, {"status": "running", "message": "Running"})
        file_path, filename = _generate_multilevel_file(payload)
        _write_multilevel_job(job_id, {
            "status": "ready",
            "file_path": file_path,
            "filename": filename,
            "message": "OK",
        })
    except HTTPException as e:
        _write_multilevel_job(job_id, {
            "status": "error",
            "message": str(e.detail),
        })
    except Exception as e:
        _write_multilevel_job(job_id, {
            "status": "error",
            "message": str(e),
        })


@router.post("/api/multilevel-pregledi")
async def multilevel_pregledi(payload: MultilevelPreglediRequest, background_tasks: BackgroundTasks):
    try:
        _validate_multilevel_payload(payload)
        job_id = uuid.uuid4().hex
        _write_multilevel_job(job_id, {
            "status": "pending",
            "message": "Started",
            "file_path": None,
            "filename": None,
        })
        background_tasks.add_task(run_multilevel_job, job_id, payload)
        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "Multilevel export started.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating multilevel reports: {e}")


@router.get("/api/multilevel-pregledi/status/{job_id}")
async def multilevel_pregledi_status(job_id: str):
    job = _read_multilevel_job(job_id)
    if not job:
        return {"status": "unknown", "message": "No job found."}
    return {
        "status": job.get("status"),
        "message": job.get("message"),
        "filename": job.get("filename"),
    }


@router.get("/api/multilevel-pregledi/download/{job_id}")
async def multilevel_pregledi_download(job_id: str):
    job = _read_multilevel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="No job found.")
    if job.get("status") != "ready":
        raise HTTPException(status_code=409, detail="File is not ready yet.")
    file_path = job.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Generated file not found.")
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=job.get("filename") or "multilevel_pregledi.xlsx",
    )


@router.post("/api/multilevel-dashboard")
def multilevel_dashboard(payload: MultilevelPreglediRequest):
    try:
        _validate_multilevel_payload(payload)
        df = _fetch_multilevel_provizija(
            payload.month,
            payload.year,
            payload.polisa_broj,
            payload.agent_id,
            payload.region_id,
            payload.team_id,
            dashboard_only=True,
        )
        if df.empty:
            raise HTTPException(status_code=404, detail="No data for selected filters.")

        work = df.copy()
        work["_par_agentid"] = _series_text(work, "par_agentid")
        work["_agent_name"] = _series_text(work, "agent_name")
        work["_polisa_broj"] = _series_text(work, "polisa_broj")
        work["_faktura"] = _series_text(work, "faktura")
        work["_mesec"] = _series_text(work, "mesec")
        work["_nacin_provizija"] = _series_text(work, "nacin_provizija")
        work["_iznos_provizija"] = _series_num(work, "iznos_provizija")
        work["_br_bodovi"] = _series_num(work, "br_bodovi")
        work["_naplata"] = _series_num(work, "naplata")
        work["_naplata_fak"] = _series_num(work, "naplata_fak")
        work["_os_aneks_fakturaid"] = _series_text(work, "os_aneks_fakturaid")

        # The multilevel source repeats the same invoice for personal/team
        # commission rows. Count its collected premium only once per invoice.
        work["_invoice_key"] = work["_os_aneks_fakturaid"].where(
            work["_os_aneks_fakturaid"] != "",
            work["_faktura"].str.upper(),
        )
        invoice_rows = work[work["_invoice_key"] != ""].drop_duplicates("_invoice_key")
        naplata_total = float(invoice_rows["_naplata_fak"].sum())
        if not naplata_total:
            naplata_total = float(invoice_rows["_naplata"].sum())
        naplata_count = int(invoice_rows["_invoice_key"].nunique())

        total_commission = float(work["_iznos_provizija"].sum())
        policies_count = int(work["_polisa_broj"].nunique())
        agents_count = int(work["_par_agentid"].nunique())
        avg_premium = float(naplata_total / policies_count) if policies_count else 0

        all_agents_df = work.groupby(["_par_agentid", "_agent_name"], dropna=False).agg(
            policies=("_polisa_broj", "nunique"),
            commission=("_iznos_provizija", "sum"),
            points=("_br_bodovi", "sum"),
            naplata=("_naplata", "sum"),
        ).reset_index().sort_values("commission", ascending=False)
        top_agents = all_agents_df.head(10)

        commission_type = work.groupby("_nacin_provizija", dropna=False).agg(
            policies=("_polisa_broj", "nunique"),
            commission=("_iznos_provizija", "sum"),
            points=("_br_bodovi", "sum"),
        ).reset_index().rename(columns={"_nacin_provizija": "type"})

        monthly = work.groupby("_mesec", dropna=False).agg(
            policies=("_polisa_broj", "nunique"),
            commission=("_iznos_provizija", "sum"),
            points=("_br_bodovi", "sum"),
        ).reset_index().rename(columns={"_mesec": "month"}).sort_values("month")

        return {
            "filters": {
                "month": payload.month,
                "year": payload.year,
                "polisa_broj": payload.polisa_broj,
                "agent_id": payload.agent_id,
                "region_id": payload.region_id,
                "team_id": payload.team_id,
            },
            "kpis": {
                "policies": policies_count,
                "premium_collected": naplata_total,
                "commission_paid": total_commission,
                "average_premium": avg_premium,
                "agents": agents_count,
                "naplata_fakturi": naplata_count,
            },
            "top_agents": [
                {
                    "agent_id": str(r["_par_agentid"]),
                    "agent_name": str(r["_agent_name"]),
                    "policies": int(r["policies"]),
                    "commission": float(r["commission"]),
                    "points": float(r["points"]),
                }
                for _, r in top_agents.iterrows()
            ],
            "all_agents": [
                {
                    "agent_id": str(r["_par_agentid"]),
                    "agent_name": str(r["_agent_name"]),
                    "policies": int(r["policies"]),
                    "commission": float(r["commission"]),
                    "points": float(r["points"]),
                    "naplata": float(r["naplata"]),
                }
                for _, r in all_agents_df.iterrows()
            ],
            "commission_type": [
                {
                    "type": str(r["type"] or "N/A"),
                    "policies": int(r["policies"]),
                    "commission": float(r["commission"]),
                    "points": float(r["points"]),
                }
                for _, r in commission_type.iterrows()
            ],
            "monthly": [
                {
                    "month": str(r["month"]),
                    "policies": int(r["policies"]),
                    "commission": float(r["commission"]),
                    "points": float(r["points"]),
                }
                for _, r in monthly.iterrows()
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating multilevel dashboard: {e}")


def _clean_nan(rows: list[dict]) -> list[dict]:
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return rows


@router.post("/api/multilevel-nepresmetani-polisi")
def multilevel_nepresmetani_polisi(payload: MultilevelPreglediRequest, request: Request):
    """
    Naplateni fakturi (po pregled na fakturi za dadeniot mesec) za koi nema
    pronajdena presmetana provizija vo prov_promotori_tp_ex.
    """
    user = request.session.get("user", {})
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403)
    try:
        _validate_multilevel_payload(payload)
        df = _fetch_multilevel_provizija(
            payload.month,
            payload.year,
            payload.polisa_broj,
            payload.agent_id,
            payload.region_id,
            payload.team_id,
            dashboard_only=True,
        )
        naplata_df = _fetch_report_naplata(
            payload.month,
            payload.year,
            payload.polisa_broj,
            payload.agent_id,
            payload.region_id,
            payload.team_id,
        )
        work = _prep_sporedba_work(df)
        _, _, _, _, nepresmetani_fakturi = _compute_sporedba_fakturi(work, naplata_df)

        rows = _clean_nan(nepresmetani_fakturi.to_dict("records"))
        return {
            "success": True,
            "count": len(rows),
            "rows": rows,
            "vkupno_naplata": float(nepresmetani_fakturi["vk_iznos_p"].sum()) if not nepresmetani_fakturi.empty else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.post("/api/exportEksel")
async def export_eksel(payload: ExportEkselRequest):
    """
    Експортира Excel за даден месец и година (без агент).
    """
    try:
        status, msg, file_path = InkasoProvizijaAgent.export_eksel(payload.month, payload.year)
        if status != "OK":
            raise HTTPException(status_code=500, detail=msg)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Excel фајлот не е пронајден")

        return FileResponse(
            path=file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(file_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Непредвидена грешка: {e}")





@router.get("/api/export_agent_tree")
async def export_agent_tree(mesec: int = Query(..., ge=1, le=12), godina: int = Query(..., ge=2000)):
    try:
        sql = f"""
        SELECT
            vrati_agent_name(a.par_agentid) AS agent,
            vrati_agent_name(a.par_nadreden_agentid) AS nadreden_agent,
            a.par_agentid,
            a.par_nadreden_agentid,
            d.desc_mk AS Filijala,
            e.desc_mk AS Region,
            t.desc_mk AS Tim,
             pa.email,
             pa.par_status_aktiven,
             vrati_agent_pozicija (a.par_agentid, {mesec}, {godina} ) agent_novo 
        FROM par_agent_st a
        LEFT JOIN par_agent_pripadnost b ON a.par_agentid = b.par_agentid
         AND mdy({mesec}, 1, {godina}) BETWEEN b.datum_od AND nvl(b.datum_do, mdy(12,31,3000))
        LEFT JOIN par_regionu_filijala c ON b.par_regionu_filijalaid = c.par_regionu_filijalaid
        LEFT JOIN par_filijala d ON c.par_filijalaid = d.par_filijalaid
        LEFT JOIN par_regionu e ON c.par_regionuid = e.par_regionuid
        LEFT JOIN par_team t ON b.par_teamid = t.par_teamid
         join par_agent pa on a.par_agentid=pa.par_agentid 
        WHERE mdy({mesec}, 1, {godina}) BETWEEN pas_datumod AND nvl(pas_datumdo, mdy(12,31,3000))
       
        """

        print("Step 1: Querying database")
        rows, ok = fetch_query(sql)
        if not ok or rows is None:
            raise HTTPException(status_code=500, detail="Не може да се извлечат податоците.")

        columns = [
    "agent",
    "nadreden_agent",
    "par_agentid",
    "par_nadreden_agentid",
    "Filijala",
    "Region",
    "Tim",
    "Email",
    "Aktiven",
    "AgentNivo"
        ]       

        df = pd.DataFrame(rows, columns=columns)
        print("Step 2: Rows fetched:", len(df))
        if df.empty:
            raise HTTPException(status_code=404, detail="Нема податоци за овој месец и година.")

        # --- Build tree ---
        tree = defaultdict(list)
        for _, row in df.iterrows():
            tree[row["par_nadreden_agentid"]].append(row["par_agentid"])

        name_lookup = df.set_index("par_agentid")["agent"].to_dict()
        region_lookup = df.set_index("par_agentid")["Region"].to_dict()
        filijala_lookup = df.set_index("par_agentid")["Filijala"].to_dict()
        team_lookup = df.set_index("par_agentid")["Tim"].to_dict()
        email_lookup = df.set_index("par_agentid")["Email"].to_dict()
        aktiven_lookup = df.set_index("par_agentid")["Aktiven"].to_dict()
        nivo_lookup = df.set_index("par_agentid")["AgentNivo"].to_dict()


        def build_lines(agent_id, level=0):
            name = name_lookup.get(agent_id, "Unknown")
            region = region_lookup.get(agent_id, "")
            filijala = filijala_lookup.get(agent_id, "")
            team = team_lookup.get(agent_id, "")
            email = email_lookup.get(agent_id, "")
            aktiven = aktiven_lookup.get(agent_id, "")
            nivo = nivo_lookup.get(agent_id, "")


            # Arrows for visual tree
            arrow = "→" if level == 1 else "↳" if level > 1 else ""
            lines = [(arrow, level, name, region, filijala, team, email, aktiven, nivo)]
            for child in tree.get(agent_id, []):
                lines.extend(build_lines(child, level + 1))
            return lines

        roots = df[df["par_nadreden_agentid"].isna()]["par_agentid"].tolist()
        all_lines = []
        for root in roots:
            all_lines.extend(build_lines(root))

        df_tree = pd.DataFrame(
        all_lines,
        columns=["Arrow", "Level", "Agent", "Region", "Filijala", "Team", "Email", "Aktiven", "AgentNivo"]
        )

        print("Step 3: Tree built with", len(df_tree), "lines")

        # --- Write Excel with formatting ---
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_tree.to_excel(writer, index=False, sheet_name="AgentTree", columns=["Agent","Region","Filijala","Team","Email","Aktiven","AgentNivo"])
            workbook = writer.book
            worksheet = writer.sheets["AgentTree"]

            # Header formatting
            header_format = workbook.add_format({"bold": True, "bg_color": "#DCE6F1", "border": 1})
            for col_num, value in enumerate(["Agent","Region","Filijala","Team","Email","Aktiven","AgentNivo"]):
                worksheet.write(0, col_num, value, header_format)

            # Column widths
            worksheet.set_column(0, 0, 50)
            worksheet.set_column(1, 3, 20)

            # Row formatting: indentation, root highlighting, alternating colors
            for row_num, row in enumerate(df_tree.itertuples(), start=1):
                level = row.Level
                arrow = row.Arrow
                fmt_properties = {}

                # Indentation for hierarchy
                fmt_properties["indent"] = level

                # Root agents → green background + bold
                if level == 0:
                    fmt_properties["bg_color"] = "#C6EFCE"
                    fmt_properties["bold"] = True
                # Alternating row colors for readability
                elif row_num % 2 == 0:
                    fmt_properties["bg_color"] = "#F2F2F2"

                fmt = workbook.add_format(fmt_properties)
                worksheet.write(row_num, 0, f"{arrow} {row.Agent}" if arrow else row.Agent, fmt)
                worksheet.write(row_num, 1, row.Region, fmt)
                worksheet.write(row_num, 2, row.Filijala, fmt)
                worksheet.write(row_num, 3, row.Team, fmt)
                worksheet.write(row_num, 3, row.Team, fmt)
                worksheet.write(row_num, 4, row.Email, fmt)
                worksheet.write(row_num, 5, row.Aktiven, fmt)
                worksheet.write(row_num, 6, row.AgentNivo, fmt)


        buffer.seek(0)
        filename = f"Struktura_Agenti_{mesec}_{godina}.xlsx"
        print("Step 4: Excel generated")
        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        import traceback
        print("🔥 ERROR in /api/export_agent_tree")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Грешка при генерирање Excel: {str(e)}")
# ---------- Agent Tree JSON ----------
@router.get("/api/agent_tree_json")
async def agent_tree_json(mesec: int = Query(..., ge=1, le=12),
                          godina: int = Query(..., ge=2000)):
    """
    Return agent hierarchy as JSON suitable for D3 tree visualization.
    """
    try:
        # --- SQL to get agent info + hierarchy ---
        sql = f"""
        SELECT
            a.par_agentid,
            a.par_nadreden_agentid,
            vrati_agent_name(a.par_agentid) AS name,
            d.desc_mk AS Filijala,
            e.desc_mk AS Region,
            t.desc_mk AS Team
        FROM par_agent_st a
        LEFT JOIN par_agent_pripadnost b ON a.par_agentid = b.par_agentid
        LEFT JOIN par_regionu_filijala c ON b.par_regionu_filijalaid = c.par_regionu_filijalaid
        LEFT JOIN par_filijala d ON c.par_filijalaid = d.par_filijalaid
        LEFT JOIN par_regionu e ON c.par_regionuid = e.par_regionuid
        LEFT JOIN par_team t ON b.par_teamid = t.par_teamid
        WHERE mdy({mesec}, 1, {godina}) BETWEEN pas_datumod AND nvl(pas_datumdo, mdy(12,31,3000))
          AND mdy({mesec}, 1, {godina}) BETWEEN b.datum_od AND nvl(b.datum_do, mdy(12,31,3000))
        """

        rows, ok = fetch_query(sql)
        if not ok or rows is None:
            raise HTTPException(status_code=500, detail="Не може да се извлечат податоците.")

        df = pd.DataFrame(rows, columns=["par_agentid","par_nadreden_agentid","name","Filijala","Region","Team"])
        if df.empty:
            raise HTTPException(status_code=404, detail="Нема податоци за овој месец и година.")

        # --- Build tree dictionary ---
        tree_dict = {
            row.par_agentid: {
                "id": row.par_agentid,
                "name": row.name,
                "Filijala": row.Filijala,
                "Region": row.Region,
                "Team": row.Team,
                "children": []
            }
            for row in df.itertuples()
        }

        root_nodes = []

        for row in df.itertuples():
            parent_id = row.par_nadreden_agentid
            if parent_id and parent_id in tree_dict:
                tree_dict[parent_id]["children"].append(tree_dict[row.par_agentid])
            else:
                root_nodes.append(tree_dict[row.par_agentid])

        return root_nodes

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Грешка при генерирање структура: {str(e)}")



@router.post("/api/send_mail_broker")
def send_mail_broker_endpoint(req: MailRequest):
    """
    Endpoint to send broker mail with attachment for the given month and year.
    Example request body: {"month": 10, "year": 2025}
    """

    try:
        print("📩 RAW REQ:", req)
        print("📩 MONTH:", req.month)
        print("📩 YEAR:", req.year)
        print("📩 BROKER:", req.broker)
        
        month = req.month
        year = req.year
        broker=req.broker

        # Call your main logic function
        result = send_mail_broker(month, year,broker)

        # If your function returns a message or status, format it nicely
        if isinstance(result, dict):
            return result
        else:
            return {"status": "success", "message": str(result)}

    except Exception as e:
        # Log and return error response
        print(f"[send_mail_broker_endpoint] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Грешка при праќање мејл: {e}")



@router.post("/api/generate_excels")
async def api_generate_excels(request: Request):
    data = await request.json()
    month = int(data.get("month"))
    year = int(data.get("year"))
    broker = data.get("broker")  # може да биде None / null


    try:
        # 👉 Информативен лог / print дека процесот започнува
        print(f"🚀 Започнува генерирање на Excel фајлови за {month}/{year} ...")

        # 👉 Твоја функција што ги генерира
        result = generate_excels_broker(month, year, broker)

        if isinstance(result, dict) and not result.get("success", True):
            return JSONResponse(status_code=500, content=result)

        # 👉 По успешното завршување
        return {
            "success": True,
            "message": f"Excel фајловите се успешно генерирани за {month}/{year}",
            "download_url": f"/siglife-report/download_all_excels?month={month}&year={year}"
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"❌ Настана грешка при генерирање: {str(e)}"
            }
        )

# Патека каде се чуваат Excel фајловите по година/месец
BROKER_EXCEL_DIR = "/opt/siglife-reporting/broker_excels"


def _broker_excels_zip_response(month: int, year: int):
    folder_path = f"{BROKER_EXCEL_DIR}/{year}/{month}"

    if not os.path.exists(folder_path):
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": f"Папката {folder_path} не постои"}
        )

    zip_stream = io.BytesIO()
    added_files = 0
    with zipfile.ZipFile(zip_stream, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".xlsx"):
                zf.write(os.path.join(folder_path, file_name), arcname=file_name)
                added_files += 1

    if added_files == 0:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": f"Нема Excel фајлови во {folder_path}"}
        )

    zip_stream.seek(0)
    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=excels_{month}_{year}.zip"}
    )



@router.get("/download_all_excels")
def download_all_excels(month: int = Query(..., ge=1, le=12), year: int = Query(..., ge=2000)):
    return _broker_excels_zip_response(month, year)

@router.post("/api/prov_promotori")
async def start_prov_promotori(
    payload: ProvPromotoriRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Start long commission calculation.
    """
    mesec = payload.mesec
    godina = payload.godina

    # ако имаш auth можеш да го земеш user
    user_id = 6

    job_id = f"{mesec}_{godina}_{datetime.now().timestamp()}"

    prov_jobs[job_id] = {
        "status": "pending",
        "message": "Started"
    }

    background_tasks.add_task(
        run_prov_promotori_job,
        job_id,
        mesec,
        godina,
        user_id
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": "Пресметката започна во позадина."
    }

@router.get("/api/prov_promotori_status/{job_id}")
async def prov_promotori_status(job_id: str):
    job = prov_jobs.get(job_id)

    if not job:
        return {"status": "unknown"}

    return job


@router.get("/api/nepresmetani_polisi")
async def nepresmetani_polisi(
    mesec: str = Query(..., description="Месец 01-12"),
    godina: str = Query(..., description="Година 2017-2030"),
    request: Request = None
):
    user = request.session.get("user", {}) if request else {}
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403)

    try:
        from calendar import monthrange
        m = int(mesec)
        g = int(godina)
        last_day = monthrange(g, m)[1]
        mdy = f"MDY({m}, {last_day}, {g})"

        sql = f"""
            SELECT FIRST 500
                TRIM(p.polisa_broj_cel)                    AS polisa_broj,
                TRIM(a.ime) || ' ' || TRIM(a.prezime)      AS agent_ime,
                pa.par_agentid,
                COUNT(DISTINCT f.os_aneks_fakturaid)        AS br_fakturi,
                SUM(f.iznos_p)                              AS vkupno_naplata
            FROM   fin_stavka f
            JOIN   os_polisa p   ON p.os_polisaid   = f.os_polisaid
            JOIN   os_ponuda o   ON o.os_ponudaid   = p.os_ponudaid
            JOIN   provizija_agent pa
                   ON  pa.par_agentid = o.par_agentid
                   AND (pa.pag_datumdo IS NULL OR pa.pag_datumdo >= {mdy})
            JOIN   par_provizijadef  pd ON pd.par_provizijadefid = pa.par_provizijadefid
            JOIN   par_provizijatip  pt ON pt.par_provizijatipid = pd.par_provizijatipid
            JOIN   par_agent         a  ON a.par_agentid         = pa.par_agentid
            WHERE  f.iznos_p IS NOT NULL
              AND  f.par_tip_kniziid IN (285, 1128, 1567)
              AND  f.datum <= {mdy}
              AND  pt.tip_provizija = 'P'
              AND  f.os_aneks_fakturaid NOT IN (
                       SELECT ppp.os_aneks_fakturaid
                       FROM   provizija_promotori_presmetka ppp
                       WHERE  ppp.provizija_agentid = pa.par_provizija_agentid
                   )
              AND  (
                       SELECT nvl(SUM(fs2.iznos_p), 0)
                       FROM   fin_stavka fs2
                       WHERE  fs2.os_aneks_fakturaid = f.os_aneks_fakturaid
                         AND  fs2.datum <= {mdy}
                         AND  fs2.iznos_p IS NOT NULL
                   ) = (
                       SELECT nvl(SUM(fs3.iznos_d), 0)
                       FROM   fin_stavka fs3
                       WHERE  fs3.os_aneks_fakturaid = f.os_aneks_fakturaid
                         AND  fs3.iznos_d IS NOT NULL
                   )
            GROUP BY TRIM(p.polisa_broj_cel),
                     TRIM(a.ime), TRIM(a.prezime),
                     pa.par_agentid
            ORDER BY TRIM(a.ime), TRIM(p.polisa_broj_cel)
        """

        rows = []
        print("=== nepresmetani_polisi SQL ===")
        print(sql)
        print("=== END SQL ===")
        with informix_cursor() as cur:
            cur.execute(sql)
            cols = [d[0].lower() for d in cur.description]
            for row in cur.fetchall():
                item = dict(zip(cols, row))
                item["vkupno_naplata"] = float(item["vkupno_naplata"] or 0)
                rows.append(item)

        return {"success": True, "count": len(rows), "rows": rows}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


@router.get("/api/zosto_ne_presmetana")
async def zosto_ne_presmetana(
    polisa: str = Query(...),
    mesec: str = Query(...),
    godina: str = Query(...),
    agentid: int = Query(...),
    request: Request = None
):
    user = request.session.get("user", {}) if request else {}
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403)
    try:
        mesec_padded = mesec.zfill(2)
        polisa_safe = polisa.strip().replace("'", "''")
        sql = (
            f"EXECUTE FUNCTION vesna.diagnoza_provizija_agent("
            f"{int(agentid)},'{polisa_safe}','{mesec_padded}','{godina}')"
        )
        with informix_cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
        text = str(row[0]) if row and row[0] else "Нема резултат од дијагнозата."
        return {"success": True, "text": text}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


zbiren_jobs: dict = {}

def run_zbiren_pregled_job(job_id: str, mesec: str, godina: str, user_id: int):
    try:
        zbiren_jobs[job_id]["status"] = "running"
        from db_ifx import Informixdriver
        conn = Informixdriver()
        try:
            cur = conn.cursor()
            sql = f"EXECUTE FUNCTION vesna.presmetka_prov_agenti_zbiren_test('{mesec}','{godina}',{user_id})"
            cur.execute(sql)
            row = cur.fetchone()
            try:
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()
        status_code = int(row[0]) if row and row[0] is not None else -1
        message = str(row[1]) if row and row[1] is not None else ""
        if status_code == 1:
            zbiren_jobs[job_id]["status"] = "ready"
            zbiren_jobs[job_id]["message"] = message or "OK"
        else:
            zbiren_jobs[job_id]["status"] = "error"
            zbiren_jobs[job_id]["message"] = message or "Грешка во процедурата"
    except Exception as e:
        zbiren_jobs[job_id]["status"] = "error"
        zbiren_jobs[job_id]["message"] = str(e)


@router.post("/api/zbiren_pregled")
async def start_zbiren_pregled(
    payload: ProvPromotoriRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    user = request.session.get("user", {})
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403)

    mesec = payload.mesec.zfill(2)
    godina = payload.godina
    user_id = user.get("userid", 6)

    job_id = f"zbiren_{mesec}_{godina}_{datetime.now().timestamp()}"
    zbiren_jobs[job_id] = {"status": "pending", "message": "Started"}

    background_tasks.add_task(run_zbiren_pregled_job, job_id, mesec, godina, user_id)

    return {"success": True, "job_id": job_id, "message": "Збирниот преглед е стартуван..."}


@router.get("/api/zbiren_pregled_status/{job_id}")
async def zbiren_pregled_status(job_id: str, request: Request):
    user = request.session.get("user", {})
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403)
    job = zbiren_jobs.get(job_id)
    if not job:
        return {"status": "unknown"}
    return job


@router.post("/api/presmetaj_polisa")
async def presmetaj_polisa(
    request: Request,
    polisa: str = Query(...),
    mesec: str = Query(...),
    godina: str = Query(...)
):
    user = request.session.get("user", {})
    if not has_any_role(user, "admin", "provizia"):
        raise HTTPException(status_code=403)
    try:
        user_id = user.get("userid", 1)
        mesec_padded = mesec.zfill(2)
        polisa_safe = polisa.strip().replace("'", "''")
        sql = (
            f"EXECUTE FUNCTION vesna.presmetka_prov_promotori_polisa("
            f"'{mesec_padded}','{godina}','{polisa_safe}',{int(user_id)})"
        )

        from db_ifx import Informixdriver
        conn = Informixdriver()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            row = cur.fetchone()
            conn.commit()
        finally:
            conn.close()

        if row:
            status_code = int(row[0]) if row[0] is not None else -1
            message = str(row[1]) if row[1] is not None else ""
            return {"success": status_code == 1, "status_code": status_code, "message": message}
        return {"success": False, "message": "Нема резултат од функцијата"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

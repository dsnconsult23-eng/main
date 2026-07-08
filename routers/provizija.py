from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse,Response
from pydantic import BaseModel, Field
from datetime import datetime
from io import BytesIO
import os
import zipfile
import shutil
from typing import Optional

import InkasoProvizijaBroker
from routers import InkasoProvizijaAgent
import routers.Connection as Connection
from SendMailAgent import send_email_with_pdf, send_email_with_pdf_odg_lice
from services.pdf_service import GenerirajPdf
from routers.SendMailBroker import send_mail_broker,generate_excels_broker
import asyncio
import pandas as pd
from io import BytesIO
from collections import defaultdict
from pydantic import BaseModel
from fastapi import Request
import io



router = APIRouter()

# -----------------------------
#   Pydantic Models
# -----------------------------
# -------------------------------
# LONG commission jobs tracking
# -------------------------------
prov_jobs = {}

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
    ]


# ---------- Background PDF generation ----------

BASE_PATH = "/opt/siglife-reporting/Pregledi"

def run_pdf_job(month: str, year: int,
                team_id: Optional[int],
                region_id: Optional[int],
                agent_id: Optional[int]):
    """Heavy PDF generation in the background."""
    try:
        ok, rez = GenerirajPdf(
            mesec=month,
            godina=year,
            par_teamid=team_id,
            par_regionuid=region_id,
            par_agentid=agent_id,
            result_label=None
        )
        if not ok:
            print(f"PDF generation failed: {rez}")
    except Exception as e:
        print(f"PDF generation exception: {e}")

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
    background_tasks.add_task(run_pdf_job,
                              month, year,
                              payload.get("team_id"),
                              payload.get("region_id"),
                              payload.get("agent_id"))

    return {
        "success": True,
        "message": (
            f"Папката {target_folder} е избришана и креирана одново. "
            f"Генерирањето на PDF за {month}/{year} започна во позадина."
        ),
    }

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
            filename="Inkaso_broker.xlsx"
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

        # 👉 По успешното завршување
        return {
            "success": True,
            "message": f"Excel фајловите се успешно генерирани за {month}/{year}"
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



@router.get("/download_all_excels")
def download_all_excels(month: int = Query(..., ge=1, le=12), year: int = Query(..., ge=2000)):
    folder_path = f"/opt/siglife-reporting/broker_excels/{year}/{month}"
    
    if not os.path.exists(folder_path):
        return {"success": False, "message": f"Папката {folder_path} не постои"}

    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".xlsx"):
                zf.write(os.path.join(folder_path, file_name), arcname=file_name)

    zip_stream.seek(0)
    return StreamingResponse(
        zip_stream,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=excels_{month}_{year}.zip"}
    )

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
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from db_ifx import informix_cursor
import pandas as pd
from datetime import datetime
import math

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def format_date(date):
    if date is None:
        return '01.01.1900'
    if isinstance(date, str):
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            return dt.strftime("%d.%m.%Y")
        except:
            return '01.01.1900'
    if isinstance(date, datetime):
        return date.strftime("%d.%m.%Y")
    return '01.01.1900'

def to_mdy_parts(date_str):
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return dt.month, dt.day, dt.year
    except:
        return (1, 1, 1900)

def clean_value(value):
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    return value

@router.post("/ponudi/upload")
async def handle_upload(request: Request, file: UploadFile = File(...)):
    try:
        # ----------------------------------------------------------
        # 1)  Prevent duplicates – quick “SELECT COUNT(*) …” check
        # ----------------------------------------------------------
        with informix_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM ponudi_import WHERE filename = ?",
                (file.filename,)
            )
            (already_uploaded,) = cursor.fetchone()
            if already_uploaded:
                # Stop right here – tell the user the file exists.
                return templates.TemplateResponse(
                    "Ponuda.html",
                    {
                        "request": request,
                        "message": (
                            f"⚠️ Фајлот “{file.filename}” веќе бил внесен во базата."
                        ),
                    },
                )

        # ----------------------------------------------------------
        # 2)  Continue with normal processing if the name is unique
        # ----------------------------------------------------------

        contents = await file.read()
        df = pd.read_excel(pd.io.common.BytesIO(contents))
        df = df.where(pd.notnull(df), None)
        print(f"[DEBUG] DataFrame loaded with {len(df)} records")

        insert_sql = """
        INSERT INTO ponudi_import (
            rb, dogovoruvac_naziv, dog_embg, dog_grad, dog_adresa,
            osig_name, osig_embg, osig_grad, osig_adresa,
            prest_starost,
            adresa_izv, telefon, email, godini,
            skadenca_od, skadenca_do,
            osig_suma, premija, osig_suma_tbs, premija_tbs,
            korisnik_d_name, korisnik_d_embg, korisnik_s_name, srodstvo,
            agent, promotor, nacin_plakanje, rati, firma,filename
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, 
            ?, ?, ?, ?, 
            MDY(?, ?, ?), MDY(?, ?, ?),
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,?,?
        )
        """

        with informix_cursor() as cursor:
            for record in df.to_dict(orient='records'):
                try:
                    skadenca_od = to_mdy_parts(format_date(record.get("skadenca_od")))
                    skadenca_do = to_mdy_parts(format_date(record.get("skadenca_do")))
                    korisnik_datraganje = to_mdy_parts(format_date(record.get("korisnik_datraganje")))

                    values = (
                        
                        clean_value(record.get("rb")),
                        clean_value(record.get("dogovoruvac_naziv")),
                        clean_value(record.get("dog_embg")),
                        clean_value(record.get("dog_grad")),
                        clean_value(record.get("dog_adresa")),

                        clean_value(record.get("osig_name")),
                        clean_value(record.get("osig_embg")),
                        clean_value(record.get("osig_grad")),
                        clean_value(record.get("osig_adresa")),

                        clean_value(record.get("prest_starost")),
                        clean_value(record.get("adresa_izv")),
                        clean_value(record.get("telefon")),
                        clean_value(record.get("email")),
                        clean_value(record.get("godini")),

                        *skadenca_od,
                        *skadenca_do,

                        clean_value(record.get("osig_suma")),
                        clean_value(record.get("premija")),
                        clean_value(record.get("osig_suma_tbs")),
                        clean_value(record.get("premija_tbs")),

                        clean_value(record.get("korisnik_d_name")),
                        clean_value(record.get("korisnik_d_embg")),
                        clean_value(record.get("korisnik_s_name")),
                        clean_value(record.get("srodstvo")),

                        clean_value(record.get("agent")),
                        clean_value(record.get("promotor")),
                        clean_value(record.get("nacin_plakanje")),
                        clean_value(record.get("rati")),
                        clean_value(record.get("firma")),
                        clean_value(file.filename)
                    )

                    # Debug print in SQL style:
                    sql_preview = f"""
                    INSERT INTO ponudi_import (
                        rb, dogovoruvac_naziv, dog_embg, dog_grad, dog_adresa,
                        osig_name, osig_embg, osig_grad, osig_adresa,
                        prest_starost, adresa_izv, telefon, email, godini,
                        skadenca_od, skadenca_do, 
                        osig_suma, premija, osig_suma_tbs, premija_tbs,
                        korisnik_d_name, korisnik_d_embg, korisnik_s_name, srodstvo,
                        agent, promotor, nacin_plakanje, rati, firma,filename
                    ) VALUES (
                        {values[0]}, '{values[1]}', {values[2]}, '{values[3]}', '{values[4]}',
                        '{values[5]}', {values[6]}, '{values[7]}', '{values[8]}',
                        {values[9]}, '{values[10]}', '{values[11]}', '{values[12]}', {values[13]},
                        mdy({values[14]}, {values[15]}, {values[16]}),
                        mdy({values[17]}, {values[18]}, {values[19]}),
                        {values[20]}, {values[21]}, {values[22]}, {values[23]},
                        '{values[24]}', {values[25]}, '{values[26]}', '{values[27]}',
                        {values[28]}, {values[29]}, '{values[30]}', {values[31]}, '{values[32]}','{values[33]}'
                    );
                    """.strip()

                    print("[DEBUG] Final SQL preview:\n", sql_preview)
                    with open("ponudi_insert_log.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(sql_preview + "\n\n")


                    cursor.execute(sql_preview)

                except Exception as e:
                    print(f"[ERROR] Failed insert for record {record}: {e}")

        # ----------------------------------------------------------        
  # 3. Call stored procedure
            try:
                print(f"[DEBUG] Calling stored procedure generiraj_polisa_import for file {file.filename}")
                cursor.execute(
                    "call generiraj_polisa_import(?, ?, ?);",
                    (file.filename, 1, 6)  # Replace with actual TIP and user ID if needed
                )
            except Exception as e:
                print(f"[ERROR] Procedure call failed: {e}")
                return templates.TemplateResponse("Ponuda.html", {
                    "request": request,
                    "message": f"⚠️ Внесот успеа, но повикот на процедурата не успеа: {e}"
                })

        # Final success message
        return templates.TemplateResponse("Ponuda.html", {
            "request": request,
            "message": "✅ Податоците се успешно внесени и обработени."
        })

    except Exception as e:
        return templates.TemplateResponse("Ponuda.html", {
            "request": request,
            "message": f"❌ Настана грешка при внес: {e}"
        })
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
import pandas as pd
import datetime
from db_ifx import informix_cursor

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def split_mdy(val):
    if pd.isna(val) or val is None:
        return (None, None, None)
    if isinstance(val, pd.Timestamp) or isinstance(val, datetime.datetime):
        return val.month, val.day, val.year
    if isinstance(val, str):
        try:
            dt = pd.to_datetime(val, dayfirst=True)
            return dt.month, dt.day, dt.year
        except:
            return (None, None, None)
    return (None, None, None)


@router.post("/ponudi/upload")
async def handle_upload(request: Request, file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_excel(pd.io.common.BytesIO(contents))

        insert_query = """
        INSERT INTO ponudi_import (
            rb, dogovoruvac_naziv, dog_embg, dog_grad, dog_adresa,
            dog_datraganje,
            osig_name, osig_embg, osig_grad, osig_adresa,
            osig_datraganje, prest_starost,
            adresa_izv, telefon, email, godini,
            skadenca_od, skadenca_do, --korisnik_datraganje,
            osig_suma, premija, osig_suma_tbs, premija_tbs,
            korisnik_d_name, korisnik_d_embg, korisnik_s_name, srodstvo,
            agent, promotor, nacin_plakanje, rati, firma
        ) VALUES (
            ?, ?, ?, ?, ?,
            MDY(?, ?, ?),
            ?, ?, ?, ?,
            MDY(?, ?, ?), ?, ?, ?, ?,
            MDY(?, ?, ?), MDY(?, ?, ?), --MDY(?, ?, ?),
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?,?
        )
        """

        with informix_cursor() as cursor:
            for _, row in df.iterrows():
                values = row.tolist()

                dog_datraganje = split_mdy(values[5])
                osig_datraganje = split_mdy(values[10])
                skadenca_od = split_mdy(values[16])
                skadenca_do = split_mdy(values[17])
                #/korisnik_datraganje = split_mdy(values[18])

                new_values = []
                new_values.extend(values[:5])                   # rb → dog_adresa
                new_values.extend(dog_datraganje)               # MDY dog_datraganje
                new_values.extend(values[6:10])                 # osig_name → osig_adresa
                new_values.extend(osig_datraganje)              # MDY osig_datraganje
                new_values.extend(values[11:16])                # prest_starost → godini
                new_values.extend(skadenca_od)                  # MDY skadenca_od
                new_values.extend(skadenca_do)                  # MDY skadenca_do
                #new_values.extend(korisnik_datraganje)          # MDY korisnik_datraganje
                new_values.extend(values[19:])                  # остатокот до крај

                print("[DEBUG] Inserting:", new_values)
                print ("[DEBUG] Query:", insert_query)
                cursor.execute(insert_query, new_values)

        return templates.TemplateResponse("Ponuda.html", {
            "request": request,
            "message": "✅ Успешно внесување на податоците во базата."
        })

    except Exception as e:
        return templates.TemplateResponse("Ponuda.html", {
            "request": request,
            "message": f"❌ Настана грешка при внес: {e}"
        })

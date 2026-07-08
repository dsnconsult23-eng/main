# routers/ponudi_upload.py
from fastapi import APIRouter, Request, UploadFile, File, Response, HTTPException
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
import math

# 🔹 Informix connection
from db_ifx import informix_cursor

router = APIRouter(prefix="/ponudi", tags=["ponudi"])
templates = Jinja2Templates(directory="templates")

# ------------------------------
# CORE LOGIC (shared by HTML + SOAP)
# ------------------------------


# -------------------------------
# Helper functions
# -------------------------------
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


# -------------------------------
# Main function
# -------------------------------
# async def process_excel_file(request: Request, file_name: str, file_bytes: bytes):
#     try:
#         # Load Excel into DataFrame
#         df = pd.read_excel(pd.io.common.BytesIO(file_bytes))
#         df = df.where(pd.notnull(df), None)
#         print(f"[DEBUG] DataFrame loaded with {len(df)} records")

#         insert_sql = """
#         INSERT INTO ponudi_import (
#             rb, dogovoruvac_naziv, dog_embg, dog_grad, dog_adresa,
#             osig_name, osig_embg, osig_grad, osig_adresa,
#             prest_starost, adresa_izv, telefon, email, godini,
#             skadenca_od, skadenca_do,
#             osig_suma, premija, osig_suma_tbs, premija_tbs,
#             korisnik_d_name, korisnik_d_embg, korisnik_s_name, srodstvo,
#             agent, promotor, nacin_plakanje, rati, firma, filename,produkt
#         ) VALUES (
#             ?, ?, ?, ?, ?,
#             ?, ?, ?, ?,
#             ?, ?, ?, ?, ?,
#             MDY(?, ?, ?), MDY(?, ?, ?),
#             ?, ?, ?, ?,
#             ?, ?, ?, ?,
#             ?, ?, ?, ?, ?, ?,?
#         )
#         """

#         with informix_cursor() as cursor:
#             for record in df.to_dict(orient="records"):
#                 try:
#                     skadenca_od = to_mdy_parts(format_date(record.get("skadenca_od")))
#                     skadenca_do = to_mdy_parts(format_date(record.get("skadenca_do")))

#                     values = (
#                         clean_value(record.get("rb")),
#                         clean_value(record.get("dogovoruvac_naziv")),
#                         clean_value(record.get("dog_embg")),
#                         clean_value(record.get("dog_grad")),
#                         clean_value(record.get("dog_adresa")),

#                         clean_value(record.get("osig_name")),
#                         clean_value(record.get("osig_embg")),
#                         clean_value(record.get("osig_grad")),
#                         clean_value(record.get("osig_adresa")),

#                         clean_value(record.get("prest_starost")),
#                         clean_value(record.get("adresa_izv")),
#                         clean_value(record.get("telefon")),
#                         clean_value(record.get("email")),
#                         clean_value(record.get("godini")),

#                         *skadenca_od,
#                         *skadenca_do,

#                         clean_value(record.get("osig_suma")),
#                         clean_value(record.get("premija")),
#                         clean_value(record.get("osig_suma_tbs")),
#                         clean_value(record.get("premija_tbs")),

#                         clean_value(record.get("korisnik_d_name")),
#                         clean_value(record.get("korisnik_d_embg")),
#                         clean_value(record.get("korisnik_s_name")),
#                         clean_value(record.get("srodstvo")),

#                         clean_value(record.get("agent")),
#                         clean_value(record.get("promotor")),
#                         clean_value(record.get("nacin_plakanje")),
#                         clean_value(record.get("rati")),
#                         clean_value(record.get("firma")),
#                         clean_value(file_name),
#                          clean_value(record.get("produkt")),
                        
#                     )

#                     sql_preview = f"""
#                     INSERT INTO ponudi_import (
#                         rb, dogovoruvac_naziv, dog_embg, dog_grad, dog_adresa,
#                         osig_name, osig_embg, osig_grad, osig_adresa,
#                         prest_starost, adresa_izv, telefon, email, godini,
#                         skadenca_od, skadenca_do, 
#                         osig_suma, premija, osig_suma_tbs, premija_tbs,
#                         korisnik_d_name, korisnik_d_embg, korisnik_s_name, srodstvo,
#                         agent, promotor, nacin_plakanje, rati, firma,filename,produkt
#                     ) VALUES (
#                         {values[0]}, '{values[1]}', {values[2]}, '{values[3]}', '{values[4]}',
#                         '{values[5]}', {values[6]}, '{values[7]}', '{values[8]}',
#                         {values[9]}, '{values[10]}', '{values[11]}', '{values[12]}', {values[13]},
#                         mdy({values[14]}, {values[15]}, {values[16]}),
#                         mdy({values[17]}, {values[18]}, {values[19]}),
#                         {values[20]}, {values[21]}, {values[22]}, {values[23]},
#                         '{values[24]}', {values[25]}, '{values[26]}', '{values[27]}',
#                         {values[28]}, {values[29]}, '{values[30]}', {values[31]}, '{values[32]}','{values[33]}','{values[34]}'
#                     );
#                     """.strip()

#                     print("[DEBUG] Final SQL preview:\n", sql_preview)
#                     with open("ponudi_insert_log.txt", "a", encoding="utf-8") as log_file:
#                         log_file.write(sql_preview + "\n\n")


#                     cursor.execute(sql_preview)

#                 except Exception as e:
#                     print(f"[ERROR] Failed insert for record {record}: {e}")


#             # Call stored procedure after all inserts
#             try:
#                 print(f"[DEBUG] Calling stored procedure generiraj_polisa_import for file {file_name}")
#                 cursor.execute("CALL generiraj_polisa_import(?, ?, ?)", (file_name, 1, 6))
#             except Exception as e:
#                 print(f"[ERROR] Procedure call failed: {e}")
#                 return f"⚠️ Внесот успеа, но повикот на процедурата не успеа: {e}"

#         return "✅ Податоците се успешно внесени и обработени."

#     except Exception as e:
#         print(f"[ERROR] Unexpected: {e}")
#         return f"❌ Настана грешка при внес: {e}"

import pandas as pd
from io import BytesIO
from datetime import datetime, date

def process_excel_file(request: Request, file_name: str, file_bytes: bytes):
    def clean_value(v):
        if v is None:
            return None
        if isinstance(v, float) and pd.isna(v):
            return None
        if isinstance(v, str):
            v = v.strip()
            return v if v != "" else None
        return v

    def sql_literal(v):
        if v is None:
            return "NULL"

        # pandas / python numeric NaN
        try:
            if pd.isna(v):
                return "NULL"
        except Exception:
            pass

        # datetime/date
        if isinstance(v, (datetime, date)):
            return f"'{v.strftime('%Y-%m-%d')}'"

        # strings
        if isinstance(v, str):
            return "'" + v.replace("'", "''") + "'"

        return str(v)

    def parse_date_parts(value):
        """
        Vraka tuple (month, day, year) ili None
        Poddrzuva:
        - Excel datetime/date
        - string: 01.07.2025
        - string: 2025-07-01
        - string: 01/07/2025
        - string: 07/01/2025
        """
        if value is None:
            return None

        # pandas Timestamp / python datetime/date
        if isinstance(value, (datetime, date, pd.Timestamp)):
            return (value.month, value.day, value.year)

        # broj sto ne e validen datum
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass

        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None

            formats = [
                "%d.%m.%Y",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%d-%m-%Y",
            ]

            for fmt in formats:
                try:
                    d = datetime.strptime(value, fmt)
                    return (d.month, d.day, d.year)
                except ValueError:
                    continue

        return None

    def mdy_sql(value):
        parts = parse_date_parts(value)
        if not parts:
            return "NULL"
        return f"MDY({parts[0]}, {parts[1]}, {parts[2]})"

    try:
        df = pd.read_excel(BytesIO(file_bytes), dtype=object)
        df = df.where(pd.notnull(df), None)
        print(f"[DEBUG] DataFrame loaded with {len(df)} records")

        inserted_count = 0
        failed_count = 0

        with informix_cursor() as cursor:
            for i, record in enumerate(df.to_dict(orient="records"), start=1):
                try:
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
                        clean_value(file_name),
                        clean_value(record.get("produkt")),
                    )

                    sql_preview = f"""
INSERT INTO ponudi_import (
    rb, dogovoruvac_naziv, dog_embg, dog_grad, dog_adresa,
    osig_name, osig_embg, osig_grad, osig_adresa,
    prest_starost, adresa_izv, telefon, email, godini,
    skadenca_od, skadenca_do,
    osig_suma, premija, osig_suma_tbs, premija_tbs,
    korisnik_d_name, korisnik_d_embg, korisnik_s_name, srodstvo,
    agent, promotor, nacin_plakanje, rati, firma, filename, produkt
) VALUES (
    {sql_literal(values[0])}, {sql_literal(values[1])}, {sql_literal(values[2])}, {sql_literal(values[3])}, {sql_literal(values[4])},
    {sql_literal(values[5])}, {sql_literal(values[6])}, {sql_literal(values[7])}, {sql_literal(values[8])},
    {sql_literal(values[9])}, {sql_literal(values[10])}, {sql_literal(values[11])}, {sql_literal(values[12])}, {sql_literal(values[13])},
    {mdy_sql(record.get("skadenca_od"))},
    {mdy_sql(record.get("skadenca_do"))},
    {sql_literal(values[14])}, {sql_literal(values[15])}, {sql_literal(values[16])}, {sql_literal(values[17])},
    {sql_literal(values[18])}, {sql_literal(values[19])}, {sql_literal(values[20])}, {sql_literal(values[21])},
    {sql_literal(values[22])}, {sql_literal(values[23])}, {sql_literal(values[24])}, {sql_literal(values[25])}, {sql_literal(values[26])}, {sql_literal(values[27])}, {sql_literal(values[28])}
);
""".strip()

                    print("[DEBUG] Final SQL preview:\n", sql_preview)

                    with open("ponudi_insert_log.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(sql_preview + "\n\n")

                    cursor.execute(sql_preview)
                    inserted_count += 1

                except Exception as e:
                    failed_count += 1
                    print(f"[ERROR] Failed insert for row {i}: {e}")
                    print(f"[ERROR] Record data: {record}")

            try:
                print(f"[DEBUG] Calling stored procedure generiraj_polisa_import for file {file_name}")
                cursor.execute("CALL generiraj_polisa_import(?, ?, ?)", (file_name, 1, 6))
            except Exception as e:
                print(f"[ERROR] Procedure call failed: {e}")
                return (
                    f"⚠️ Внесени се {inserted_count} редови, "
                    f"неуспешни {failed_count}. "
                    f"Но повикот на процедурата не успеа: {e}"
                )

        return (
            f"✅ Податоците се успешно внесени и обработени. "
            f"Внесени: {inserted_count}, неуспешни: {failed_count}"
        )

    except Exception as e:
        print(f"[ERROR] Unexpected: {e}")
        return f"❌ Настана грешка при внес: {e}"
# ------------------------------
# HTML UPLOAD ENDPOINT
# ------------------------------
# @router.post("/upload")
# async def handle_upload(request: Request, file: UploadFile = File(...)):
#     contents = await file.read()
#     message = await process_excel_file(request, file.filename, contents)
#     return templates.TemplateResponse("Ponuda.html", {"request": request, "message": message})
from fastapi.concurrency import run_in_threadpool

@router.post("/upload")
async def handle_upload(request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    message = await run_in_threadpool(process_excel_file, request, file.filename, contents)
    return templates.TemplateResponse("Ponuda.html", {"request": request, "message": message})

# ------------------------------
# SOAP UPLOAD ENDPOINT
# ------------------------------
@router.post("/upload_soap")
async def handle_upload_soap(request: Request):
    # Check content type
    content_type = request.headers.get("Content-Type", "")
    if not content_type.startswith("text/xml"):
        fault = f"""<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Client</faultcode>
      <faultstring>Content-Type must be text/xml</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""
        return Response(content=fault, media_type="application/xml", status_code=400)
    
    body = await request.body()
    try:
        # Parse SOAP XML
        root = ET.fromstring(body.decode("utf-8"))
        ns = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "tns": "http://webservisiiute.siglife.mk/ponudi"
        }

        upload_req = root.find(".//tns:UploadRequest", ns)
        if upload_req is None:
            raise ValueError("UploadRequest element not found")
            
        file_name = upload_req.find("tns:fileName", ns).text
        file_content_b64 = upload_req.find("tns:fileContent", ns).text
        file_bytes = base64.b64decode(file_content_b64)

        # Process file
        message = await process_excel_file(request, file_name, file_bytes)

        # Build SOAP Response
        soap_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="http://webservisiiute.siglife.mk/ponudi">
  <soap:Body>
    <tns:UploadResponse>
      <status>{"OK" if "✅" in message else "ERROR"}</status>
      <message>{message}</message>
    </tns:UploadResponse>
  </soap:Body>
</soap:Envelope>
"""
        return Response(content=soap_response, media_type="text/xml")

    except Exception as e:
        fault = f"""<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Server</faultcode>
      <faultstring>{str(e)}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>"""
        return Response(content=fault, media_type="text/xml", status_code=500)


# ------------------------------
# WSDL ENDPOINT
# ------------------------------
@router.get("/upload.wsdl")
async def get_wsdl():
    wsdl_content = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns:tns="http://webservisiiute.siglife.mk/ponudi"
             xmlns:xsd="http://www.w3.org/2001/XMLSchema"
             name="PonudiService"
             targetNamespace="http://webservisiiute.siglife.mk/ponudi">

  <types>
    <xsd:schema targetNamespace="http://webservisiiute.siglife.mk/ponudi">
      <xsd:element name="UploadRequest">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="fileName" type="xsd:string"/>
            <xsd:element name="fileContent" type="xsd:base64Binary"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="UploadResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="status" type="xsd:string"/>
            <xsd:element name="message" type="xsd:string"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>

  <message name="UploadRequestMessage">
    <part name="parameters" element="tns:UploadRequest"/>
  </message>
  <message name="UploadResponseMessage">
    <part name="parameters" element="tns:UploadResponse"/>
  </message>

  <portType name="PonudiPortType">
    <operation name="Upload">
      <input message="tns:UploadRequestMessage"/>
      <output message="tns:UploadResponseMessage"/>
    </operation>
  </portType>

  <binding name="PonudiBinding" type="tns:PonudiPortType">
    <soap:binding style="document"
                  transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="Upload">
      <soap:operation soapAction="upload"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>

  <service name="PonudiService">
    <port name="PonudiPort" binding="tns:PonudiBinding">
      <soap:address location="https://webservisiiute.siglife.mk/siglife-report/ponudi/upload_soap"/>
    </port>
  </service>
</definitions>
"""
    return Response(content=wsdl_content, media_type="application/xml")


# ------------------------------
# HTML PAGE ENDPOINT - This will handle /siglife-report/Ponuda
# ------------------------------
@router.get("/Ponuda")
async def ponuda_page(request: Request):
    return templates.TemplateResponse("Ponuda.html", {"request": request, "message": None})


# ------------------------------
# REDIRECT FOR OLD URLS (if needed)
# ------------------------------
@router.get("/", include_in_schema=False)
async def redirect_ponudi():
    return RedirectResponse(url="/siglife-report/ponudi/Ponuda")
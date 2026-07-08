import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import routers.Connection as Connection

def fetch_xml_data_soap(formatted_date):
    """
    Fetches XML from SOAP service using POST with proper headers.
    """
    url = "https://feeds.mse.mk/service/FreeMSEFeeds.svc/fundunitvalue/XML/4a8ac71c-c340-4c38-9532-87bce8b9396a"
    
    # SOAP request body
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
   <soapenv:Header/>
   <soapenv:Body>
      <tem:GetFundUnitValue>
         <tem:date>{formatted_date}</tem:date>
      </tem:GetFundUnitValue>
   </soapenv:Body>
</soapenv:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "Accept": "text/xml"
    }

    response = requests.post(url, data=soap_body, headers=headers, verify=False)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch SOAP data, status code: {response.status_code}")

def parse_xml_data(xml_data):
    # Define namespaces
    namespaces = {
        "": "http://tempuri.org/",
        "a": "http://schemas.datacontract.org/2004/07/Entities",
    }
    root = ET.fromstring(xml_data)
    fund_unit_values = root.findall(".//a:FundUnitValue", namespaces=namespaces)
    parsed_data = []

    for fund in fund_unit_values:
        data = {
            "calculation_date": fund.find("a:CalculationDate", namespaces).text,
            "daily_avg_sale_price": float(fund.find("a:DailyAverageSalePrice", namespaces).text),
            "daily_buying_price": float(fund.find("a:DailyBuyingPrice", namespaces).text),
            "description_en": fund.find("a:DescriptionEN", namespaces).text,
            "description_mk": fund.find("a:DescriptionMK", namespaces).text,
            "last_daily_sale_price": float(fund.find("a:LastDailySalePrice", namespaces).text),
            "value_date": fund.find("a:ValueDate", namespaces).text,
        }
        parsed_data.append(data)
    return parsed_data

def insert_data_to_informix(data):
    sql = """
    INSERT INTO appuser.os_udel_upload
    (os_udel_uploadid, datecreated, usercreated, version, invrest_fond, cena_udel_mkd, 
     cena_udel_eur, datum, par_statusid, os_udel_uploadfileid) 
    values( sq_os_udel_upload.nextval, CURRENT, 'admin', 0, ?, ?, 
           ? / vrati_kurs(MDY(?, ?, ?), 'EUR'), MDY(?, ?, ?), 1, 1 )
    """
    results, OK = Connection.OSISinit()

    for record in data:
        try:
            raw_value_date = record["value_date"]
            value_date = datetime.strptime(raw_value_date.split("T")[0], "%Y-%m-%d").date()
            day, month, year = value_date.day, value_date.month, value_date.year

            results.execute(sql, (
                record["description_mk"],
                record["daily_buying_price"],
                record["daily_buying_price"],
                month, day, year,
                month, day, year,
            ))
            print(f"Inserted record for value_date: {value_date}")
        except Exception as e:
            print(f"Error inserting record: {e}")

def update_fund_data():
    results, OK = Connection.OSISinit()
    results.execute("select max(datum) from os_udel_upload")
    rez = results.fetchone()

    if rez and rez[0]:
        start_date = rez[0] if isinstance(rez[0], datetime.date) else datetime.strptime(rez[0], "%Y-%m-%d").date()
    else:
        start_date = datetime.now().date() - timedelta(days=1)

    end_date = datetime.now().date()
    current_date = start_date + timedelta(days=1)

    try:
        while current_date <= end_date:
            formatted_date = current_date.strftime("%Y%m%d")
            print("Processing date:", formatted_date)

            # Fetch SOAP XML data using POST
            xml_data = fetch_xml_data_soap(formatted_date)
            parsed_data = parse_xml_data(xml_data)

            # Insert into Informix
            insert_data_to_informix(parsed_data)

            current_date += timedelta(days=1)
        
        return {"message": "Data updated successfully"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

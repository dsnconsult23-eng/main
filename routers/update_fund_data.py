

from decimal import *
import time
import datetime
from datetime import date
from datetime import time
from datetime import datetime  
import locale,os
import platform
from datetime import datetime, timedelta
import routers.Connection  as Connection

#from flask import Flask, jsonify, request
import requests
import xml.etree.ElementTree as ET
import threading




# In[8]:




def fetch_xml_data(url):
    response = requests.get(url, verify=False)  # Disable SSL cert verification
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch data, status code: {response.status_code}")

def parse_xml_data(xml_data):
    # Define namespaces
    namespaces = {
        "": "http://tempuri.org/",
        "a": "http://schemas.datacontract.org/2004/07/Entities",
    }
    root = ET.fromstring(xml_data)

    # Locate the FundUnitValue nodes
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

	
def execute_stored_procedure(procedure_name, parameter):
    """
    Executes a stored procedure with a single parameter.
    
    :param procedure_name: The name of the stored procedure.
    :param parameter: The parameter to pass to the stored procedure.
    :return: The result of the stored procedure execution.
    """
    try:
        # Format the SQL call with the procedure name and parameter
        sql = f"{{call {procedure_name} ('{parameter}')}}"
        print("SQL procedure call:", sql)

        # Initialize database connection
        results, OK = Connection.OSISinit()
        
        # Execute the stored procedure
        results.execute(sql)
        rez = results.fetchone()

        print("Procedure result:", rez)
        return rez
    except Exception as e:
        print(f"Error executing stored procedure '{procedure_name}': {e}")
        return None



def insert_data_to_informix(data):
    # SQL Insert statement
    sql = """
    INSERT INTO appuser.os_udel_upload
    (os_udel_uploadid, datecreated, usercreated, version, invrest_fond, cena_udel_mkd, 
     cena_udel_eur, datum, par_statusid, os_udel_uploadfileid) 
    values( sq_os_udel_upload.nextval, CURRENT, 'admin', 0, ?, ?, 
           ? / vrati_kurs(MDY(?, ?, ?), 'EUR'), MDY(?, ?, ?), 1, 1 )
    """
    print (sql) 
    results, OK = Connection.OSISinit()

    for record in data:
        try:
            raw_value_date = record["value_date"]
            value_date = datetime.strptime(raw_value_date.split("T")[0], "%Y-%m-%d").date()
            # Convert value_date to string in dd/mm/yyyy format for display or logging
            value_date_display = value_date.strftime("%d/%m/%Y")  # For display or logging
            
            # Extract day, month, and year for MDY() function in Informix
            day = value_date.day
            month = value_date.month
            year = value_date.year

            # Print value_date in dd/mm/yyyy format for logging or display
            print(f"Value date for display (dd/mm/yyyy): {value_date_display}")

            # Execute the SQL statement for each record, using MDY() to pass date parts
            results.execute(sql, (
                record["description_mk"],                  # invrest_fond
                record["daily_buying_price"],              # cena_udel_mkd
                record["daily_buying_price"],              # cena_udel_eur numerator
                month,                                     # Pass month to MDY()
                day,                                       # Pass day to MDY()
                year,                                      # Pass year to MDY()
                month,                                     # Pass month again for datum
                day,                                       # Pass day again for datum
                year,                                      # Pass year again for datum
            ))
            print(f"Inserted record for value_date (display format): {value_date_display}")
        except Exception as e:
            print(f"Error inserting record: {e}")





def update_fund_data():
    sql = "select max(datum) from os_udel_upload" 
    print(sql)

    results, OK = Connection.OSISinit()
    results.execute(sql)    
    rez = results.fetchone()
    
    # Get the last date from the database
    if rez and rez[0]:
        if isinstance(rez[0], str):
            start_date = datetime.strptime(rez[0], "%Y-%m-%d").date()  # Adjust format if needed
        else:
            start_date = rez[0]  # Already a date object
    else:
        # Handle case where no date is returned
        start_date = datetime.now().date() - timedelta(days=1)
    print("Last date from database:", start_date)
    
    # Generate dates from the last date until today
    end_date = datetime.now().date()  # Today's date
    print("Today's date:", end_date)
    
    # Loop through each date from start_date to end_date
    current_date = start_date + timedelta(days=1)  # Start from the day after the last date
    try:
        while current_date <= end_date:
            # Format the date in YYYYMMDD
            formatted_date = current_date.strftime("%Y%m%d")
            print("Processing date:", formatted_date)
            
            # Construct the URL
            url = f"https://feeds.mse.mk/service/FreeMSEFeeds.svc/fundunitvalue/XML/4a8ac71c-c340-4c38-9532-87bce8b9396a/{formatted_date}"
            print("URL:", url)
            
            # Fetch and parse the XML data
            xml_data = fetch_xml_data(url)
            print("Fetched XML data successfully")
            parsed_data = parse_xml_data(xml_data)
            print ("Parsed XML data successfully:", parsed_data)
            # Insert the data into Informix
            insert_data_to_informix(parsed_data)
            print ("Inserted data into Informix successfully")
            
            # Move to the next date
            current_date += timedelta(days=1)
        
        return ({"message": "Data updated successfully"}), 200
    except Exception as e:
        return ({"error": str(e)}), 500





def update_fund_data_datum(tdatum):
    sql = "select max(datum) from os_udel_upload" 
    print(sql)

    results, OK = Connection.OSISinit()
    results.execute(sql)    
    rez = results.fetchone()
    
    # Get the last date from the database
    if rez and rez[0]:
        if isinstance(rez[0], str):
            start_date = datetime.strptime(rez[0], "%Y-%m-%d").date()  # Adjust format if needed
        else:
            start_date = rez[0]  # Already a date object
    else:
        # Handle case where no date is returned
        start_date = datetime.now().date() - timedelta(days=1)
    print("Last date from database:", start_date)
    
    # Generate dates from the last date until today
    end_date = datetime.now().date()  # Today's date
    print("Today's date:", end_date)
    
    # Loop through each date from start_date to end_date
    current_date = start_date + timedelta(days=1)  # Start from the day after the last date
    try:
        while current_date <= end_date:
            # Format the date in YYYYMMDD
            formatted_date = current_date.strftime("%Y%m%d")
            print("Processing date:", formatted_date)
            
            # Construct the URL
            url = f"https://feeds.mse.mk/service/FreeMSEFeeds.svc/fundunitvalue/XML/4a8ac71c-c340-4c38-9532-87bce8b9396a/{formatted_date}"
            print("URL:", url)
            
            # Fetch and parse the XML data
            xml_data = fetch_xml_data(url)
            parsed_data = parse_xml_data(xml_data)
            
            # Insert the data into Informix
            insert_data_to_informix(parsed_data)
            
            # Move to the next date
            current_date += timedelta(days=1)
        
        return ({"message": "Data updated successfully"}), 200
    except Exception as e:
        return ({"error": str(e)}), 500

# In[11]:
def scheduled_fund_update():
    print("Scheduled task running: update_fund_data()")
    try:
        update_fund_data()  # This will execute the same logic as your POST route
    except Exception as e:
        print(f"Error in scheduled update_fund_data: {e}")



import requests
import socket
import platform
import jaydebeapi
import platform,sys
import math
import os 
from os.path import basename
import locale
import routers.Connection  as Connection # absolute import
import re
from datetime import datetime

# Function to get local machine's IP address
def get_ip_address():
    try:
        return requests.get("https://api64.ipify.org?format=json").json()["ip"]
    except Exception as e:
        print("Could not get IP address:", e)
        return None

# Get the current IP address

current_ip = get_ip_address()
print("Current IP Address:", current_ip)

# Define user credentials based on IP (Example mapping)
ip_credentials = {
    "192.168.1.100": {"username": "User1", "password": "Pass1"},
    "192.168.1.101": {"username": "User2", "password": "Pass2"},
    "62.162.114.68": {"username": "CFjLdHb1", "password": "mf4Kb1tp"}  # Replace with actual external IP
}

credentials = ip_credentials.get(current_ip, {"username": "default_user", "password": "default_pass"})
url = "https://web2sms.akton.net/rest/send_sms"

import re
from datetime import datetime
import requests

def prebSMS(selected_option):
    # Set default credentials if IP is not mapped
    sql = f"""
    select  first 1  client_id, trim(client_naziv) client_naziv, 
    vrati_client_telefon(par_clientid), vrati_valutaid_polisa(os_polisaid) valutaid, 
    sum(iznos) - sum(naplata) dolg 
    from report_fakturi 
    where data_faktura < today 
    and dogovoruvac_prav_fiz = 'F'
    group by 1, 2, 3, 4
    having sum(iznos) - sum(naplata) > 1
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Грешка - нема врска со база")
        return OK, 0.0, "Грешка - нема врска со база"

    # Execute SQL query and fetch results
    results.execute(sql)
    podatoci = []

    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    if not podatoci:
        return True, [], "Нема податоци за испраќање"

    sent_count = 0

    for row in podatoci:
        client_id, client_naziv, phone_number, valutaid, dolg = row

        # Test phone number for debugging
        phone_number = "071-297860"
        #print(f"Testing with phone number: {phone_number}")

        # Skip if the phone number is empty or None
        if not phone_number:
            continue
        
        # Clean and format phone number
        cleaned_number = re.sub(r'\D', '', phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]

        # Create a personalized message
        if valutaid == 1:
            valuta = "EUR"
            if dolg < 2:
                continue
        else:
            valuta = "ден"
            if dolg < 100:
                continue

        today_date = datetime.today().strftime("%d.%m.%Y")
        message = (
            f"Почитуван/а {client_naziv}, вашиот доспеан долг кон Uniqa Life со состојба на {today_date} изнесува {dolg} {valuta}. Ве молиме да ја подмирите премијата."
        )

        # SMS API parameters
        params = {
            "from": "UniqaLife",
            "to": cleaned_number.strip(),
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"]
        }

        # Send GET request
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                sent_count += 1  # Increase counter only on successful response
            print(f"Sent to {cleaned_number}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Failed to send to {cleaned_number}: {e}")

    # Return message with SMS count
    return True, podatoci, f"Испратени се {sent_count} СМС пораки"

def prebSMSRodenden(selected_option):
    # Set default credentials if IP is not mapped
    sql = f"""
    select    par_clientid client_id, trim(desc) client_naziv, 
    vrati_client_telefon(par_clientid)  from par_client
    where client_tip_pf='F'
    and month(datumraganje)=MONTH(today)
    and day(datumraganje)=day(today)
    and nvl(edb,'')<>''
    and nvl(telefon,'')<>''
    """

    print(sql)
    results, OK = Connection.OSISinit()
    if not OK:
        print("Грешка - нема врска со база")
        return OK, 0.0, "Грешка - нема врска со база"

    # Execute SQL query and fetch results
    results.execute(sql)
    podatoci = []

    while True:
        row = results.fetchone()
        if not row:
            break
        podatoci.append(row)

    results.close()

    if not podatoci:
        return True, [], "Нема податоци за испраќање"

    sent_count = 0

    for row in podatoci:
        client_id, client_naziv, phone_number = row

        # Test phone number for debugging
        #phone_number = "071-297860"
        #print(f"Testing with phone number: {phone_number}")

        # Skip if the phone number is empty or None
        if not phone_number:
            continue
        
        # Clean and format phone number
        cleaned_number = re.sub(r'\D', '', phone_number)
        if cleaned_number.startswith("07"):
            cleaned_number = "389" + cleaned_number[1:]



        today_date = datetime.today().strftime("%d.%m.%Y")
        message = (
            f"Sreken rodenden! Neka sekoj nov den VI donese zdravje, radost i sigurnost na koja mozzete da se potprete. Vash UNIQA LIFE."
        )

        # SMS API parameters
        params = {
            "from": "UniqaLife",
            "to": cleaned_number.strip(),
            "message": message,
            "username": credentials["username"],
            "password": credentials["password"]
        }

        # Send GET request
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                sent_count += 1  # Increase counter only on successful response
            print(f"Sent to {cleaned_number}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Failed to send to {cleaned_number}: {e}")

    # Return message with SMS count
    return True, podatoci, f"Испратени се {sent_count} СМС пораки"


def scheduled_prebSMS():
    print("Scheduled: Sending prebSMS")
    prebSMS(None)

def scheduled_prebSMSRodenden():
    print("Scheduled: Sending prebSMSRodenden")
    prebSMSRodenden(None)



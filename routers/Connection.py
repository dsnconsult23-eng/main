
import jaydebeapi
from decimal import *
import datetime
from datetime import date, datetime, timedelta
import locale
import os
import platform

DB_HOST = os.getenv("IFX_HOST", "192.168.100.120")
DB_PORT = os.getenv("IFX_PORT", "5864")
DB_NAME = os.getenv("IFX_DB",   "uniqa_live")
DB_USER = os.getenv("IFX_USER", "appuser")
DB_PASS = os.getenv("IFX_PASS", "OxBm?Q(*)")

REPORTING_HOST = os.getenv("IFX_REPORTING_HOST", "192.168.100.143")
REPORTING_PORT = os.getenv("IFX_REPORTING_PORT", "1400")


def Informixdriver():
    if platform.system() == "Windows":
        base = r"C:\SigLifeReporting_Informix"
    else:
        base = "/opt/siglife-reporting"
    driver1 = os.path.join(base, "jdbc-4.50.4.1.jar")
    driver2 = os.path.join(base, "bson-4.2.0.jar")
    return driver1, driver2


def MSdriver():
    if platform.system() == "Windows":
        locale.setlocale(locale.LC_ALL, '')
        pth  = r"C:\SigLifeReporting_Informix\UCanAccess" + os.sep
        pth1 = pth + "lib" + os.sep
    else:
        pth  = "/opt/siglife-reporting/UCanAccess/"
        pth1 = pth + "lib/"

    # Driveri za MS-Access: https://ucanaccess.sourceforge.net/site.html
    ucanaccess_jars = [
        pth  + "ucanaccess-5.0.1.jar",
        pth1 + "commons-lang3-3.8.1.jar",
        pth1 + "commons-logging-1.2.jar",
        pth1 + "hsqldb-2.5.0.jar",
        pth1 + "jackcess-3.0.1.jar",
    ]

    sep = ";" if platform.system() == "Windows" else ":"
    return sep.join(ucanaccess_jars)


def OSISinit():
    driver1, driver2 = Informixdriver()
    driver3 = MSdriver()
    try:
        conn = jaydebeapi.connect(
            "com.informix.jdbc.IfxDriver",
            f"jdbc:informix-sqli://{DB_HOST}:{DB_PORT}/{DB_NAME}:DB_LOCALE=en_US.utf8",
            [DB_USER, DB_PASS],
            [driver1, driver2, driver3]
        )
        db = conn.cursor()
    except Exception as e:
        print(f"[Connection] OSISinit error: {e}")
        return "", False
    return db, True


def OSISinitConn():
    driver1, driver2 = Informixdriver()
    driver3 = MSdriver()
    try:
        conn = jaydebeapi.connect(
            "com.informix.jdbc.IfxDriver",
            f"jdbc:informix-sqli://{DB_HOST}:{DB_PORT}/{DB_NAME}:DB_LOCALE=en_US.utf8",
            [DB_USER, DB_PASS],
            [driver1, driver2, driver3]
        )
        db = conn.cursor()
    except Exception as e:
        print(f"[Connection] OSISinitConn error: {e}")
        return None, None, False
    return conn, db, True


def OSISinitReporting():
    driver1, driver2 = Informixdriver()
    driver3 = MSdriver()
    try:
        conn = jaydebeapi.connect(
            "com.informix.jdbc.IfxDriver",
            f"jdbc:informix-sqli://{REPORTING_HOST}:{REPORTING_PORT}/{DB_NAME}:DB_LOCALE=en_US.utf8",
            [DB_USER, DB_PASS],
            [driver1, driver2, driver3]
        )
        db = conn.cursor()
    except Exception as e:
        print(f"[Connection] OSISinitReporting error: {e}")
        return None, None, False
    return conn, db, True


    









import os
import platform
import jaydebeapi
from contextlib import contextmanager

# ---------- CONFIG ----------
DB_HOST = os.getenv("IFX_HOST", "192.168.100.120")
DB_PORT = os.getenv("IFX_PORT", "5864")
DB_NAME = os.getenv("IFX_DB",   "uniqa_live")
DB_USER = os.getenv("IFX_USER", "appuser")
DB_PASS = os.getenv("IFX_PASS", "OxBm?Q(*)")  # Or set this via environment
# -----------------------------

def _informix_jars():
    if platform.system() == "Windows":
        base = r"C:\\SigLifeReporting_Informix"
    else:
        base = "/"
    return [
        os.path.join(base, "jdbc-4.50.4.1.jar"),
        os.path.join(base, "bson-4.2.0.jar"),
    ]

def _ucanaccess_classpath():
    if platform.system() == "Windows":
        base = r"C:\SigLifeReporting_Informix\UCanAccess"
    else:
        base = "/UCanAccess"

    jars = [
        "ucanaccess-5.0.1.jar",
        "lib/commons-lang3-3.8.1.jar",
        "lib/commons-logging-1.2.jar",
        "lib/hsqldb-2.5.0.jar",
        "lib/jackcess-3.0.1.jar",
    ]

    return [os.path.join(base, j) for j in jars]


@contextmanager
def informix_cursor():
    if not DB_PASS:
        raise RuntimeError("Please set IFX_PASS environment variable.")

    url = f"jdbc:informix-sqli://{DB_HOST}:{DB_PORT}/{DB_NAME}:DB_LOCALE=en_US.utf8"
    jars = _informix_jars() + _ucanaccess_classpath()

    print("[DEBUG] JDBC URL:", url)
    print("[DEBUG] JARs:", jars)

    conn = jaydebeapi.connect("com.informix.jdbc.IfxDriver", url, [DB_USER, DB_PASS], jars)
    try:
        yield conn.cursor()
    finally:
        conn.close()
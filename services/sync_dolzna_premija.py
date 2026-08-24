import os
import sys
import time
import logging
from pathlib import Path

import paramiko
from routers.Connection import OSISinit


# =========================================================
# CONFIG
# =========================================================
SERVER_B_HOST = os.getenv("SERVER_B_HOST", "192.168.100.20")
SERVER_B_PORT = int(os.getenv("SERVER_B_PORT", "22"))
SERVER_B_USER = os.getenv("SERVER_B_USER", "root")
SERVER_B_PASSWORD = os.getenv("SERVER_B_PASSWORD", "Uniq@2023!")

REMOTE_UPLOAD_DIR = "/usr/seamApp/uploads"
OLD_PATH_PREFIX = "/opt/siglife-reporting/UNIQA/"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
LOG_FILE = os.getenv("SYNC_LOG_FILE", "/var/log/sync_dolzna_premija.log")

SFTP_RETRIES = int(os.getenv("SFTP_RETRIES", "3"))
SFTP_RETRY_DELAY = int(os.getenv("SFTP_RETRY_DELAY", "10"))


# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# =========================================================
# DB
# =========================================================
def get_cursor_and_connection():
    obj = OSISinit()

    if isinstance(obj, tuple):
        if len(obj) >= 2:
            first, second = obj[0], obj[1]

            if hasattr(first, "execute"):
                return first, None

            if hasattr(first, "cursor") and hasattr(second, "execute"):
                return second, first

    if hasattr(obj, "execute"):
        return obj, None

    if hasattr(obj, "cursor"):
        conn = obj
        return conn.cursor(), conn

    raise RuntimeError("OSISinit() did not return a usable cursor/connection")


def fetch_rows(cursor):
    sql = f"""
        SELECT FIRST {BATCH_SIZE}
               send_mail_dolzna_premijaid,
               TRIM(path) AS path
          FROM send_mail_dolzna_premija
         WHERE TRIM(path) LIKE '{OLD_PATH_PREFIX}%'
         ORDER BY send_mail_dolzna_premijaid
    """
    cursor.execute(sql)
    return cursor.fetchall()


def update_row(cursor, row_id, new_path):
    sql = """
        UPDATE send_mail_dolzna_premija
           SET path = ?
         WHERE send_mail_dolzna_premijaid = ?
    """
    cursor.execute(sql, (new_path, row_id))


# =========================================================
# SFTP
# =========================================================
def create_sftp():
    transport = paramiko.Transport((SERVER_B_HOST, SERVER_B_PORT))
    transport.connect(username=SERVER_B_USER, password=SERVER_B_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return transport, sftp


def close_sftp(transport, sftp):
    try:
        if sftp:
            sftp.close()
    except Exception:
        pass

    try:
        if transport:
            transport.close()
    except Exception:
        pass


def recreate_sftp():
    transport = None
    sftp = None

    for attempt in range(1, SFTP_RETRIES + 1):
        try:
            logger.info("Creating SFTP connection attempt %s/%s", attempt, SFTP_RETRIES)
            transport, sftp = create_sftp()
            logger.info("SFTP connection established to %s:%s", SERVER_B_HOST, SERVER_B_PORT)
            return transport, sftp
        except Exception as e:
            logger.error("SFTP connect failed on attempt %s: %s", attempt, str(e))
            close_sftp(transport, sftp)

            if attempt < SFTP_RETRIES:
                time.sleep(SFTP_RETRY_DELAY)
            else:
                raise


def ensure_remote_dir(sftp, remote_dir):
    parts = remote_dir.strip("/").split("/")
    current = ""

    for part in parts:
        current += "/" + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            logger.info("Creating remote directory: %s", current)
            sftp.mkdir(current)


def is_sftp_alive(transport, sftp):
    try:
        return (
            transport is not None and
            sftp is not None and
            transport.is_active()
        )
    except Exception:
        return False


def upload_file_with_retry(local_path: Path, remote_path: str, transport, sftp):
    for attempt in range(1, SFTP_RETRIES + 1):
        try:
            logger.info(
                "Uploading attempt %s/%s: %s -> %s",
                attempt, SFTP_RETRIES, local_path, remote_path
            )

            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            if not is_sftp_alive(transport, sftp):
                logger.warning("SFTP connection is not active. Reconnecting...")
                close_sftp(transport, sftp)
                transport, sftp = recreate_sftp()

            remote_dir = os.path.dirname(remote_path)
            ensure_remote_dir(sftp, remote_dir)

            sftp.put(str(local_path), remote_path)
            logger.info("Uploaded successfully: %s", remote_path)
            return transport, sftp

        except FileNotFoundError:
            logger.error("Local file NOT FOUND: %s", local_path)
            raise

        except Exception as e:
            logger.error(
                "Upload failed for %s on attempt %s: %s",
                remote_path, attempt, str(e)
            )

            close_sftp(transport, sftp)

            if attempt < SFTP_RETRIES:
                time.sleep(SFTP_RETRY_DELAY)
                transport, sftp = recreate_sftp()
            else:
                raise

    return transport, sftp


# =========================================================
# MAIN PROCESS
# =========================================================
def process():
    cursor, conn = get_cursor_and_connection()
    rows = fetch_rows(cursor)

    if not rows:
        logger.info("No rows found for processing.")
        return

    logger.info("Found %s rows.", len(rows))

    success_count = 0
    fail_count = 0
    skipped_count = 0

    transport = None
    sftp = None

    try:
        transport, sftp = recreate_sftp()

        for row in rows:
            row_id = row[0]
            old_path = (row[1] or "").strip()

            try:
                if not old_path:
                    skipped_count += 1
                    logger.warning("Skipping row %s because path is empty.", row_id)
                    continue

                local_file = Path(old_path)

                if not local_file.exists():
                    skipped_count += 1
                    logger.warning(
                        "Skipping row %s because local file does not exist: %s",
                        row_id,
                        old_path
                    )
                    continue

                filename = os.path.basename(old_path)
                new_path = f"{REMOTE_UPLOAD_DIR}/{filename}"

                transport, sftp = upload_file_with_retry(
                    local_file,
                    new_path,
                    transport,
                    sftp
                )

                update_row(cursor, row_id, new_path)

                if conn is not None:
                    conn.commit()

                success_count += 1
                logger.info("Updated row %s: %s -> %s", row_id, old_path, new_path)

            except FileNotFoundError as e:
                skipped_count += 1
                logger.warning("Skipping row %s: %s", row_id, str(e))

                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                continue

            except Exception as e:
                fail_count += 1
                logger.exception("Failed row %s: %s", row_id, str(e))

                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

    finally:
        close_sftp(transport, sftp)

    logger.info(
        "Done. Success=%s, Failed=%s, Skipped=%s",
        success_count, fail_count, skipped_count
    )


def scheduled_sync_dolzna_premija():
    logger.info("START scheduled_sync_dolzna_premija")
    process()
    logger.info("END scheduled_sync_dolzna_premija")


if __name__ == "__main__":
    process()
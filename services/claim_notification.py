import json
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from auth.smtp_config import load_smtp_config_once
from routers import Connection

_last_check: datetime = None
_CONFIG_FILE = Path(__file__).parent.parent / "data" / "claim_notify.json"


def _load_notify_emails() -> list[str]:
    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        return [e.strip() for e in data.get("emails", []) if e.strip()]
    except Exception as e:
        print(f"[CLAIM NOTIFY] Error loading config: {e}")
        return []


def save_notify_emails(emails: list[str]) -> bool:
    try:
        _CONFIG_FILE.write_text(
            json.dumps({"emails": [e.strip() for e in emails if e.strip()]}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return True
    except Exception as e:
        print(f"[CLAIM NOTIFY] Error saving config: {e}")
        return False


def _send_claim_email(smtp_cfg: dict, to_emails: list[str], claims: list[dict]):
    for claim in claims:
        ref        = claim.get("gacclaimid") or ""
        policy     = claim.get("policynumber") or ""
        claim_date = claim.get("claimdate")
        ctype      = claim.get("ctype") or ""
        desc       = claim.get("claimdescription") or ""
        place      = claim.get("claimplace_address") or ""
        country    = claim.get("claimplace_countrycode") or ""
        received   = claim.get("date_insert")

        if hasattr(claim_date, "strftime"):
            claim_date_str = claim_date.strftime("%d.%m.%Y")
        else:
            claim_date_str = str(claim_date or "").split(" ")[0]

        if hasattr(received, "strftime"):
            received_str = received.strftime("%d.%m.%Y %H:%M")
        else:
            received_str = str(received or "")

        place_full = f"{place.strip()}, {country.strip()}".strip(", ")

        subject = f"Нова пријава на штета – {ref} | Полиса {policy}"
        body = f"""\
Пристигна нова пријава на штета преку Иуте портал.

Референца (Иуте):   {ref}
Број на полиса:     {policy}
Датум на настан:    {claim_date_str}
Вид на штета:       {ctype}
Опис:               {desc}
Место:              {place_full}

Датум на прием:     {received_str}
"""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"]    = smtp_cfg["sender_email"]
        msg["To"]      = ", ".join(to_emails)
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_cfg["smtp_host"], smtp_cfg["smtp_port"]) as server:
                server.starttls()
                server.login(smtp_cfg["sender_username"], smtp_cfg["sender_password"])
                server.send_message(msg)
            print(f"[CLAIM NOTIFY] Email sent for {ref}")
        except Exception as e:
            print(f"[CLAIM NOTIFY] Email error for {ref}: {e}")


def check_new_claims():
    global _last_check

    since = _last_check if _last_check else (datetime.now() - timedelta(hours=24))
    now   = datetime.now()

    print(f"[CLAIM NOTIFY] Checking claims since {since}")

    to_emails = _load_notify_emails()
    if not to_emails:
        print("[CLAIM NOTIFY] No recipient emails configured — skipping")
        _last_check = now
        return

    cursor, OK = Connection.OSISinit()
    if not OK or cursor is None:
        print("[CLAIM NOTIFY] DB connection failed")
        return

    try:
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "SELECT gacclaimid, policynumber, claimdate, ctype, claimdescription, "
            "claimplace_countrycode, claimplace_address, date_insert "
            "FROM polisa_claim WHERE date_insert > ? ORDER BY date_insert ASC",
            [since_str]
        )
        rows = cursor.fetchall()
    except Exception as e:
        print(f"[CLAIM NOTIFY] SELECT error: {e}")
        _last_check = now
        return
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if not rows:
        print("[CLAIM NOTIFY] No new claims")
        _last_check = now
        return

    print(f"[CLAIM NOTIFY] Found {len(rows)} new claim(s)")

    claims = [
        {
            "gacclaimid":            r[0],
            "policynumber":          r[1],
            "claimdate":             r[2],
            "ctype":                 r[3],
            "claimdescription":      r[4],
            "claimplace_countrycode":r[5],
            "claimplace_address":    r[6],
            "date_insert":           r[7],
        }
        for r in rows
    ]

    try:
        smtp_cfg = load_smtp_config_once()
        _send_claim_email(smtp_cfg, to_emails, claims)
    except Exception as e:
        print(f"[CLAIM NOTIFY] SMTP config error: {e}")

    _last_check = now

from routers import Connection


def get_cursor_from_osis():
    print("[SMTP CONFIG] Opening OSIS connection for SMTP settings")
    obj, ok = Connection.OSISinit()
    if not ok:
        print("[SMTP CONFIG] OSIS connection failed")
        raise Exception("Error - no connection to the database")

    try:
        cur = obj.cursor()
        print("[SMTP CONFIG] OSIS returned connection object")
        return cur, obj
    except Exception:
        print("[SMTP CONFIG] OSIS returned cursor object")
        return obj, None


def get_smtp_settings():
    sql = "SELECT key, value FROM adm_appsettings WHERE key LIKE 'smtp.%'"

    print("[SMTP CONFIG] Loading smtp.% settings from adm_appsettings")
    cur, conn = get_cursor_from_osis()
    try:
        cur.execute(sql)
        settings = {}
        while True:
            row = cur.fetchone()
            if not row:
                break
            settings[str(row[0])] = row[1]
        safe_keys = ", ".join(sorted(settings.keys()))
        print(f"[SMTP CONFIG] Loaded keys: {safe_keys}")
        return settings
    finally:
        try:
            cur.close()
            print("[SMTP CONFIG] Cursor closed")
        except Exception:
            pass
        if conn:
            try:
                conn.close()
                print("[SMTP CONFIG] Connection closed")
            except Exception:
                pass


def load_smtp_config_once():
    settings = get_smtp_settings()

    sender_email = settings.get("smtp.fromaddress")
    sender_username = settings.get("smtp.username")
    sender_password = settings.get("smtp.password")

    if not sender_email or not sender_username or not sender_password:
        print(
            "[SMTP CONFIG] Missing credentials: "
            f"from={bool(sender_email)}, username={bool(sender_username)}, password={bool(sender_password)}"
        )
        raise Exception("Missing SMTP credentials (smtp.fromaddress / smtp.username / smtp.password)")

    config = {
        "sender_email": sender_email,
        "sender_username": sender_username,
        "sender_password": sender_password,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587
    }
    print(
        "[SMTP CONFIG] Using SMTP "
        f"host={config['smtp_host']} port={config['smtp_port']} "
        f"from={config['sender_email']} username={config['sender_username']} "
        f"password_set={bool(config['sender_password'])}"
    )
    return config

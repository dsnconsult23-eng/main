"""Daily scheduler task for refreshing replacement-policy relationships."""

from datetime import datetime

from routers import Connection


def scheduled_update_zamenska_polisa():
    started_at = datetime.now()
    conn, cursor, ok = Connection.OSISinitConn()
    if not ok or conn is None:
        print("[update_zamenska_polisa] ERROR: nema konekcija so bazata")
        return None

    try:
        jconn = getattr(conn, "jconn", None)
        if jconn is not None:
            jconn.setAutoCommit(False)

        # In a client call the SPL return value is read from the result set;
        # `INTO tempp` is used only inside Informix SPL code.
        cursor.execute("EXECUTE FUNCTION appuser.update_zamenska_polisa()")
        row = cursor.fetchone()
        tempp = row[0] if row else None
        conn.commit()
        elapsed = (datetime.now() - started_at).total_seconds()
        print(
            f"[update_zamenska_polisa] OK: tempp={tempp!r}, "
            f"vreme={elapsed:.2f}s"
        )
        return tempp
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[update_zamenska_polisa] ERROR: {exc}")
        return None
    finally:
        try:
            cursor.close()
        finally:
            conn.close()

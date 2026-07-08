
from routers import Connection


def map_user_row(row):
    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "full_name": row[3],
        "role_name": row[4],
        "is_active": int(row[5]),
        "created_at": row[6]
    }


def get_user_by_username(username: str):
    conn = None
    cur = None
    try:
        results, OK = Connection.OSISinit()
        if not OK:
            print("[AUTH] ❌ DB connection failed")
            return None

        cur = results

        cur.execute("""
            SELECT
                id,
                username,
                password_hash,
                full_name,
                role_name,
                is_active,
                created_at
            FROM polisa_users
            WHERE username = ?
        """, (username,))

        row = cur.fetchone()
        return map_user_row(row)

    finally:
        try:
            if cur:
                cur.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


def get_user_by_id(user_id: int):
    conn = None
    cur = None
    try:
        results, OK = Connection.OSISinit()
        if not OK:
            print("[AUTH] ❌ DB connection failed")
            return None

        cur = results

        cur.execute("""
            SELECT
                id,
                username,
                password_hash,
                full_name,
                role_name,
                is_active,
                created_at
            FROM polisa_users
            WHERE id = ?
        """, (user_id,))

        row = cur.fetchone()
        return map_user_row(row)

    finally:
        try:
            if cur:
                cur.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


def create_user(username: str, password_hash: str, full_name: str, role_name: str,
                is_active: int = 1, must_change_password: int = 1):
    results, OK = Connection.OSISinit()
    if not OK:
        print("[AUTH] ❌ DB connection failed")
        return False

    cur = results

    try:
        cur.execute("""
            INSERT INTO polisa_users
                (username, password_hash, full_name, role_name, is_active, must_change_password)
            VALUES
                (?, ?, ?, ?, ?, ?)
        """, (username, password_hash, full_name, role_name, is_active, must_change_password))

        try:
            cur.connection.commit()
        except:
            pass

        return True

    except Exception as e:
        print(f"[AUTH] ❌ create_user error: {e}")
        return False

    finally:
        try:
            cur.close()
        except:
            pass


def list_users():
    conn = None
    cur = None
    try:
        results, OK = Connection.OSISinit()
        if not OK:
            print("[AUTH] ❌ DB connection failed")
            return None

        cur = results

        cur.execute("""
            SELECT
                id,
                username,
                password_hash,
                full_name,
                role_name,
                is_active,
                created_at
            FROM polisa_users
            ORDER BY id
        """)

        rows = cur.fetchall()
        return [map_user_row(r) for r in rows]

    finally:
        try:
            if cur:
                cur.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

def get_user(username: str):
    user = get_user_by_username(username)
    if not user:
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "password_hash": user["password_hash"],
        "name": user["full_name"],
        "role": user["role_name"],
        "is_active": user["is_active"]
    }
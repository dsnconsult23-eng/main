
from db_ifx import informix_cursor
from auth.role_utils import normalize_roles


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
    try:
        with informix_cursor() as cur:
            cur.execute("""
                SELECT id, username, password_hash, full_name, role_name, is_active, created_at
                FROM polisa_users WHERE username = ?
            """, (username,))
            return map_user_row(cur.fetchone())
    except Exception as e:
        print(f"[AUTH] get_user_by_username error: {e}")
        return None


def get_user_by_id(user_id: int):
    try:
        with informix_cursor() as cur:
            cur.execute("""
                SELECT id, username, password_hash, full_name, role_name, is_active, created_at
                FROM polisa_users WHERE id = ?
            """, (user_id,))
            return map_user_row(cur.fetchone())
    except Exception as e:
        print(f"[AUTH] get_user_by_id error: {e}")
        return None


def create_user(username: str, password_hash: str, full_name: str, role_name: str,
                is_active: int = 1, must_change_password: int = 1):
    try:
        with informix_cursor() as cur:
            cur.execute("""
                INSERT INTO polisa_users
                    (username, password_hash, full_name, role_name, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, password_hash, full_name, role_name, is_active, must_change_password))

            return True
    except Exception as e:
        print(f"[AUTH] create_user error: {e}")
        return False


def update_user(user_id: int, full_name: str, role_name: str, is_active: int):
    try:
        with informix_cursor() as cur:
            cur.execute("""
                UPDATE polisa_users
                SET full_name = ?, role_name = ?, is_active = ?
                WHERE id = ?
            """, (full_name, role_name, is_active, user_id))

            return True
    except Exception as e:
        print(f"[AUTH] update_user error: {e}")
        return False


def update_password(user_id: int, new_hash: str) -> bool:
    try:
        with informix_cursor() as cur:
            cur.execute(
                "UPDATE polisa_users SET password_hash = ? WHERE id = ?",
                (new_hash, user_id)
            )

            return True
    except Exception as e:
        print(f"[AUTH] update_password error: {e}")
        return False


def list_users():
    try:
        with informix_cursor() as cur:
            cur.execute("""
                SELECT id, username, password_hash, full_name, role_name, is_active, created_at
                FROM polisa_users ORDER BY id
            """)
            return [map_user_row(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[AUTH] list_users error: {e}")
        return None


def get_user(username: str):
    user = get_user_by_username(username)
    if not user:
        return None

    roles = normalize_roles(user["role_name"])

    return {
        "id": user["id"],
        "username": user["username"],
        "password_hash": user["password_hash"],
        "name": user["full_name"],
        "role": roles[0] if roles else "",
        "roles": roles,
        "role_name": ",".join(roles),
        "is_active": user["is_active"]
    }

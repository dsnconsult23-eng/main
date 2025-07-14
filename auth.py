import hashlib
import binascii
from db_ifx import get_connection

def hash_password(password: str, salt: str) -> str:
    combo = password + salt
    h = hashlib.sha256(combo.encode('utf-8')).digest()
    return binascii.hexlify(h).decode().upper()

def verify_password(stored_hash: str, stored_salt: str, password_attempt: str) -> bool:
    return stored_hash == hash_password(password_attempt, stored_salt)

def get_user(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, passwordhash, passwordsalt, full_name, email, role "
        "FROM user_accounts WHERE username = ?", (username,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "passwordhash": row[2],
            "passwordsalt": row[3],
            "full_name": row[4],
            "email": row[5],
            "role": row[6]
        }
    return None

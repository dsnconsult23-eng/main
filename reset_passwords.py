from auth.auth_utils import get_password_hash
from auth.auth_repository import get_user_by_username, update_password

users = [
    ("aml_user",  "Uniq@2025!"),
    ("finance1",  "Finance123!"),
    ("izv_user",  "123456Izv"),
]

for username, password in users:
    user = get_user_by_username(username)
    if not user:
        print(f"[SKIP] {username} — не постои")
        continue
    ok = update_password(user["id"], get_password_hash(password))
    print(f"[{'OK' if ok else 'ERROR'}] {username}")

from auth.auth_utils import get_password_hash
from auth.auth_repository import create_user

password_hash = get_password_hash("Siglife123!")

create_user(
    username="admin",
    password_hash=password_hash,
    full_name="Admin Admin",
    role_name="admin",
    is_active=1
)

print("Admin user created.")
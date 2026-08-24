from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.auth_repository import get_user_by_username, get_user_by_id, create_user, list_users, update_user, update_password
from auth.auth_utils import get_password_hash
from auth.role_utils import ALLOWED_ROLES, ROLE_OPTIONS, normalize_roles, has_any_role
from auth.smtp_config import load_smtp_config_once

import os
import smtplib
import secrets
import string
from typing import List, Optional
from email.message import EmailMessage

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


def require_users_access(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    if not has_any_role(user, "users_create"):
        raise HTTPException(status_code=403, detail="Access denied")

    return user


def build_user_view(user_row):
    roles = normalize_roles(user_row.get("role_name"))
    item = dict(user_row)
    item["roles"] = roles
    item["roles_display"] = ", ".join(roles)
    return item


def generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits + "@#$%!"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_reset_password_email(to_email: str, full_name: str, username: str, password: str):
    smtp_cfg = load_smtp_config_once()
    msg = EmailMessage()
    msg["Subject"] = "SigLife Reporting - Ресетирана лозинка"
    msg["From"] = smtp_cfg["sender_email"]
    msg["To"] = to_email
    msg.set_content(f"""
Почитуван/а {full_name},

Побарано е ресетирање на лозинката за Вашиот корисник.

Линк за најава:
https://webservisiiute.siglife.mk/siglife-report/login

Username: {username}
Привремена лозинка: {password}

При следната најава ќе можете да ја промените лозинката.

Доколку не сте го побарале ресетирањето, игнорирајте го овој email.

Со почит,
SigLife IT
""")
    with smtplib.SMTP(smtp_cfg["smtp_host"], smtp_cfg["smtp_port"]) as server:
        server.starttls()
        server.login(smtp_cfg["sender_username"], smtp_cfg["sender_password"])
        server.send_message(msg)


def send_new_user_email(to_email: str, full_name: str, username: str, password: str):
    print(f"[NEW USER MAIL] Preparing mail for to={to_email} username={username}")
    smtp_cfg = load_smtp_config_once()

    msg = EmailMessage()
    msg["Subject"] = "SigLife Reporting - Кориснички податоци"
    msg["From"] = smtp_cfg["sender_email"]
    msg["To"] = to_email

    msg.set_content(f"""
Почитуван/а {full_name},

За Вас е креиран корисник за SigLife Reporting.

Линк за најава:
https://webservisiiute.siglife.mk/siglife-report/login

Username: {username}
Привремена лозинка: {password}

Со почит,
SigLife IT
""")

    print(
        "[NEW USER MAIL] Connecting SMTP "
        f"host={smtp_cfg['smtp_host']} port={smtp_cfg['smtp_port']} "
        f"from={smtp_cfg['sender_email']} user={smtp_cfg['sender_username']}"
    )
    with smtplib.SMTP(smtp_cfg["smtp_host"], smtp_cfg["smtp_port"]) as server:
        print("[NEW USER MAIL] SMTP connected, starting TLS")
        server.starttls()
        print("[NEW USER MAIL] TLS started, logging in")
        server.login(smtp_cfg["sender_username"], smtp_cfg["sender_password"])
        print("[NEW USER MAIL] Login OK, sending message")
        server.send_message(msg)
        print("[NEW USER MAIL] Message sent OK")


@router.get("/users/create")
async def create_user_form(request: Request):
    user = require_users_access(request)
    if isinstance(user, RedirectResponse):
        return user

    return templates.TemplateResponse(
        "create_user.html",
        {
            "request": request,
            "user": user,
            "active": "users_create",
            "role_options": ROLE_OPTIONS,
            "error": None,
            "success": None
        }
    )


@router.get("/users")
async def users_list(request: Request):
    user = require_users_access(request)
    if isinstance(user, RedirectResponse):
        return user

    rows = list_users() or []
    users = [build_user_view(row) for row in rows]

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "user": user,
            "active": "users",
            "users": users,
            "error": None,
            "success": "Корисникот е успешно ажуриран." if request.query_params.get("success") == "1" else None
        }
    )


@router.get("/users/{user_id}/edit")
async def edit_user_form(request: Request, user_id: int):
    admin_user = require_users_access(request)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    user_row = get_user_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        "edit_user.html",
        {
            "request": request,
            "user": admin_user,
            "active": "users",
            "edit_user": build_user_view(user_row),
            "role_options": ROLE_OPTIONS,
            "error": None,
            "success": None
        }
    )


@router.post("/users/{user_id}/edit")
async def edit_user_post(
    request: Request,
    user_id: int,
    full_name: str = Form(...),
    role_name: Optional[List[str]] = Form(None),
    is_active: str = Form("1")
):
    admin_user = require_users_access(request)
    if isinstance(admin_user, RedirectResponse):
        return admin_user

    user_row = get_user_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    full_name = full_name.strip()
    roles = normalize_roles(role_name)
    is_active_int = 1 if is_active == "1" else 0

    error = None
    if not full_name or not roles:
        error = "Име/презиме и најмалку една улога се задолжителни."

    invalid_roles = [role for role in roles if role not in ALLOWED_ROLES]
    if invalid_roles:
        error = f"Невалидна улога: {', '.join(invalid_roles)}"

    if error:
        current = build_user_view(user_row)
        current["full_name"] = full_name
        current["roles"] = roles
        current["is_active"] = is_active_int
        return templates.TemplateResponse(
            "edit_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users",
                "edit_user": current,
                "role_options": ROLE_OPTIONS,
                "error": error,
                "success": None
            }
        )

    ok = update_user(
        user_id=user_id,
        full_name=full_name,
        role_name=",".join(roles),
        is_active=is_active_int
    )

    if not ok:
        return templates.TemplateResponse(
            "edit_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users",
                "edit_user": build_user_view(user_row),
                "role_options": ROLE_OPTIONS,
                "error": "Грешка при снимање на корисникот.",
                "success": None
            }
        )

    if str(admin_user.get("id")) == str(user_id):
        admin_user["name"] = full_name
        admin_user["role"] = roles[0] if roles else ""
        admin_user["roles"] = roles
        request.session["user"] = admin_user

    return RedirectResponse(url="/siglife-report/users?success=1", status_code=303)


@router.post("/users/create")
async def create_user_post(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    role_name: Optional[List[str]] = Form(None),
    is_active: str = Form("1")
):
    admin_user = request.session.get("user")

    if not admin_user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    if not has_any_role(admin_user, "users_create"):
        raise HTTPException(status_code=403, detail="Access denied")

    username = username.strip().lower()
    full_name = full_name.strip()
    roles = normalize_roles(role_name)
    is_active_int = 1 if is_active == "1" else 0

    if not username or not full_name or not roles:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "role_options": ROLE_OPTIONS,
                "error": "Сите задолжителни полиња мора да бидат внесени.",
                "success": None
            }
        )

    invalid_roles = [role for role in roles if role not in ALLOWED_ROLES]
    if invalid_roles:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "role_options": ROLE_OPTIONS,
                "error": f"Невалидна улога: {', '.join(invalid_roles)}",
                "success": None
            }
        )

    role_name_value = ",".join(roles)

    existing_user = get_user_by_username(username)
    if existing_user:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "role_options": ROLE_OPTIONS,
                "error": "Корисничкото име веќе постои.",
                "success": None
            }
        )

    temp_password = generate_temp_password()

    ok = create_user(
        username=username,
        password_hash=get_password_hash(temp_password),
        full_name=full_name,
        role_name=role_name_value,
        is_active=is_active_int
    )

    if not ok:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "role_options": ROLE_OPTIONS,
                "error": "Грешка при снимање на корисникот.",
                "success": None
            }
        )

    try:
        send_new_user_email(
            to_email=username,
            full_name=full_name,
            username=username,
            password=temp_password
        )
    except Exception as e:
        print("[MAIL ERROR]", e)
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "role_options": ROLE_OPTIONS,
                "error": f"Корисникот е креиран, но mail не е испратен: {e}",
                "success": None
            }
        )

    return templates.TemplateResponse(
        "create_user.html",
        {
            "request": request,
            "user": admin_user,
            "active": "users_create",
            "role_options": ROLE_OPTIONS,
            "error": None,
            "success": f"Корисникот '{username}' е успешно креиран и му е испратен email."
        }
    )


@router.get("/forgot-password")
async def forgot_password_form(request: Request):
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "error": None, "success": None}
    )


@router.post("/forgot-password")
async def forgot_password_post(request: Request, username: str = Form(...)):
    _SAME_MSG = "Доколку корисникот постои, испратена е нова лозинка на вашата email адреса."

    username = username.strip().lower()
    user = get_user_by_username(username)

    if not user or int(user.get("is_active", 0)) != 1:
        return templates.TemplateResponse(
            "forgot_password.html",
            {"request": request, "error": None, "success": _SAME_MSG}
        )

    temp_password = generate_temp_password()
    update_password(user["id"], get_password_hash(temp_password))

    try:
        send_reset_password_email(
            to_email=username,
            full_name=user.get("full_name", ""),
            username=username,
            password=temp_password
        )
    except Exception as e:
        print(f"[FORGOT PASSWORD MAIL ERROR] {e}")

    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "error": None, "success": _SAME_MSG}
    )

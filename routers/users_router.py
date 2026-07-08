from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.auth_repository import get_user_by_username, create_user

import os
import smtplib
import secrets
import string
from email.message import EmailMessage

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))


def generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits + "@#$%!"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_new_user_email(to_email: str, full_name: str, username: str, password: str):
    smtp_host = "smtp.office365.com"
    smtp_port = 587

    # СМЕНИ ГИ ОВИЕ
    smtp_user = os.getenv("SMTP_USER", "noreply@siglife.mk")
    smtp_pass = os.getenv("SMTP_PASS", "YOUR_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = "SigLife Reporting - Кориснички податоци"
    msg["From"] = smtp_user
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

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


@router.get("/users/create")
async def create_user_form(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return templates.TemplateResponse(
        "create_user.html",
        {
            "request": request,
            "user": user,
            "active": "users_create",
            "error": None,
            "success": None
        }
    )


@router.post("/users/create")
async def create_user_post(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    role_name: str = Form(...),
    is_active: str = Form("1")
):
    admin_user = request.session.get("user")

    if not admin_user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    if admin_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    username = username.strip().lower()
    full_name = full_name.strip()
    role_name = role_name.strip()
    is_active_int = 1 if is_active == "1" else 0

    if not username or not full_name or not role_name:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "error": "Сите задолжителни полиња мора да бидат внесени.",
                "success": None
            }
        )

    existing_user = get_user_by_username(username)
    if existing_user:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
                "error": "Корисничкото име веќе постои.",
                "success": None
            }
        )

    temp_password = generate_temp_password()

    ok = create_user(
        username=username,
        password_hash=temp_password,   # моментално plain text
        full_name=full_name,
        role_name=role_name,
        is_active=is_active_int
    )

    if not ok:
        return templates.TemplateResponse(
            "create_user.html",
            {
                "request": request,
                "user": admin_user,
                "active": "users_create",
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
            "error": None,
            "success": f"Корисникот '{username}' е успешно креиран и му е испратен email."
        }
    )
from datetime import timedelta

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from auth.auth_utils import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/siglife-report/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None
        }
    )


@router.post("/siglife-report/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = authenticate_user(username, password)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Погрешно корисничко име или лозинка"
            }
        )

    access_token = create_access_token(
        data={
            "sub": user["username"],
            "user_id": user["id"],
            "role_name": user["role_name"]
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response = RedirectResponse(
        url="/siglife-report/dashboard",
        status_code=303
    )

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    return response


@router.get("/siglife-report/logout")
def logout():
    response = RedirectResponse(
        url="/siglife-report/login",
        status_code=303
    )
    response.delete_cookie("access_token", path="/")
    return response


@router.get("/siglife-report/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user
        }
    )
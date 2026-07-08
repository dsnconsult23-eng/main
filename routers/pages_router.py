from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from auth.auth_utils import get_current_user, require_roles

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/siglife-report/izvestuvanja", response_class=HTMLResponse)
def izvestuvanja_page(
    request: Request,
    current_user=Depends(require_roles(["admin", "notifications_admin"]))
):
    return templates.TemplateResponse(
        "izvestuvanja.html",
        {
            "request": request,
            "current_user": current_user
        }
    )


@router.get("/siglife-report/finansii", response_class=HTMLResponse)
def finansii_page(
    request: Request,
    current_user=Depends(require_roles(["admin", "finance"]))
):
    return templates.TemplateResponse(
        "finansii.html",
        {
            "request": request,
            "current_user": current_user
        }
    )
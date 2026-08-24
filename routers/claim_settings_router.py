from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from auth.role_utils import has_any_role
from services.claim_notification import _load_notify_emails, save_notify_emails
from fastapi import HTTPException
import os

router = APIRouter()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)


def _require_claim_access(request: Request):
    user = request.session.get("user")
    if not user:
        return None, RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, "claim_notify"):
        return None, RedirectResponse(url="/siglife-report/dashboard", status_code=303)
    return user, None


@router.get("/claim-notify-settings")
async def claim_notify_settings_form(request: Request):
    user, redirect = _require_claim_access(request)
    if redirect:
        return redirect

    emails = _load_notify_emails()
    return templates.TemplateResponse(
        "claim_notify_settings.html",
        {
            "request": request,
            "user": user,
            "active": "claim_notify",
            "emails": "\n".join(emails),
            "success": None,
            "error": None,
        }
    )


@router.post("/claim-notify-settings")
async def claim_notify_settings_save(request: Request, emails_input: str = Form(...)):
    user, redirect = _require_claim_access(request)
    if redirect:
        return redirect

    emails = [e.strip() for e in emails_input.replace(",", "\n").splitlines() if e.strip()]
    ok = save_notify_emails(emails)

    return templates.TemplateResponse(
        "claim_notify_settings.html",
        {
            "request": request,
            "user": user,
            "active": "claim_notify",
            "emails": "\n".join(emails),
            "success": "Адресите се зачувани." if ok else None,
            "error": None if ok else "Грешка при зачувување.",
        }
    )

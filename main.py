from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.staticfiles import StaticFiles

# Import routers
from routers.ponudi_upload import router as ponudi_router
from routers.MatematickaRezerva import router as matematicka_rezerva_router
from routers.REO import router as reo_router
#from routers.GeneratePDFIzvestuvanje import router as generate_pdf_router
#from routers.SendMailizvestuvanje import router as send_mail_router
from routers.provizija import router as provizia_router  # <- the fixed router

from routers.SMS import scheduled_prebSMSRodenden,scheduled_prebSMSPromenaIme
from routers.update_fund_data_soap import scheduled_fund_update
from routers.GeneratePDFIzvestuvanje import scheduled_generate_pdf
from routers.SendMailizvestuvanje import sendMailIzvestuvanje
from routers.SchedulerBackUp import scheduled_knizi_KO, scheduled_knizi_PO
from routers.aso_router import  router as aso_router  # Import the router module
from routers.SendMailBroker import router as broker_router
from routers.AML import router as AML_router
from routers.report_udel import router as report_udel_router
from routers.finansii import router as finansii_router
from routers.izvestuvanja import router as izvestuanja_router
from routers.users_router import router as users_router

# from routers.auth_router import router as auth_router
# from routers.pages_router import router as pages_router
from auth.auth_repository import get_user
import os
from datetime import datetime

# -----------------------------
# Main FastAPI app
# -----------------------------
app = FastAPI()

# -----------------------------
# Sub-application for /siglife-report
# -----------------------------
siglife_app = FastAPI(
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    title="SIGLife Reporting",
    description="Internal reporting system for SIGLife"
)

# Session middleware
SECRET_KEY = os.getenv("SIGLIFE_SECRET_KEY", "change_this_secret")
siglife_app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
siglife_app.mount("/static", StaticFiles(directory="static"), name="static")

# siglife_app.include_router(auth_router)
# siglife_app.include_router(pages_router)

# Include routers
siglife_app.include_router(ponudi_router)
siglife_app.include_router(matematicka_rezerva_router)
siglife_app.include_router(reo_router)
#siglife_app.include_router(generate_pdf_router)
#siglife_app.include_router(send_mail_router)
siglife_app.include_router(provizia_router)  # <-- Provizia endpoints
siglife_app.include_router(aso_router)  # Include the ASO router
siglife_app.include_router(broker_router)   # <-- BROKER EXCEL ENDPOINTS
siglife_app.include_router(AML_router)   # <-- AML ENDPOINTS
siglife_app.include_router(report_udel_router)
siglife_app.include_router(finansii_router)
siglife_app.include_router(izvestuanja_router)
siglife_app.include_router(users_router)
# print("=== LOADED ROUTES IN siglife_app ===")
# for r in siglife_app.routes:
#     print(" ->", r.path, r.methods)




# -----------------------------
# Background scheduler
# -----------------------------

ENABLE_SCHEDULER = True
scheduler = BackgroundScheduler(daemon=True)

if ENABLE_SCHEDULER:

    @app.on_event("startup")      # <-- attach to root app, not siglife_app
    def start_scheduler():
        scheduler.add_job(scheduled_prebSMSRodenden,trigger='cron', hour=11, minute=0, id='birthday_sms')
        scheduler.add_job(scheduled_fund_update,trigger='cron', hour=18, minute=35, id='scheduled_fund_update')
        scheduler.add_job(sendMailIzvestuvanje,trigger='cron',     hour='9,16',     minute='10,0', id='SendMailIzvestuvanje')
        #scheduler.add_job(scheduled_generate_pdf,trigger='cron', hour=9, minute=57, id='scheduled_generate_pdf')
        scheduler.add_job(scheduled_knizi_PO, trigger='cron', day=1, hour=18, minute=0, id='scheduled_knizi_po')
        scheduler.add_job(scheduled_knizi_KO, trigger='cron', day=1, hour=20, minute=30, id='scheduled_knizi_ko')
        # scheduler.add_job(scheduled_prebSMSPromenaIme,trigger='cron', hour=7, minute=40, id='birthday_promena_ime')
        scheduler.start()
        print("Scheduler started")

    @app.on_event("shutdown")     # <-- also root app
    def shutdown_scheduler():
        scheduler.shutdown()
        print("Scheduler shut down")

# -----------------------------
# Templates
# -----------------------------
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# -----------------------------
# Session dependency
# -----------------------------
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=303,
            detail="Redirect",
            headers={"Location": "/siglife-report/login"}
        )
    return user

# -----------------------------
# UI routes
# -----------------------------
@siglife_app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

# @siglife_app.post("/login")
# async def login(request: Request, username: str = Form(...), password: str = Form(...)):

#     # --- USER DATABASE (можеш да додаваш колку сакаш)
#     users = {
#         os.getenv("SIGLIFE_ADMIN_USER", "admin"): {
#             "password": os.getenv("SIGLIFE_ADMIN_PASS", "secret"),
#             "name": "Админ Админ",
#             "role": "Admin"
#         },
#         "aml_user": {
#             "password": "Uniq@2025!",
#             "name": "AML Корисник",
#             "role": "AML"
#         }
#     }

#     # --- CHECK LOGIN ---
#     if username not in users or password != users[username]["password"]:
#         return templates.TemplateResponse(
#             "login.html",
#             {"request": request, "error": "Invalid username or password"}
#         )

#     # --- SET SESSION ---
#     request.session["user"] = {
#         "Име и презиме": users[username]["name"],
#         "role": users[username]["role"]
#     }

#     return RedirectResponse(url="/siglife-report/dashboard", status_code=303)
@siglife_app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):

    user = get_user(username)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"}
        )

    if int(user["is_active"]) != 1:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "User disabled"}
        )

    # PRIVREMENO: plain password check
    if password != user["password_hash"]:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"}
        )

    # SESSION
    request.session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "name": user["name"],
        "role": user["role"]
    }

    return RedirectResponse(
        url="/siglife-report/dashboard",
        status_code=303
    )


@siglife_app.get("/dashboard")
async def dashboard(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@siglife_app.get("/provizia")
async def provizia(request: Request, user=Depends(get_current_user)):
    now = datetime.now()
    return templates.TemplateResponse(
        "provizia.html",
        {"request": request, "user": user, "current_month": str(now.month).zfill(2), "current_year": now.year}
    )


@siglife_app.get("/aso_reports")
async def aso_reports(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("aso_reports.html", {"request": request, "user": user})

@siglife_app.get("/Ponuda")
async def Ponuda(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("Ponuda.html", {"request": request, "user": user})

# @siglife_app.get("/logout")
# async def logout(request: Request):
#     request.session.clear()
#     return RedirectResponse(url="/siglife-report/login", status_code=303)

@siglife_app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(
        url="/siglife-report/login",
        status_code=303
    )

# -----------------------------
# Mount sub-application
# -----------------------------
app.mount("/siglife-report", siglife_app)

# -----------------------------
# Block root access
# -----------------------------
@app.get("/", include_in_schema=False)
async def block_root():
    raise HTTPException(status_code=404, detail="Use /siglife-report prefix")

@app.api_route("/{path:path}", methods=["GET", "POST"], include_in_schema=False)
async def block_all_root_paths():
    raise HTTPException(status_code=404, detail="Use /siglife-report prefix")

@siglife_app.get("/izvestuvanja")
async def izvestuvanja_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)

    if user["role"] not in ["admin", "izvestuvanja"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return templates.TemplateResponse(
        "izvestuvanja.html",
        {
            "request": request,
            "user": user,
            "active": "izvestuvanja"
        }
    )

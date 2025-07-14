from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse,HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from routers.ponudi_upload import router as ponudi_router
from routers.MatematickaRezerva import router as matematicka_rezerva_router
from routers.SMS import scheduled_prebSMS, scheduled_prebSMSRodenden
from apscheduler.schedulers.background import BackgroundScheduler
from routers.update_fund_data import scheduled_fund_update
from routers.GeneratePDFIzvestuvanje import scheduled_generate_pdf
from routers.SendMailizvestuvanje import sendMailIzvestuvanje


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.include_router(ponudi_router)
app.include_router(matematicka_rezerva_router)
scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    # Run every day at 11:00 AM server time
    #scheduler.add_job(scheduled_prebSMS, trigger='cron', hour=11, minute=0, id='daily_sms')
    scheduler.add_job(scheduled_prebSMSRodenden, trigger='cron', hour=11, minute=00, id='birthday_sms')
    scheduler.add_job(scheduled_fund_update, trigger='cron', hour=18, minute=30, id='scheduled_fund_update')
    scheduler.add_job(sendMailIzvestuvanje,trigger='cron',hour=12, minute=5, id='SendMailIzvestuvanje')
    scheduler.add_job(scheduled_generate_pdf,trigger='cron',hour=22, minute=47, id='scheduled_generate_pdf')
    scheduler.start()
    print("Scheduler started (11:00 AM daily)")

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    print("Scheduler shut down.")

templates = Jinja2Templates(directory="templates")

@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != "admin" or password != "secret":
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    
    request.session["user"] = {"Име и презиме ": "Админ Админ", "role": "Admin"}
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard")
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/provizia")
async def provizia(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("provizia.html", {"request": request, "user": user})

@app.get("/aso_reports")
async def aso_reports(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("aso_reports.html", {"request": request, "user": user})

@app.get("/Ponuda")
async def Ponuda(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("Ponuda.html", {"request": request, "user": user})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")




import logging
import os

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from services.mesh_service import MeshService, MeshServiceError
from auth.role_utils import has_any_role


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mesh", tags=["Mesh"])
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))
mesh_service = MeshService()


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/siglife-report/login", status_code=303)
    if not has_any_role(user, "mesh"):
        raise HTTPException(status_code=403, detail="Access denied")
    return user


def get_current_user_api(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not has_any_role(user, "mesh"):
        raise HTTPException(status_code=403, detail="Access denied")
    return user


def _raise_mesh_http_error(exc: Exception):
    if isinstance(exc, MeshServiceError):
        raise HTTPException(status_code=exc.status_code, detail=exc.public_message)
    raise HTTPException(status_code=500, detail="Unexpected Mesh integration error.")


@router.get("/", response_class=HTMLResponse)
async def mesh_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "mesh.html",
        {
            "request": request,
            "title": "Mesh / Compliance",
            "active": "mesh",
            "user": user
        }
    )

@router.get("/client")
async def get_client(user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_client_info)
    except Exception as e:
        logger.exception("Error loading Mesh client info")
        _raise_mesh_http_error(e)


@router.get("/customers")
async def get_customers(search: str = None, user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_customers, search)
    except Exception as e:
        logger.exception("Error loading Mesh customers")
        _raise_mesh_http_error(e)


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_customer, customer_id)
    except Exception as e:
        logger.exception("Error loading Mesh customer")
        _raise_mesh_http_error(e)


@router.get("/customers/{customer_id}/scores")
async def get_customer_scores(customer_id: str, user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_customer_scores, customer_id)
    except Exception as e:
        logger.exception("Error loading Mesh customer scores")
        _raise_mesh_http_error(e)


@router.get("/customers/{customer_id}/monitor")
async def get_customer_monitor(customer_id: str, user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_customer_monitor, customer_id)
    except Exception as e:
        logger.exception("Error loading Mesh customer monitor")
        _raise_mesh_http_error(e)


@router.get("/cases")
async def get_cases(user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_cases)
    except Exception as e:
        logger.exception("Error loading Mesh cases")
        _raise_mesh_http_error(e)


@router.post("/create-and-screen-sync")
async def create_and_screen_sync(request: Request, user=Depends(get_current_user_api)):
    try:
        payload = await request.json()
        return await run_in_threadpool(mesh_service.create_and_screen_sync, payload)
    except Exception as e:
        logger.exception("Error in create-and-screen-sync")
        _raise_mesh_http_error(e)


@router.post("/create-and-screen-async")
async def create_and_screen_async(request: Request, user=Depends(get_current_user_api)):
    try:
        payload = await request.json()
        return await run_in_threadpool(mesh_service.create_and_screen_async, payload)
    except Exception as e:
        logger.exception("Error in create-and-screen-async")
        _raise_mesh_http_error(e)


@router.get("/workflow/{workflow_id}")
async def workflow_status(workflow_id: str, user=Depends(get_current_user_api)):
    try:
        return await run_in_threadpool(mesh_service.get_workflow_status, workflow_id)
    except Exception as e:
        logger.exception("Error loading workflow status")
        _raise_mesh_http_error(e)


@router.post("/webhook/create")
async def create_webhook(request: Request, user=Depends(get_current_user_api)):
    try:
        payload = await request.json()
        return await run_in_threadpool(mesh_service.create_webhook, payload)
    except Exception as e:
        logger.exception("Error creating webhook")
        _raise_mesh_http_error(e)


@router.post("/webhook/test")
async def test_webhook(request: Request, user=Depends(get_current_user_api)):
    try:
        payload = await request.json()
        return await run_in_threadpool(mesh_service.test_webhook, payload)
    except Exception as e:
        logger.exception("Error testing webhook")
        _raise_mesh_http_error(e)

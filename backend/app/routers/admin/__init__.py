from fastapi import APIRouter

from app.routers.admin.tickets import router as tickets_router
from app.routers.admin.outages import router as outages_router
from app.routers.admin.technicians import router as technicians_router
from app.routers.admin.overview import router as overview_router

router = APIRouter()

router.include_router(overview_router)
router.include_router(tickets_router)
router.include_router(outages_router)
router.include_router(technicians_router)
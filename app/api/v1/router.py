from fastapi import APIRouter

from app.api.v1 import dashboard, fires, ingestion, simulations

api_router = APIRouter()

api_router.include_router(fires.router)
api_router.include_router(ingestion.router)
api_router.include_router(simulations.router)
api_router.include_router(dashboard.router)

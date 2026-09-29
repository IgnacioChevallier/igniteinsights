import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.db.session import engine

logging.basicConfig(level=settings.log_level.upper())
# httpx logs every request URL at INFO, and the FIRMS and OpenTopography keys travel in it.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting igniteinsights-api (env=%s)", settings.app_env)
    yield
    await engine.dispose()
    logger.info("igniteinsights-api shutdown complete")


app = FastAPI(
    title="IgniteInsights API",
    description=(
        "Backend API for the IgniteInsights wildfire prediction pipeline in "
        "Patagonia. The endpoints are organized around pipeline stages: checking "
        "service health, ingesting source datasets, reading stored fire detections, "
        "and eventually launching ELMFIRE simulations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


def _standard_response(status: str, data: Any = None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@app.get(
    "/health",
    summary="Check API and database health",
    description=(
        "Verifies that the API process is running and that it can open a connection "
        "to Postgres. Use this endpoint first when debugging the local stack. A "
        "`status` of `ok` means the API and database are connected; `degraded` means "
        "the API is up but the database check failed."
    ),
)
async def health() -> JSONResponse:
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("DB healthcheck failed: %s", exc)

    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content=_standard_response(
            status="ok" if db_ok else "degraded",
            data={"db": "connected" if db_ok else "unreachable"},
        ),
    )

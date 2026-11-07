"""Modo operativo: lo que ve el cliente y lo que el admin controla.

GET  /operativo/estado   — la vista del cliente (incendios activos y su último pronóstico)
PUT  /operativo          — admin: modo demo/vivo, reloj de la demo, mostrar el ensamble
POST /operativo/pasada   — admin: lleva el reloj de la demo a la pasada siguiente o anterior
POST /operativo/tick     — cron: un ciclo FIRMS → incendios → pronósticos, en segundo plano

La autorización vive en el frontend (frontend/middleware.ts): esta API no tiene dominio público
y sólo Next le habla, por la red privada. Ver docs/dashboard-producto.md.
"""
import asyncio
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import jobs
from app.db.session import async_session_factory
from app.dependencies import get_db
from app.operativo import servicio

router = APIRouter(prefix="/operativo", tags=["operativo"])

# Un tick por vez: el runner corre una sola simulación y dos ticks pronosticarían la misma pasada.
_tick_lock = asyncio.Lock()


def _envelope(status: str, data=None, error: dict | None = None) -> dict:
    return {
        "status": status,
        "data": data,
        "error": error,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.get(
    "/estado",
    summary="Estado del producto para la vista del cliente",
    description=(
        "El 'ahora' efectivo (el reloj congelado en modo demo), los incendios activos agrupados "
        "a 3 km con su último pronóstico ya disponible a esa hora, la última pasada VIIRS visible "
        "y la próxima estimada, y las detecciones de las últimas 24 h. Una pasada sólo cuenta "
        "cuando pasó la latencia de FIRMS (3 h)."
    ),
)
async def get_estado(session: AsyncSession = Depends(get_db)):
    return _envelope("success", await servicio.estado(session))


class OperativoUpdate(BaseModel):
    modo: Literal["demo", "vivo"] | None = None
    reloj: datetime | None = None
    calcular_ensamble: bool | None = None


@router.put("", summary="Cambiar el modo, el reloj de la demo o si se muestra el ensamble")
async def put_operativo(body: OperativoUpdate, session: AsyncSession = Depends(get_db)):
    op = await servicio.leer_operativo(session)
    if body.modo is not None:
        op.modo = body.modo
    if body.reloj is not None:
        op.reloj = body.reloj
    if body.calcular_ensamble is not None:
        op.calcular_ensamble = body.calcular_ensamble
    await session.commit()
    return _envelope("success", await servicio.estado(session))


@router.post("/pasada", summary="Llevar el reloj de la demo a la pasada siguiente o anterior")
async def post_pasada(
    direccion: Literal[1, -1] = Query(1),
    session: AsyncSession = Depends(get_db),
):
    op = await servicio.leer_operativo(session)
    if op.modo != "demo":
        raise HTTPException(status_code=409, detail="El reloj sólo se mueve en modo demo")
    destino = await servicio.pasadas_demo(session, direccion)
    if destino is None:
        raise HTTPException(status_code=404,
                            detail="No hay otra pasada pronosticada en esa dirección")
    op.reloj = destino
    await session.commit()
    return _envelope("success", await servicio.estado(session))


class TickRequest(BaseModel):
    # Sólo para precalcular una demo: un "ahora" pasado, sin bajar FIRMS (ya ingerido).
    ahora: datetime | None = None
    modo: Literal["demo", "vivo"] = "vivo"
    ingerir: bool = True
    # Filtro opcional para preparar o reparar el replay de una localidad específica.
    solo_localidad: str | None = None


@router.post(
    "/tick",
    summary="Un ciclo del modo en vivo (lo llama el cron en las ventanas de pasada)",
    description=(
        "Si el modo es demo y el pedido no es una precarga de la demo, no hace nada. Si no: baja "
        "FIRMS, agrupa los incendios activos y corre una ventana P-24 por cada pasada nueva. "
        "Responde enseguida con un job_id (GET /jobs/{id})."
    ),
)
async def post_tick(body: TickRequest | None = None):
    body = body or TickRequest()
    if _tick_lock.locked():
        return _envelope("success", {"omitido": "hay un tick en curso"})

    async def _run():
        async with _tick_lock, async_session_factory() as session:
            op = await servicio.leer_operativo(session)
            if body.modo == "vivo" and op.modo != "vivo":
                return {"omitido": "modo demo"}
            return {"pronosticos": await servicio.tick(session, body.ahora, body.modo,
                                                       body.ingerir, body.solo_localidad)}

    return _envelope("success", {"job_id": jobs.start(_run())})

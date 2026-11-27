"""Flujo de Prefect para leer placas. Sin probar todavia contra un servidor de Prefect.

Para ejecutarlo: pip install prefect; prefect server start; python -m apps.worker.flows
El API ya procesa la lectura en segundo plano por si misma (app/services/readings.py);
este flujo es la ruta de produccion con reintentos y trazabilidad.
"""
import uuid
from prefect import flow, task

from app.db import SessionLocal
from app.services.plate_reader import get_fallback_reader, get_reader
from app.services.readings import process_reading
from app.services.storage import get_storage


@task(retries=2, retry_delay_seconds=10)
def read_plate(asset_id: str, image_id: str):
    with SessionLocal() as db:
        r = process_reading(db, get_storage(), uuid.UUID(asset_id), uuid.UUID(image_id),
                            get_reader(), get_fallback_reader())
        return r.status.value


@flow(name="leer-placa")
def leer_placa(asset_id: str, image_id: str):
    return read_plate(asset_id, image_id)


@task(retries=1, retry_delay_seconds=15)
def avanzar_llamadas() -> dict:
    from app.services.call_results import tick
    from app.services.voice import get_voice
    with SessionLocal() as db:
        return tick(db, get_voice())


@flow(name="cotizar-agendar-tick")
def cotizar_agendar_tick():
    """Un paso: avanza busquedas de cotizaciones (oleadas, horario, reintentos, topes), citas por confirmar y recordatorios.
    Programarlo cada minuto: prefect deployment (cron '* * * * *'). Sin Prefect alojado, el mismo paso corre con `python -m admin.tick` en cron.
    Postgres es la verdad; este flujo solo empuja y es idempotente."""
    return avanzar_llamadas()

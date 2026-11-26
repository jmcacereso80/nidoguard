"""Preparar los cuidados de un equipo: lo usan la ruta manual y la tarea en segundo plano al confirmar el equipo."""
import logging
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import AssetEvent, AssetStatus, CareTask, EquipmentAsset
from .care_planner import MAX_TASKS, CarePlanner, first_due, get_planner

log = logging.getLogger("nidoguard.cuidados")


def today_mx() -> date:
    """Hoy en la Ciudad de Mexico (el servidor puede estar en otra zona)."""
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


class SinCuidados(Exception):
    """La IA no pudo proponer cuidados (error o respuesta vacia)."""


def generate_for_asset(db: Session, asset_id: uuid.UUID, planner: CarePlanner, hoy: date, actor_id: uuid.UUID | None = None) -> bool:
    """Crea los cuidados sugeridos si el equipo aun no tiene ninguno. Devuelve True si los creo.
    Es idempotente: bloquea la fila del equipo para que dos llamadas a la vez no dupliquen. Con error, no guarda nada."""
    a = db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == asset_id).with_for_update())
    if a is None or db.scalar(select(CareTask.id).where(CareTask.asset_id == a.id).limit(1)):
        db.rollback()
        return False
    try:
        plan = planner.plan(a.category, a.name, a.brand, a.model)
    except Exception as e:
        db.rollback()
        raise SinCuidados(str(e)) from e
    vistos: set[str] = set()
    for it in plan.tasks:
        clave = it.title.lower()
        if clave in vistos or len(vistos) >= MAX_TASKS:
            continue
        vistos.add(clave)
        db.add(CareTask(asset_id=a.id, organization_id=a.organization_id, title=it.title[:200], detail=it.detail[:300] or None,
                        instructions=it.instructions or None, every_n=it.every_n, every_unit=it.every_unit,
                        priority=it.priority, source="sugerencia", status="sugerida",
                        next_due=first_due(hoy, it.every_n, it.every_unit)))
    if not vistos:
        db.rollback()
        raise SinCuidados("La IA no propuso cuidados")
    db.add(AssetEvent(asset_id=a.id, organization_id=a.organization_id, type="cuidados_sugeridos", actor_id=actor_id,
                      payload={"cantidad": len(vistos), "modelo_ia": getattr(planner, "name", None)}))
    db.commit()
    return True


def prepare_in_background(asset_id: uuid.UUID) -> None:
    """Tarea en segundo plano al confirmar un equipo: si falla, no pasa nada; se reintenta al abrir la pestaña Cuidado."""
    db = SessionLocal()
    try:
        a = db.get(EquipmentAsset, asset_id)
        if a is None or a.status != AssetStatus.completo:  # solo equipos ya confirmados
            return
        generate_for_asset(db, asset_id, get_planner(), today_mx())
    except Exception:
        log.exception("No se pudieron preparar los cuidados del equipo %s", asset_id)
    finally:
        db.close()

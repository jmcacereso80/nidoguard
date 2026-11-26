"""Preparar los cuidados de un equipo: lo usan la ruta manual y la tarea en segundo plano al confirmar el equipo."""
import logging
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import AssetEvent, AssetStatus, CareTask, CareTemplate, EquipmentAsset
from .care_planner import MAX_TASKS, CareItem, CarePlan, CarePlanner, first_due, get_planner
from .manuales import norm

log = logging.getLogger("nidoguard.cuidados")


def today_mx() -> date:
    """Hoy en la Ciudad de Mexico (el servidor puede estar en otra zona)."""
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


class SinCuidados(Exception):
    """La IA no pudo proponer cuidados (error o respuesta vacia)."""


def template_key(a: EquipmentAsset) -> tuple[str, str] | None:
    """Clave del plan compartido: por marca y modelo si los hay; si no, por tipo de equipo. Sin ninguno de los dos no se comparte
    (el nombre que la persona le puso al equipo es suyo y nunca entra a la base compartida)."""
    if a.brand and a.model:
        return f"modelo|{norm(a.brand)}|{norm(a.model)}", "modelo"
    if a.category and norm(a.category):
        return f"tipo|{norm(a.category)}", "tipo"
    return None


def _items(plan: CarePlan) -> list[dict]:
    """Hasta MAX_TASKS cuidados, sin titulos repetidos."""
    vistos, out = set(), []
    for it in plan.tasks:
        clave = it.title.lower()
        if clave in vistos or len(out) >= MAX_TASKS:
            continue
        vistos.add(clave)
        out.append(it.model_dump())
    return out


def _template_for(db: Session, a: EquipmentAsset, planner: CarePlanner) -> tuple[list[dict], str]:
    """Devuelve (cuidados, origen). Aprende una sola vez por modelo (o tipo): si ya esta guardado, no llama a la IA."""
    k = template_key(a)
    if k is None:  # no se puede compartir: se genera solo para este equipo
        return _items(_plan(planner, a)), "sugerencia"
    key, kind = k
    # Un candado por clave: si dos equipos del mismo modelo se confirman a la vez, la IA se llama una sola vez.
    db.execute(text("select pg_advisory_xact_lock(hashtext(:k))"), {"k": key})
    t = db.scalar(select(CareTemplate).where(CareTemplate.key == key))
    if t is None:
        items = _items(_plan(planner, a, compartido=True))
        t = CareTemplate(key=key, kind=kind, category=a.category, items=items, planner=getattr(planner, "name", None), uses=0)
        if kind == "modelo":
            t.brand, t.model = a.brand.strip(), a.model.strip()
        db.add(t)
    t.uses += 1
    return list(t.items), t.source


def _plan(planner: CarePlanner, a: EquipmentAsset, compartido: bool = False) -> CarePlan:
    try:
        # En un plan compartido la IA no recibe el nombre que puso la persona.
        nombre = (a.category or "equipo") if compartido else a.name
        plan = planner.plan(a.category, nombre, a.brand, a.model)
    except Exception as e:
        raise SinCuidados(str(e)) from e
    if not plan.tasks:
        raise SinCuidados("La IA no propuso cuidados")
    return plan


def generate_for_asset(db: Session, asset_id: uuid.UUID, planner: CarePlanner, hoy: date, actor_id: uuid.UUID | None = None) -> bool:
    """Crea los cuidados sugeridos si el equipo aun no tiene ninguno. Devuelve True si los creo.
    Usa el plan ya aprendido de su modelo (o tipo) y solo llama a la IA si es la primera vez.
    Es idempotente: bloquea la fila del equipo para que dos llamadas a la vez no dupliquen. Con error, no guarda nada."""
    a = db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == asset_id).with_for_update())
    if a is None or db.scalar(select(CareTask.id).where(CareTask.asset_id == a.id).limit(1)):
        db.rollback()
        return False
    try:
        items, source = _template_for(db, a, planner)
    except SinCuidados:
        db.rollback()
        raise
    for it in items:
        it = CareItem.model_validate(it)
        db.add(CareTask(asset_id=a.id, organization_id=a.organization_id, title=it.title[:200], detail=it.detail[:300] or None,
                        instructions=it.instructions or None, every_n=it.every_n, every_unit=it.every_unit,
                        priority=it.priority, source=source, status="sugerida",
                        next_due=first_due(hoy, it.every_n, it.every_unit)))
    db.add(AssetEvent(asset_id=a.id, organization_id=a.organization_id, type="cuidados_sugeridos", actor_id=actor_id,
                      payload={"cantidad": len(items), "origen": source, "plan_compartido": template_key(a) is not None}))
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

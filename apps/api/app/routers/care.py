"""Cuidados recurrentes de cada equipo: generar, ver, marcar como realizados, reprogramar, confirmar o descartar."""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AssetStatus, CareRecord, CareTask, EquipmentAsset, Organization, Space, User
from ..security import current_org, current_user
from ..services.care_planner import MAX_TASKS, CarePlanner, add_every, first_due, get_planner
from .assets import _event, _own

log = logging.getLogger(__name__)
router = APIRouter(tags=["cuidados"])


def today_mx() -> date:
    """Hoy en la Ciudad de Mexico (el servidor puede estar en otra zona)."""
    return datetime.now(ZoneInfo("America/Mexico_City")).date()


class DoneIn(BaseModel):
    done_on: date | None = None


class RescheduleIn(BaseModel):
    next_due: date


def _task_out(t: CareTask) -> dict:
    return {
        "id": str(t.id), "title": t.title, "detail": t.detail, "instructions": t.instructions,
        "every": {"n": t.every_n, "unit": t.every_unit}, "priority": t.priority,
        "source": t.source, "confirmed": t.status == "confirmada",
        "next_due": t.next_due.isoformat(),
        "done_at": t.last_done_at.date().isoformat() if t.last_done_at else None,
    }


def _tasks(db: Session, asset_id: uuid.UUID) -> list[CareTask]:
    return list(db.scalars(select(CareTask).where(CareTask.asset_id == asset_id, CareTask.status != "descartada")
                           .order_by(CareTask.next_due, CareTask.title)))


def _care_out(a: EquipmentAsset, tasks: list[CareTask]) -> dict:
    # El plan del modelo solo se da por firme cuando marca y modelo estan confirmados (Q-015).
    return {"model_confirmed": a.status == AssetStatus.completo and bool(a.model), "tasks": [_task_out(t) for t in tasks]}


def _task(db: Session, org: Organization, task_id: uuid.UUID) -> CareTask:
    t = db.scalar(select(CareTask).where(CareTask.id == task_id, CareTask.organization_id == org.id,
                                         CareTask.status != "descartada"))
    if not t:
        raise HTTPException(404, "No encontramos ese cuidado.")
    return t


@router.get("/assets/{asset_id}/care")
def get_care(asset_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    a = _own(db, org, asset_id)
    return _care_out(a, _tasks(db, a.id))


@router.post("/assets/{asset_id}/care/generate")
def generate_care(asset_id: uuid.UUID, user: User = Depends(current_user), org: Organization = Depends(current_org),
                  db: Session = Depends(get_db), planner: CarePlanner = Depends(get_planner)):
    """Prepara los cuidados del equipo. Es idempotente: si ya tiene cuidados (aunque haya descartado alguno), no vuelve a generar."""
    _own(db, org, asset_id)
    # Bloquea la fila del equipo para que dos llamadas a la vez no creen cuidados duplicados.
    a = db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == asset_id).with_for_update())
    ya = db.scalar(select(CareTask.id).where(CareTask.asset_id == a.id).limit(1))
    if ya:
        return _care_out(a, _tasks(db, a.id))
    try:
        plan = planner.plan(a.category, a.name, a.brand, a.model)
    except Exception:
        log.exception("No se pudieron generar los cuidados del equipo %s", a.id)
        db.rollback()
        raise HTTPException(503, "No pudimos preparar los cuidados ahora. Inténtalo de nuevo en unos minutos.")
    hoy, vistos = today_mx(), set()
    for it in plan.tasks:
        clave = it.title.lower()
        if clave in vistos or len(vistos) >= MAX_TASKS:
            continue
        vistos.add(clave)
        db.add(CareTask(asset_id=a.id, organization_id=org.id, title=it.title[:200], detail=it.detail[:300] or None,
                        instructions=it.instructions or None, every_n=it.every_n, every_unit=it.every_unit,
                        priority=it.priority, source="sugerencia", status="sugerida",
                        next_due=first_due(hoy, it.every_n, it.every_unit)))
    if not vistos:
        db.rollback()
        raise HTTPException(503, "No pudimos preparar los cuidados ahora. Inténtalo de nuevo en unos minutos.")
    _event(db, a, "cuidados_sugeridos", user, cantidad=len(vistos), modelo_ia=getattr(planner, "name", None))
    db.commit()
    return _care_out(a, _tasks(db, a.id))


@router.post("/care/{task_id}/done")
def mark_done(task_id: uuid.UUID, body: DoneIn | None = None, user: User = Depends(current_user),
              org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """Marca el cuidado como realizado y calcula la siguiente fecha. Hacerlo tambien lo confirma como util."""
    t = _task(db, org, task_id)
    hoy = today_mx()
    hecho = (body.done_on if body and body.done_on else hoy)
    if hecho > hoy:
        raise HTTPException(422, "La fecha no puede ser futura.")
    if hecho < hoy - timedelta(days=366):
        raise HTTPException(422, "Esa fecha es muy antigua. Elige una más reciente.")
    t.last_done_at = datetime.now(timezone.utc)
    # La siguiente vez se cuenta desde que se hizo, pero nunca en el pasado.
    t.next_due = max(add_every(hecho, t.every_n, t.every_unit), hoy + timedelta(days=1))
    if t.status == "sugerida":
        t.status = "confirmada"
    db.add(CareRecord(task_id=t.id, asset_id=t.asset_id, organization_id=org.id, done_on=hecho, actor_id=user.id))
    a = db.get(EquipmentAsset, t.asset_id)
    _event(db, a, "cuidado_hecho", user, tarea=t.title, fecha=hecho.isoformat())
    db.commit()
    return _task_out(t)


@router.post("/care/{task_id}/reschedule")
def reschedule(task_id: uuid.UUID, body: RescheduleIn, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    t = _task(db, org, task_id)
    hoy = today_mx()
    if body.next_due < hoy:
        raise HTTPException(422, "Elige una fecha de hoy en adelante.")
    if body.next_due > hoy + timedelta(days=366 * 3):
        raise HTTPException(422, "Elige una fecha más cercana.")
    t.next_due = body.next_due
    db.commit()
    return _task_out(t)


@router.post("/care/{task_id}/confirm")
def confirm_task(task_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """'Me sirve': la persona acepta la sugerencia."""
    t = _task(db, org, task_id)
    t.status = "confirmada"
    db.commit()
    return _task_out(t)


@router.post("/care/{task_id}/dismiss")
def dismiss_task(task_id: uuid.UUID, user: User = Depends(current_user), org: Organization = Depends(current_org),
                 db: Session = Depends(get_db)):
    """'No aplica': deja de mostrarse y no se vuelve a sugerir."""
    t = _task(db, org, task_id)
    t.status = "descartada"
    _event(db, db.get(EquipmentAsset, t.asset_id), "cuidado_descartado", user, tarea=t.title)
    db.commit()
    return {"ok": True}


@router.get("/care")
def household_care(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """Todos los cuidados del hogar, para la pantalla Cuidado del menu. El frente separa proximas y vencidas con 'today'."""
    rows = db.execute(
        select(CareTask, EquipmentAsset, Space.name).join(EquipmentAsset, EquipmentAsset.id == CareTask.asset_id)
        .outerjoin(Space, Space.id == EquipmentAsset.space_id)
        .where(CareTask.organization_id == org.id, CareTask.status != "descartada")
        .order_by(CareTask.next_due, CareTask.title)).all()
    return {"today": today_mx().isoformat(),
            "tasks": [{**_task_out(t), "asset_id": str(a.id), "asset_name": a.name, "space_name": sp} for t, a, sp in rows]}

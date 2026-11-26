from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..db import get_db
from ..models import ClaimAttempt, Kit, KitStatus, Organization, SmartTag, TagStatus, User
from ..security import client_ip, current_org, current_user
from ..services.codes import hash_code

router = APIRouter(prefix="/kits", tags=["kits"])


class ClaimIn(BaseModel):
    code: str = Field(min_length=6, max_length=64)


def _too_many_failures(db: Session, user: User, ip: str) -> bool:
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    n = db.scalar(
        select(func.count()).select_from(ClaimAttempt).where(
            ClaimAttempt.success.is_(False), ClaimAttempt.created_at >= since,
            or_(ClaimAttempt.user_id == user.id, ClaimAttempt.ip == ip),
        )
    )
    return (n or 0) >= get_settings().claim_max_failures_per_hour


@router.post("/claim")
def claim_kit(body: ClaimIn, request: Request, user: User = Depends(current_user),
              org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    ip = client_ip(request)
    if _too_many_failures(db, user, ip):
        raise HTTPException(429, "Demasiados intentos. Espera un rato e inténtalo de nuevo.")
    h = hash_code(body.code)
    kit = db.scalar(select(Kit).where(or_(Kit.code_hash == h, Kit.short_hash == h)).with_for_update())
    if not kit:
        db.add(ClaimAttempt(user_id=user.id, ip=ip, success=False))
        db.commit()
        raise HTTPException(404, "No encontramos ese código. Revisa que esté bien escrito.")
    if kit.status == KitStatus.reclamado:
        if kit.organization_id == org.id:
            return _kit_out(db, kit)  # ya era tuyo: respuesta idempotente
        db.add(ClaimAttempt(user_id=user.id, ip=ip, success=False))
        db.commit()
        raise HTTPException(409, "Este kit ya fue activado.")
    kit.status = KitStatus.reclamado
    kit.organization_id = org.id
    kit.claimed_by = user.id
    kit.claimed_at = datetime.now(timezone.utc)
    for t in db.scalars(select(SmartTag).where(SmartTag.kit_id == kit.id)):
        t.organization_id = org.id
        t.status = TagStatus.disponible
    db.add(ClaimAttempt(user_id=user.id, ip=ip, success=True))
    db.commit()
    return _kit_out(db, kit)


def _kit_out(db: Session, kit: Kit):
    total = db.scalar(select(func.count()).select_from(SmartTag).where(SmartTag.kit_id == kit.id))
    used = db.scalar(select(func.count()).select_from(SmartTag).where(
        SmartTag.kit_id == kit.id, SmartTag.status == TagStatus.vinculada))
    return {"id": str(kit.id), "status": kit.status.value, "tags_total": total, "tags_used": used}


@router.get("")
def my_kits(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    kits = db.scalars(select(Kit).where(Kit.organization_id == org.id).order_by(Kit.claimed_at)).all()
    return [_kit_out(db, k) for k in kits]

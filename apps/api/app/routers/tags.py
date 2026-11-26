from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import EquipmentAsset, Membership, SmartTag, TagStatus, User
from ..security import optional_user

router = APIRouter(prefix="/tags", tags=["etiquetas"])


@router.get("/{token}")
def resolve_tag(token: str, user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    """Resuelve el token de una etiqueta. Nunca devuelve datos privados a quien no es dueño."""
    tag = db.scalar(select(SmartTag).where(SmartTag.token == token.strip().upper()))
    if not tag:
        raise HTTPException(404, "Esta etiqueta no es de NidoGuard o no es válida.")
    if user is None:
        return {"state": "necesita_sesion"}
    my_orgs = set(db.scalars(select(Membership.organization_id).where(Membership.user_id == user.id)))
    if tag.organization_id is None or tag.organization_id not in my_orgs:
        return {"state": "ajena"}
    if tag.status == TagStatus.disponible:
        return {"state": "disponible", "tag_id": str(tag.id)}
    if tag.status == TagStatus.vinculada:
        asset = db.scalar(select(EquipmentAsset).where(EquipmentAsset.tag_id == tag.id))
        if asset:
            return {"state": "vinculada", "asset": {"id": str(asset.id), "name": asset.name,
                                                       "status": asset.status.value}}
    return {"state": "ajena"}

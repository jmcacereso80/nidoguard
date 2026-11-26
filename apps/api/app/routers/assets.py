import uuid
from typing import Literal
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import (
    AssetEvent, AssetImage, AssetReading, AssetStatus, EquipmentAsset, Organization,
    ReadingStatus, SmartTag, Space, Property, TagStatus, User,
)
from ..security import current_org, current_user
from ..services import readings
from ..services.storage import ALLOWED_TYPES, MAX_BYTES, Storage, get_storage

router = APIRouter(prefix="/assets", tags=["equipos"])

NAME_PENDING = "Equipo sin nombre"
PENDING = (AssetStatus.registrado, AssetStatus.leido, AssetStatus.por_confirmar,
           AssetStatus.necesita_foto, AssetStatus.faltan_datos)


class AssetIn(BaseModel):
    tag_token: str
    name: str | None = Field(default=None, max_length=200)  # si no viene, la IA lo sugiere de la placa
    space_id: uuid.UUID | None = None
    new_space_name: str | None = Field(default=None, max_length=120)
    plate_content_type: str | None = None


class ManualIn(BaseModel):
    category: str | None = None
    brand: str | None = None
    model: str | None = None
    serial: str | None = None
    extra: dict | None = None


class ConfirmIn(ManualIn):
    name: str | None = Field(default=None, max_length=200)


class BulkIn(BaseModel):
    ids: list[uuid.UUID]


def _own(db: Session, org: Organization, asset_id: uuid.UUID) -> EquipmentAsset:
    a = db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == asset_id,
                                               EquipmentAsset.organization_id == org.id))
    if not a:
        raise HTTPException(404, "No encontramos ese equipo.")
    return a


def _event(db, asset, type_, actor=None, **payload):
    db.add(AssetEvent(asset_id=asset.id, organization_id=asset.organization_id, type=type_,
                      payload=payload, actor_id=actor.id if actor else None))


def _out(a: EquipmentAsset):
    return {"id": str(a.id), "name": a.name, "status": a.status.value, "category": a.category,
            "brand": a.brand, "model": a.model, "serial": a.serial, "extra": a.extra,
            "space_id": str(a.space_id) if a.space_id else None,
            "created_at": a.created_at.isoformat()}


@router.post("", status_code=201)
def create_asset(body: AssetIn, user: User = Depends(current_user), org: Organization = Depends(current_org),
                 db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    tag = db.scalar(select(SmartTag).where(SmartTag.token == body.tag_token.strip().upper()).with_for_update())
    if not tag or tag.organization_id != org.id:
        raise HTTPException(404, "Esta etiqueta no está disponible en tu hogar.")
    if tag.status != TagStatus.disponible:
        raise HTTPException(409, "Esta etiqueta ya está en uso.")
    space = None
    if body.space_id:
        space = db.scalar(select(Space).where(Space.id == body.space_id, Space.organization_id == org.id))
        if not space:
            raise HTTPException(404, "No encontramos esa ubicación.")
    elif body.new_space_name and body.new_space_name.strip():
        prop = db.scalar(select(Property).where(Property.organization_id == org.id).order_by(Property.created_at))
        space = Space(organization_id=org.id, property_id=prop.id, name=body.new_space_name.strip())
        db.add(space)
        db.flush()
    else:
        raise HTTPException(422, "Elige dónde está el equipo.")
    given = (body.name or "").strip()
    asset = EquipmentAsset(organization_id=org.id, tag_id=tag.id, space_id=space.id,
                           name=given or NAME_PENDING, created_by=user.id,
                           extra={} if given else {"nombre_pendiente": True})
    db.add(asset)
    db.flush()
    tag.status = TagStatus.vinculada
    _event(db, asset, "registro", user, tag_id=str(tag.id))
    out = _out(asset)
    out["space_id"] = str(space.id)
    if body.plate_content_type:
        ext = ALLOWED_TYPES.get(body.plate_content_type)
        if not ext:
            raise HTTPException(422, "Formato de foto no permitido. Usa JPG, PNG, WEBP o HEIC.")
        img_id = uuid.uuid4()
        key = f"org/{org.id}/assets/{asset.id}/{img_id}.{ext}"
        db.add(AssetImage(id=img_id, asset_id=asset.id, organization_id=org.id, kind="placa",
                          storage_key=key, content_type=body.plate_content_type))
        out["upload"] = {"image_id": str(img_id), "method": "PUT", "url": storage.presign_put(key, body.plate_content_type),
                         "headers": {"Content-Type": body.plate_content_type}}
    db.commit()
    return out


class PhotoIn(BaseModel):
    content_type: str
    kind: Literal["placa", "equipo"] = "placa"


@router.post("/{asset_id}/fotos")
def new_photo(asset_id: uuid.UUID, body: PhotoIn, org: Organization = Depends(current_org),
              db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """Foto nueva para un equipo que ya existe (p. ej. la anterior salio borrosa)."""
    a = _own(db, org, asset_id)
    ext = ALLOWED_TYPES.get(body.content_type)
    if not ext:
        raise HTTPException(422, "Formato de foto no permitido. Usa JPG, PNG, WEBP o HEIC.")
    if body.kind == "equipo":
        n = db.scalar(select(func.count()).select_from(AssetImage).where(
            AssetImage.asset_id == a.id, AssetImage.kind == "equipo"))
        if n >= 2:
            raise HTTPException(422, "Puedes subir hasta 2 fotos del equipo.")
    img_id = uuid.uuid4()
    key = f"org/{org.id}/assets/{a.id}/{img_id}.{ext}"
    db.add(AssetImage(id=img_id, asset_id=a.id, organization_id=org.id, kind=body.kind,
                      storage_key=key, content_type=body.content_type))
    db.commit()
    return {"image_id": str(img_id), "method": "PUT", "url": storage.presign_put(key, body.content_type),
            "headers": {"Content-Type": body.content_type}}


@router.post("/{asset_id}/images/{image_id}/uploaded")
def image_uploaded(asset_id: uuid.UUID, image_id: uuid.UUID, tasks: BackgroundTasks,
                   org: Organization = Depends(current_org), db: Session = Depends(get_db),
                   storage: Storage = Depends(get_storage)):
    asset = _own(db, org, asset_id)
    img = db.scalar(select(AssetImage).where(AssetImage.id == image_id, AssetImage.asset_id == asset.id))
    if not img:
        raise HTTPException(404, "No encontramos esa foto.")
    info = storage.head(img.storage_key)
    if not info:
        raise HTTPException(409, "La foto todavía no llega. Inténtalo de nuevo.")
    if info["size"] > MAX_BYTES:
        raise HTTPException(413, "La foto es demasiado pesada (máximo 12 MB).")
    img.uploaded = True
    # Una foto del equipo sola espera a la placa; si el equipo ya fue leido, se vuelve a leer con todas.
    leido = db.scalar(select(func.count()).select_from(AssetReading).where(
        AssetReading.asset_id == asset.id, AssetReading.source == "ia")) or 0
    if img.kind == "placa" or leido:
        asset.status = AssetStatus.registrado
        db.add(AssetReading(asset_id=asset.id, organization_id=org.id, source="ia", status=ReadingStatus.procesando))
        db.commit()
        tasks.add_task(readings.enqueue_reading, asset.id, img.id)
        return {"ok": True, "lectura": True}
    db.commit()
    return {"ok": True, "lectura": False}


@router.get("")
def list_assets(status: str | None = None, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    q = select(EquipmentAsset).where(EquipmentAsset.organization_id == org.id).order_by(EquipmentAsset.created_at.desc())
    if status == "por_confirmar":
        q = q.where(EquipmentAsset.status.in_(PENDING))
    elif status:
        q = q.where(EquipmentAsset.status == AssetStatus(status))
    return [_out(a) for a in db.scalars(q)]


def _latest_reading(db, asset_id):
    return db.scalar(select(AssetReading).where(AssetReading.asset_id == asset_id)
                     .order_by(AssetReading.created_at.desc()))


@router.get("/{asset_id}")
def get_asset(asset_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    a = _own(db, org, asset_id)
    r = _latest_reading(db, a.id)
    events = db.scalars(select(AssetEvent).where(AssetEvent.asset_id == a.id).order_by(AssetEvent.created_at)).all()
    out = _out(a)
    out["reading"] = None if not r else {"status": r.status.value, "source": r.source, "fields": r.fields,
                                         "confidence": r.confidence, "confirmed": r.confirmed_at is not None}
    out["events"] = [{"type": e.type, "at": e.created_at.isoformat(), "payload": e.payload} for e in events]
    return out


def _apply(a: EquipmentAsset, f: dict):
    for k in ("category", "brand", "model", "serial"):
        if f.get(k):
            setattr(a, k, f[k])
    if f.get("extra"):
        a.extra = {**(a.extra or {}), **f["extra"]}


class AssetEditIn(BaseModel):
    """Campos que el usuario puede corregir. Solo cambia lo que se manda."""
    name: str | None = Field(default=None, max_length=200)
    space_id: uuid.UUID | None = None
    category: str | None = Field(default=None, max_length=80)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial: str | None = Field(default=None, max_length=120)


@router.patch("/{asset_id}")
def edit_asset(asset_id: uuid.UUID, body: AssetEditIn, user: User = Depends(current_user),
               org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    a = _own(db, org, asset_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return _out(a)
    if "name" in changes and not (changes["name"] or "").strip():
        raise HTTPException(422, "El equipo necesita un nombre.")
    if "space_id" in changes:
        if changes["space_id"] is None:
            raise HTTPException(422, "Elige dónde está el equipo.")
        space = db.scalar(select(Space).where(Space.id == changes["space_id"], Space.organization_id == org.id))
        if not space:
            raise HTTPException(404, "No encontramos esa ubicación.")
        a.space_id = space.id
    for k in ("name", "category", "brand", "model", "serial"):
        if k in changes:
            v = (changes[k] or "").strip() or None
            setattr(a, k, v)
    if "name" in changes:
        a.extra = {**(a.extra or {}), "nombre_pendiente": False}
    _event(db, a, "edicion", user, fields=sorted(changes.keys()))
    db.commit()
    return _out(a)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db),
                 storage: Storage = Depends(get_storage)):
    """Elimina el equipo y su historial. La etiqueta vuelve a quedar disponible para otro equipo."""
    a = _own(db, org, asset_id)
    keys = list(db.scalars(select(AssetImage.storage_key).where(AssetImage.asset_id == a.id)))
    if a.tag_id:
        tag = db.get(SmartTag, a.tag_id)
        if tag:
            tag.status = TagStatus.disponible
    db.delete(a)              # lecturas, fotos y eventos se borran en cascada (ON DELETE CASCADE)
    db.commit()
    for key in keys:          # la foto privada tambien se borra de R2; si falla, no bloquea el borrado
        try:
            storage.delete(key)
        except Exception:
            pass
    return Response(status_code=204)


@router.patch("/{asset_id}/manual")
def manual_data(asset_id: uuid.UUID, body: ManualIn, user: User = Depends(current_user),
                org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    a = _own(db, org, asset_id)
    data = body.model_dump(exclude_none=True)
    _apply(a, data)
    db.add(AssetReading(asset_id=a.id, organization_id=org.id, source="manual", status=ReadingStatus.lista,
                        fields=data, confidence={k: 1.0 for k in data}, confirmed_at=datetime.now(timezone.utc)))
    a.status = AssetStatus.completo
    _event(db, a, "datos_manuales", user, fields=list(data))
    db.commit()
    return _out(a)


@router.post("/{asset_id}/confirm")
def confirm(asset_id: uuid.UUID, body: ConfirmIn, user: User = Depends(current_user),
            org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    a = _own(db, org, asset_id)
    r = _latest_reading(db, a.id)
    base = dict(r.fields) if r and r.status == ReadingStatus.lista else {}
    edits = body.model_dump(exclude_none=True)
    name = edits.pop("name", None)
    _apply(a, {**base, **edits})
    if name and name.strip():
        a.name = name.strip()
        a.extra = {**(a.extra or {}), "nombre_pendiente": False}
    if (a.extra or {}).get("nombre_pendiente"):
        raise HTTPException(422, "Escribe qué equipo es antes de confirmar.")
    if r:
        r.confirmed_at = datetime.now(timezone.utc)
    a.status = AssetStatus.completo
    _event(db, a, "confirmado", user)
    db.commit()
    return _out(a)


@router.post("/confirm-bulk")
def confirm_bulk(body: BulkIn, user: User = Depends(current_user), org: Organization = Depends(current_org),
                 db: Session = Depends(get_db)):
    done, skipped = [], []
    for aid in body.ids:
        a = db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == aid, EquipmentAsset.organization_id == org.id))
        r = _latest_reading(db, aid) if a else None
        if not a or not r or r.status != ReadingStatus.lista or r.source != "ia":
            skipped.append(str(aid))
            continue
        _apply(a, r.fields)
        r.confirmed_at = datetime.now(timezone.utc)
        a.status = AssetStatus.completo
        _event(db, a, "confirmado", user, bulk=True)
        done.append(str(aid))
    db.commit()
    return {"confirmed": done, "skipped": skipped}

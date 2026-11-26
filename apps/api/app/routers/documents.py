"""Garantia y factura del equipo: la persona sube el archivo (foto o PDF) y escribe la fecha de vencimiento.
No se usa IA para estos documentos: el archivo es el respaldo y la fecha la pone la persona."""
import hashlib
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AssetDocument, AssetEvent, Organization, User, Warranty
from ..security import current_org, current_user
from ..services.storage import Storage, get_storage
from .assets import _event, _own

router = APIRouter(prefix="/assets", tags=["documentos"])

# Tipos permitidos y tamano maximo en bytes.
ALLOWED = {
    "image/jpeg": ("jpg", 12 * 1024 * 1024),
    "image/png": ("png", 12 * 1024 * 1024),
    "image/webp": ("webp", 12 * 1024 * 1024),
    "image/heic": ("heic", 12 * 1024 * 1024),
    "application/pdf": ("pdf", 20 * 1024 * 1024),
}
KINDS = ("garantia", "factura")


def sniff(head: bytes) -> str | None:
    """Tipo real del archivo por sus primeros bytes (no por la extension ni por lo que dice el navegador)."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"heim", b"heis"):
        return "image/heic"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    return None


class UploadIn(BaseModel):
    kind: str
    filename: str = Field(min_length=1, max_length=200)
    content_type: str
    size: int = Field(gt=0)


class WarrantyIn(BaseModel):
    document_id: uuid.UUID
    ends_on: date
    provider: str | None = Field(default=None, max_length=200)
    price: float | None = Field(default=None, ge=0, le=100_000_000)


def _doc_out(d: AssetDocument) -> dict:
    return {"id": str(d.id), "kind": d.kind, "filename": d.filename, "uploaded": d.uploaded}


def _own_doc(db: Session, org: Organization, asset_id: uuid.UUID, document_id: uuid.UUID) -> AssetDocument:
    d = db.scalar(select(AssetDocument).where(AssetDocument.id == document_id, AssetDocument.asset_id == asset_id,
                                              AssetDocument.organization_id == org.id))
    if not d:
        raise HTTPException(404, "No encontramos ese documento.")
    return d


@router.get("/{asset_id}/documents")
def list_documents(asset_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    a = _own(db, org, asset_id)
    w = db.scalar(select(Warranty).where(Warranty.asset_id == a.id))
    garantias = list(db.scalars(select(AssetDocument).where(
        AssetDocument.asset_id == a.id, AssetDocument.kind == "garantia", AssetDocument.uploaded.is_(True))
        .order_by(AssetDocument.created_at.desc())))
    facturas = list(db.scalars(select(AssetDocument).where(
        AssetDocument.asset_id == a.id, AssetDocument.kind == "factura", AssetDocument.uploaded.is_(True))
        .order_by(AssetDocument.created_at.desc())))
    pendiente = next((g for g in garantias if w is None or g.id != w.document_id), None)
    return {
        "manuals": [],  # la busqueda del manual es una fase posterior
        "warranty": None if not w else {
            "ends_on": w.ends_on.isoformat(), "provider": w.provider, "price": w.price,
            "confirmed": True, "estimated": False, "document_id": str(w.document_id),
        },
        "warranty_pending": None if not pendiente else {"document_id": str(pendiente.id), "filename": pendiente.filename},
        "invoice": None if not facturas else {
            "id": str(facturas[0].id), "uploaded_at": facturas[0].created_at.isoformat(), "name": facturas[0].filename,
        },
    }


@router.post("/{asset_id}/documents/upload-url")
def upload_url(asset_id: uuid.UUID, body: UploadIn, org: Organization = Depends(current_org),
               db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    a = _own(db, org, asset_id)
    if body.kind not in KINDS:
        raise HTTPException(422, "Elige si es garantía o factura.")
    if body.content_type not in ALLOWED:
        raise HTTPException(422, "Formato no permitido. Usa foto (JPG, PNG, WEBP o HEIC) o PDF.")
    ext, max_bytes = ALLOWED[body.content_type]
    if body.size > max_bytes:
        raise HTTPException(413, f"El archivo es demasiado pesado (máximo {max_bytes // (1024 * 1024)} MB).")
    doc_id = uuid.uuid4()
    key = f"org/{org.id}/assets/{a.id}/docs/{doc_id}.{ext}"
    db.add(AssetDocument(id=doc_id, asset_id=a.id, organization_id=org.id, kind=body.kind,
                         filename=body.filename.strip()[:200], storage_key=key, content_type=body.content_type,
                         size=body.size, uploaded=False))
    db.commit()
    return {"document_id": str(doc_id), "upload_url": storage.presign_put(key, body.content_type),
            "method": "PUT", "headers": {"Content-Type": body.content_type}}


@router.post("/{asset_id}/documents/{document_id}/process")
def process_document(asset_id: uuid.UUID, document_id: uuid.UUID, org: Organization = Depends(current_org),
                     db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """Confirma la subida: revisa el tipo real y el tamano, y evita guardar dos veces el mismo archivo."""
    _own(db, org, asset_id)
    d = _own_doc(db, org, asset_id, document_id)
    if d.uploaded:
        return _doc_out(d)  # idempotente
    info = storage.head(d.storage_key)
    if not info:
        raise HTTPException(409, "El archivo todavía no llega. Inténtalo de nuevo.")
    _, max_bytes = ALLOWED[d.content_type]
    if info["size"] > max_bytes:
        storage.delete(d.storage_key); db.delete(d); db.commit()
        raise HTTPException(413, "El archivo es demasiado pesado.")
    raw = storage.get_bytes(d.storage_key)
    if sniff(raw[:32]) != d.content_type:
        storage.delete(d.storage_key); db.delete(d); db.commit()
        raise HTTPException(422, "El archivo no es una foto o un PDF válido.")
    digest = hashlib.sha256(raw).hexdigest()
    igual = db.scalar(select(AssetDocument).where(
        AssetDocument.asset_id == d.asset_id, AssetDocument.sha256 == digest, AssetDocument.uploaded.is_(True),
        AssetDocument.id != d.id))
    if igual:  # el mismo archivo ya estaba: no se guarda dos veces
        storage.delete(d.storage_key); db.delete(d); db.commit()
        return {**_doc_out(igual), "duplicado": True}
    d.uploaded = True
    d.sha256 = digest
    d.size = len(raw)
    db.commit()
    return _doc_out(d)


@router.post("/{asset_id}/warranty")
def save_warranty(asset_id: uuid.UUID, body: WarrantyIn, user: User = Depends(current_user),
                  org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """La persona confirma la fecha de vencimiento (y proveedor y precio si los tiene). Se puede volver a guardar para corregir."""
    a = _own(db, org, asset_id)
    d = _own_doc(db, org, asset_id, body.document_id)
    if d.kind != "garantia" or not d.uploaded:
        raise HTTPException(422, "Sube primero el documento de la garantía.")
    w = db.scalar(select(Warranty).where(Warranty.asset_id == a.id))
    if w is None:
        w = Warranty(asset_id=a.id, organization_id=org.id)
        db.add(w)
    w.document_id = d.id
    w.ends_on = body.ends_on
    w.provider = (body.provider or "").strip() or None
    w.price = body.price
    w.updated_at = datetime.now(timezone.utc)
    _event(db, a, "garantia", user, ends_on=body.ends_on.isoformat())
    db.commit()
    return {"ends_on": w.ends_on.isoformat(), "provider": w.provider, "price": w.price, "document_id": str(w.document_id)}


@router.get("/{asset_id}/care")
def care(asset_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """Plan de cuidado. Por ahora vacio: la fase de cuidado llega despues."""
    a = _own(db, org, asset_id)
    return {"model_confirmed": bool(a.model), "tasks": []}

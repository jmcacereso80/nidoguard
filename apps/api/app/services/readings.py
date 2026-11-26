"""Procesa la lectura de una placa: imagen -> IA -> AssetReading -> estado del equipo."""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal
from ..models import AssetEvent, AssetImage, AssetReading, AssetStatus, EquipmentAsset, ReadingStatus
from .plate_reader import FIELD_NAMES, PlateExtraction, PlateReader, get_fallback_reader, get_reader
from .storage import Storage, get_storage

log = logging.getLogger("nidoguard.readings")
KEY_FIELDS = ("brand", "model")


def _needs_fallback(r: PlateExtraction) -> bool:
    if not r.legible:
        return False  # una foto ilegible no mejora con otro modelo: se pide otra foto
    low = get_settings().plate_min_confidence
    return any((getattr(r, f).value is None or getattr(r, f).confidence < low) for f in KEY_FIELDS)


def read_with_fallback(image: bytes, content_type: str, reader: PlateReader, fallback: PlateReader | None):
    result, used = reader.read(image, content_type), reader.name
    if fallback is not None and _needs_fallback(result):
        better = fallback.read(image, content_type)
        if better.legible:
            result, used = better, fallback.name
    return result, used


def process_reading(db: Session, storage: Storage, asset_id: uuid.UUID, image_id: uuid.UUID,
                    reader: PlateReader, fallback: PlateReader | None = None) -> AssetReading:
    asset = db.get(EquipmentAsset, asset_id)
    img = db.get(AssetImage, image_id)
    reading = db.scalar(select(AssetReading).where(AssetReading.asset_id == asset_id, AssetReading.source == "ia")
                        .order_by(AssetReading.created_at.desc()))
    if reading is None:
        reading = AssetReading(asset_id=asset_id, organization_id=asset.organization_id, source="ia")
        db.add(reading)
    try:
        result, used = read_with_fallback(storage.get_bytes(img.storage_key), img.content_type, reader, fallback)
    except Exception as e:  # la lectura nunca debe romper el alta
        log.exception("fallo la lectura de la placa")
        reading.status, reading.error = ReadingStatus.error, str(e)[:500]
        asset.status = AssetStatus.necesita_foto
        db.commit()
        return reading
    fields = {f: getattr(result, f).value for f in FIELD_NAMES if getattr(result, f).value is not None}
    if result.suggested_name:
        fields["suggested_name"] = result.suggested_name
    reading.fields = fields
    reading.confidence = {f: getattr(result, f).confidence for f in FIELD_NAMES}
    reading.transcript = result.transcript
    reading.model_used = used
    if not result.legible:
        reading.status, asset.status = ReadingStatus.necesita_foto, AssetStatus.necesita_foto
    elif not (fields.get("brand") and fields.get("model")):
        reading.status, asset.status = ReadingStatus.faltan_datos, AssetStatus.faltan_datos
    else:
        reading.status, asset.status = ReadingStatus.lista, AssetStatus.por_confirmar
    db.add(AssetEvent(asset_id=asset_id, organization_id=asset.organization_id, type="lectura_ia",
                      payload={"estado": reading.status.value, "modelo_ia": used}))
    db.commit()
    return reading


def enqueue_reading(asset_id: uuid.UUID, image_id: uuid.UUID) -> None:
    """Ejecuta la lectura. En produccion lo toma el flujo de Prefect (apps/worker)."""
    try:
        with SessionLocal() as db:
            process_reading(db, get_storage(), asset_id, image_id, get_reader(), get_fallback_reader())
    except Exception:
        log.exception("no se pudo procesar la lectura")

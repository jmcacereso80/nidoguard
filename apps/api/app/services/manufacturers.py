"""Lineas de servicio de los fabricantes. Una linea solo se llama cuando una persona la verifico."""
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import ManufacturerServiceLine

log = logging.getLogger("nidoguard.lineas")


def brand_key(brand: str | None) -> str:
    s = unicodedata.normalize("NFKD", brand or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def verified_line(db: Session, brand: str | None) -> ManufacturerServiceLine | None:
    key = brand_key(brand)
    if not key:
        return None
    return db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == key, ManufacturerServiceLine.status == "verificada"))


def mark_verified(line: ManufacturerServiceLine) -> None:
    line.status, line.verified_at = "verificada", datetime.now(timezone.utc)


RETRY_AFTER = timedelta(days=14)  # si no se encontro la linea, se vuelve a intentar hasta pasadas 2 semanas


def ensure_line(db: Session, brand: str | None, finder) -> ManufacturerServiceLine | None:
    """Garantiza que la marca tenga una fila: la que ya existe, o lo que encuentre la busqueda (por verificar). Nunca llama a nadie."""
    key = brand_key(brand)
    if not key:
        return None
    line = db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == key))
    now = datetime.now(timezone.utc)
    if line and (line.status != "sin_resultado" or (line.found_at and now - line.found_at < RETRY_AFTER)):
        return line
    try:
        cand = finder.find(brand.strip())
    except Exception:  # sin red, llave mala o servicio caido: se intenta otro dia
        log.exception("No se pudo buscar la linea de %s", brand)
        return line
    line = line or ManufacturerServiceLine(brand_key=key, brand=brand.strip())
    line.found_at, line.found_by = now, "ia"
    if cand:
        line.phone_e164, line.hours, line.requires_account_holder, line.source, line.status = cand.phone, cand.hours, cand.requires_holder, cand.source_url, "por_verificar"
    else:
        line.phone_e164, line.status = None, "sin_resultado"
    db.add(line)
    try:
        db.commit()
    except IntegrityError:  # otra solicitud la creo al mismo tiempo
        db.rollback()
        return db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == key))
    return line


def candidate_line(db: Session, brand: str | None) -> ManufacturerServiceLine | None:
    """La linea encontrada pero aun sin verificar: solo se le muestra a la persona, nunca se llama."""
    key = brand_key(brand)
    return db.scalar(select(ManufacturerServiceLine).where(ManufacturerServiceLine.brand_key == key, ManufacturerServiceLine.status == "por_verificar",
                                                           ManufacturerServiceLine.phone_e164.is_not(None))) if key else None


def lookup_in_background(brand: str | None, finder) -> None:
    """Corre fuera de la solicitud (tarda varios segundos): abre su propia sesion."""
    from ..db import SessionLocal
    if not brand:
        return
    with SessionLocal() as db:
        ensure_line(db, brand, finder)

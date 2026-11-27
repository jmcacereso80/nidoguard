"""Lineas de servicio de los fabricantes. Una linea solo se llama cuando una persona la verifico."""
import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ManufacturerServiceLine


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

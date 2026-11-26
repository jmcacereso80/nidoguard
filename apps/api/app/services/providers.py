"""Directorio compartido de tecnicos: se busca en el mapa una sola vez por ciudad y especialidad y se guarda.
Interfaz (ProviderSource) + implementacion con Apify (Google Maps) + falsa para pruebas."""
import logging
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ProviderSearch, ServiceProvider

log = logging.getLogger(__name__)

# Lista cerrada: cada solicitud se asigna a una de estas especialidades.
SPECIALTIES: dict[str, str] = {
    "aire_acondicionado": "técnico de aire acondicionado y minisplit",
    "refrigeracion": "reparación de refrigeradores",
    "lavadoras": "reparación de lavadoras y secadoras",
    "estufas_hornos": "reparación de estufas y hornos",
    "boiler": "técnico de boiler y calentadores de agua",
    "electrodomesticos": "reparación de electrodomésticos",
}


@dataclass
class ProviderRecord:
    source_id: str
    name: str
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    colony: str | None = None
    lat: float | None = None
    lng: float | None = None
    rating: float | None = None
    reviews: int | None = None
    hours: dict | None = None
    brands: list[str] = field(default_factory=list)


class ProviderSource(Protocol):
    def search(self, city: str, specialty: str) -> list[ProviderRecord]: ...


def norm_key(text_: str) -> str:
    t = unicodedata.normalize("NFKD", text_ or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def search_key(city: str, specialty: str) -> str:
    return f"{norm_key(city)}|{specialty}"


def to_e164_mx(raw: str | None) -> str | None:
    """Telefonos de Mexico a formato +52XXXXXXXXXX (10 digitos). Lo que no tenga 10 digitos se descarta."""
    if not raw:
        return None
    d = re.sub(r"\D", "", raw)
    if d.startswith("52") and len(d) in (12, 13):
        d = d[2:]
        if len(d) == 11 and d.startswith("1"):  # formato antiguo de celular: 52 1 + 10
            d = d[1:]
    if len(d) == 12 and d.startswith("52"):
        d = d[2:]
    if len(d) != 10:
        return None
    return "+52" + d


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class ApifyMapsSource:
    """Google Maps con Apify. Los nombres de los campos de salida los confirma el CLI con una corrida real."""

    def search(self, city: str, specialty: str) -> list[ProviderRecord]:
        s = get_settings()
        if not s.apify_token:
            return []
        body = {"searchStringsArray": [SPECIALTIES[specialty]], "locationQuery": f"{city}, México",
                "maxCrawledPlacesPerSearch": 40, "language": "es", "countryCode": "mx"}
        with httpx.Client(timeout=300) as c:
            r = c.post(f"https://api.apify.com/v2/acts/{s.apify_maps_actor}/run-sync-get-dataset-items",
                       headers={"Authorization": f"Bearer {s.apify_token}"}, json=body)
            r.raise_for_status()
            items = r.json()
        return parse_maps_items(items, city)


def parse_maps_items(items: list[dict], city: str) -> list[ProviderRecord]:
    out = []
    for it in items:
        pid = it.get("placeId") or it.get("cid")
        name = it.get("title")
        if not pid or not name or it.get("permanentlyClosed") or it.get("temporarilyClosed"):
            continue
        loc = it.get("location") or {}
        out.append(ProviderRecord(
            source_id=f"maps:{pid}", name=name[:300],
            phone=it.get("phoneUnformatted") or it.get("phone"), website=it.get("website"),
            address=it.get("address"), city=it.get("city") or city, colony=it.get("neighborhood"),
            lat=loc.get("lat"), lng=loc.get("lng"), rating=it.get("totalScore"),
            reviews=it.get("reviewsCount"), hours=None))
    return out


class FakeSource:
    """Tecnicos inventados alrededor del centro de la CDMX, con telefonos ficticios (555 01xx)."""

    def search(self, city: str, specialty: str) -> list[ProviderRecord]:
        base = {"aire_acondicionado": "Frío", "refrigeracion": "Refri", "lavadoras": "Lava"}.get(specialty, "Servicio")
        recs = []
        seed = sum(ord(c) for c in norm_key(city)) % 90  # telefonos ficticios distintos por ciudad
        for i in range(12):
            recs.append(ProviderRecord(
                source_id=f"fake:{norm_key(city)}:{specialty}:{i}", name=f"{base} Técnico {i + 1}",
                phone=f"55 55{seed:02d} {i:04d}", address=f"Calle de Prueba {i + 1}", city=city, colony="Del Valle",
                lat=19.3869 + (i - 6) * 0.008, lng=-99.1693 + (i % 4 - 2) * 0.01,
                rating=round(4.0 + (i % 10) / 12, 1), reviews=20 + i * 7))
        return recs


def get_source() -> ProviderSource:
    return FakeSource() if get_settings().provider_source == "fake" else ApifyMapsSource()


def ensure_directory(db: Session, city: str, specialty: str, source: ProviderSource | None = None, force: bool = False) -> ProviderSearch:
    """Busca en el mapa solo si esa ciudad y especialidad no se buscaron en los ultimos dias. Con candado por clave."""
    if specialty not in SPECIALTIES:
        raise ValueError(f"Especialidad desconocida: {specialty}")
    key = search_key(city, specialty)
    db.execute(text("select pg_advisory_xact_lock(hashtext(:k))"), {"k": "prov:" + key})
    row = db.scalar(select(ProviderSearch).where(ProviderSearch.key == key))
    ttl = timedelta(days=get_settings().provider_ttl_days)
    if row and row.status == "lista" and not force and datetime.now(timezone.utc) - row.updated_at < ttl:
        db.commit()
        return row
    if not row:
        row = ProviderSearch(key=key, city=city, specialty=specialty, status="buscando")
        db.add(row)
    row.status = "buscando"
    db.flush()
    try:
        recs = (source or get_source()).search(city, specialty)
        new = save_records(db, recs, specialty)
        row.status, row.results, row.new_providers, row.detail = "lista", len(recs), new, None
    except Exception as e:
        log.exception("fallo la busqueda de tecnicos %s", key)
        row.status, row.detail = "error", str(e)[:500]
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return row


def save_records(db: Session, recs: list[ProviderRecord], specialty: str) -> int:
    """Guarda sin duplicar: por identificador del mapa y por telefono. Devuelve cuantos son nuevos."""
    new = 0
    for r in recs:
        phone = to_e164_mx(r.phone)
        row = db.scalar(select(ServiceProvider).where(ServiceProvider.source_id == r.source_id))
        if not row and phone:
            row = db.scalar(select(ServiceProvider).where(ServiceProvider.phone_e164 == phone))
        if row:
            if specialty not in row.specialties:
                row.specialties = [*row.specialties, specialty]
            continue
        db.add(ServiceProvider(
            source=r.source_id.split(":")[0], source_id=r.source_id, name=r.name, phone_e164=phone,
            website=r.website, address=r.address, city=r.city, colony=r.colony, lat=r.lat, lng=r.lng,
            specialties=[specialty], brands=r.brands, rating=r.rating, reviews=r.reviews, hours=r.hours))
        new += 1
    db.flush()
    return new


def candidates(db: Session, specialty: str, lat: float, lng: float, radius_km: float, limit: int = 30) -> list[tuple[ServiceProvider, float]]:
    """Tecnicos con telefono, activos y que se pueden llamar, ordenados por mezcla de cercania y calificacion."""
    rows = db.scalars(select(ServiceProvider).where(
        ServiceProvider.status == "activo", ServiceProvider.do_not_call.is_(False),
        ServiceProvider.phone_e164.is_not(None), ServiceProvider.lat.is_not(None),
        ServiceProvider.specialties.contains([specialty]))).all()
    scored = []
    for p in rows:
        d = distance_km(lat, lng, p.lat, p.lng)
        if d > radius_km:
            continue
        rating = p.rating or 3.5
        response = (p.answered + 1) / (p.attempts + 2)  # historial de contestar, suavizado
        score = (rating / 5) * 0.4 + (1 - d / radius_km) * 0.4 + response * 0.2
        scored.append((p, d, score))
    scored.sort(key=lambda x: -x[2])
    return [(p, d) for p, d, _ in scored[:limit]]

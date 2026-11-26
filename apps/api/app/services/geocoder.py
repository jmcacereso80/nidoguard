"""Convierte una direccion en coordenadas. Interfaz + implementacion real (Nominatim) + falsa para pruebas.
Se geocodifica una sola vez, al guardar la direccion."""
from dataclasses import dataclass
from typing import Protocol
import httpx
from ..config import get_settings


@dataclass
class GeoPoint:
    lat: float
    lng: float


class Geocoder(Protocol):
    def geocode(self, street: str, colony: str | None, postal_code: str | None, city: str, state: str | None) -> GeoPoint | None: ...


class NominatimGeocoder:
    URL = "https://nominatim.openstreetmap.org/search"

    def geocode(self, street, colony, postal_code, city, state):
        params = {
            "format": "jsonv2", "limit": 1, "countrycodes": "mx",
            "street": street, "city": city, "postalcode": postal_code or "", "state": state or "",
        }
        params = {k: v for k, v in params.items() if v}
        try:
            r = httpx.get(self.URL, params=params, timeout=10,
                          headers={"User-Agent": get_settings().geocoder_user_agent})
            r.raise_for_status()
            rows = r.json()
        except Exception:
            return None
        if not rows:
            return None
        return GeoPoint(lat=float(rows[0]["lat"]), lng=float(rows[0]["lon"]))


class FakeGeocoder:
    """Devuelve un punto fijo cerca del centro de la CDMX; 'Calle Sin Mapa' simula una direccion no encontrada."""

    def geocode(self, street, colony, postal_code, city, state):
        if "sin mapa" in street.lower():
            return None
        return GeoPoint(lat=19.3869, lng=-99.1693)


def get_geocoder() -> Geocoder:
    return FakeGeocoder() if get_settings().geocoder == "fake" else NominatimGeocoder()

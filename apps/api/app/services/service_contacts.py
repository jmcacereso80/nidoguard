"""Teléfonos de servicio que la persona guarda en el perfil de su equipo: el del fabricante y el de la tienda donde lo compró.

Ej. lo compró en Liverpool: el primer año la garantía es con la tienda y después con el fabricante.
Son números de la propia persona: se le muestran a ella para que llame. El asistente de voz NUNCA llama a un número que la persona escribió
(solo a líneas verificadas por NidoGuard), para que nadie pueda usarlo para hacer llamar a un tercero."""
from datetime import date

from ..models import EquipmentAsset

KEY = "servicio"


def read(a: EquipmentAsset | None) -> dict:
    return dict(((a.extra or {}).get(KEY) or {})) if a else {}


def store_covers(a: EquipmentAsset | None, today: date) -> bool:
    """True si la tienda todavía cubre la garantía (hasta la fecha que la persona escribió)."""
    c = read(a)
    try:
        until = date.fromisoformat(c.get("store_until") or "")
    except ValueError:
        return False
    return until >= today and bool(c.get("store_name") or c.get("store_phone"))


def contacts_out(a: EquipmentAsset | None, today: date) -> dict:
    c = read(a)
    maker = {"name": c.get("maker_name"), "phone": c.get("maker_phone")} if (c.get("maker_name") or c.get("maker_phone")) else None
    store = {"name": c.get("store_name"), "phone": c.get("store_phone"), "until": c.get("store_until"), "active": store_covers(a, today)} \
        if (c.get("store_name") or c.get("store_phone")) else None
    return {"maker": maker, "store": store}


def save(a: EquipmentAsset, maker_name, maker_phone, store_name, store_phone, store_until) -> None:
    data = {"maker_name": maker_name, "maker_phone": maker_phone, "store_name": store_name, "store_phone": store_phone,
            "store_until": store_until.isoformat() if store_until else None}
    extra = dict(a.extra or {})
    extra[KEY] = {k: v for k, v in data.items() if v}
    if not extra[KEY]:
        extra.pop(KEY)
    a.extra = extra

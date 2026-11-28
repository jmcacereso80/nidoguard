"""Revision de seguridad por reglas: no depende de la IA. Si la persona menciona gas, chispas, humo u olor a quemado,
siempre se muestra la alerta antes de seguir."""
import re
from .providers import norm_key

RULES: list[tuple[str, str]] = [
    ("gas", r"\b(olor|huele|huelo|fuga|escape)\b.*\bgas\b|\bgas\b.*\b(olor|huele|huelo|fuga|escape)\b|\bfuga de gas\b"),
    ("chispas", r"\bchispa|\bchispean|\bchispea"),
    ("humo", r"\bhumo\b|\bhumea"),
    ("quemado", r"\b(olor|huele|huelo)\b.*\bquema|\bse quema|\bquemandose|\bolor a quemado"),
    ("descarga", r"\bme dio (un )?(toque|choque|descarga)|\bda (toques|choques|descargas)|\bdescarga electrica"),
    ("agua_electricidad", r"\bagua\b.*\b(enchufe|contacto|cable|corto)\b|\b(enchufe|contacto|cable|corto)\b.*\bagua\b"),
]

MESSAGES = {
    "gas": "Mencionaste olor a gas",
    "chispas": "Mencionaste chispas",
    "humo": "Mencionaste humo",
    "quemado": "Mencionaste olor a quemado",
    "descarga": "Mencionaste una descarga eléctrica",
    "agua_electricidad": "Mencionaste agua cerca de la electricidad",
    "otro": "Esto podría ser peligroso",
}
ADVICE = ("No uses el equipo ni prendas luces o enchufes. Abre puertas y ventanas y sal de la casa si hay olor a gas. "
          "Llama al 911.")


def check(text: str | None) -> str | None:
    """Devuelve el tipo de alerta o None."""
    t = norm_key(text or "")
    for kind, pattern in RULES:
        if re.search(pattern, t):
            return kind
    return None


def alert_out(kind: str | None, acknowledged: bool) -> dict | None:
    if not kind:
        return None
    return {"kind": kind, "title": MESSAGES.get(kind, MESSAGES["otro"]), "advice": ADVICE, "acknowledged": acknowledged}

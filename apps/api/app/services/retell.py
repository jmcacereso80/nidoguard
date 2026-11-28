"""Llamador real con Retell. Solo marca; los resultados llegan por webhook (routers/webhooks.py).
Reglas de seguridad: nada sale si CALLS_ENABLED es falso, si hay lista permitida y el numero no esta, o si el negocio pidio no ser llamado."""
import hashlib
import hmac
import time

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ServiceCall
from .voice import CallContext

API = "https://api.retellai.com"


def sign(raw: bytes, api_key: str, ts_ms: int) -> str:
    d = hmac.new(api_key.encode(), raw + str(ts_ms).encode(), hashlib.sha256).hexdigest()
    return f"v={ts_ms},d={d}"


def verify_signature(raw: bytes, header: str | None, api_key: str, tolerance_s: int = 300, now_ms: int | None = None) -> bool:
    """Firma de Retell: 'v=<ms>,d=<hex>' = HMAC-SHA256(api_key, cuerpo + ms)."""
    if not header or not api_key:
        return False
    try:
        parts = dict(x.split("=", 1) for x in header.split(","))
        ts, digest = int(parts["v"]), parts["d"]
    except (KeyError, ValueError):
        return False
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    if abs(now_ms - ts) > tolerance_s * 1000:
        return False
    expected = hmac.new(api_key.encode(), raw + str(ts).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, digest)


def allowed(phone: str | None) -> tuple[bool, str]:
    s = get_settings()
    if not s.calls_enabled:
        return False, "llamadas apagadas"
    if not phone:
        return False, "sin telefono"
    allow = {x.strip() for x in s.calls_allowlist.split(",") if x.strip()}
    if allow and phone not in allow:
        return False, "fuera de la lista permitida"
    return True, ""


def dynamic_variables(ctx: CallContext) -> dict[str, str]:
    """Retell solo acepta texto. Nunca va la direccion exacta a un tecnico: solo la zona."""
    v = {"tipo": ctx.kind, "equipo": ctx.equipment, "trabajo": ctx.service or "", "sintoma": ctx.symptom or "",
         "urgencia": ctx.urgency or "", "zona": ctx.zone, "negocio": ctx.business_name or ""}
    if ctx.kind in ("cotizar", "agendar", "recordatorio"):  # el agente siempre ve estos dos datos; si faltan, lo dice y no inventa
        v["marca"], v["modelo"] = "sin dato", "sin dato"
    franja = str(ctx.extra.get("franja_elegida") or "la fecha acordada")
    saludos = {"agendar": f"Hola, buen día. Le llamo de NidoGuard para dejar confirmada la visita que usted ofreció, {franja}. ¿Tiene un momento?",
               "recordatorio": f"Hola, buen día. Le llamo de NidoGuard para recordarle la visita de {franja}. ¿Tiene un momento?",
               "cancelar": f"Hola, buen día. Le llamo de NidoGuard por la visita de {franja}. ¿Tiene un momento?"}
    if ctx.kind in saludos:  # el agente de agenda abre con {{saludo}}: nunca con el saludo de cotizar
        v["saludo"] = saludos[ctx.kind]
    for k, val in ctx.extra.items():
        if k in {"marca", "modelo", "serie", "fecha_compra", "titular", "direccion", "telefono_titular", "franja_elegida", "precio", "nombre", "telefono_cliente", "acceso"} and val:
            v[k] = str(val)
    return v


class RetellCaller:
    name = "retell"

    def place(self, db: Session, call: ServiceCall, ctx: CallContext) -> None:
        call.status = "en_cola"  # se marca en oleadas desde requests_flow.dispatch

    def collect(self, db, req, now):
        return None

    def _post(self, path: str, body: dict) -> dict:
        s = get_settings()
        r = httpx.post(API + path, json=body, headers={"Authorization": f"Bearer {s.retell_api_key}"}, timeout=20)
        r.raise_for_status()
        return r.json()

    def dial(self, db: Session, call: ServiceCall, ctx: CallContext, phone: str | None) -> bool:
        s = get_settings()
        ok, why = allowed(phone)
        if not ok:
            call.status = "omitida"
            return False
        agent = {"fabricante": s.retell_agent_id_fabricante, "agendar": s.retell_agent_id_agenda, "recordatorio": s.retell_agent_id_agenda, "cancelar": s.retell_agent_id_agenda}.get(ctx.kind, "") or s.retell_agent_id
        try:
            data = self._post("/v2/create-phone-call", {
                "from_number": s.retell_from_number, "to_number": phone, "override_agent_id": agent,
                "retell_llm_dynamic_variables": dynamic_variables(ctx), "metadata": {"call_id": str(call.id)}})
        except Exception:  # sin red, llave mala o numero rechazado: no se reintenta solo
            call.status = "error"
            return False
        call.status, call.retell_call_id = "llamando", data.get("call_id")
        return True

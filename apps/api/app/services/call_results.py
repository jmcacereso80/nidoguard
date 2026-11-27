"""Llamadas reales: marcar en oleadas, recibir lo que pasó (webhook), guardar la cotización o la cita y cerrar la búsqueda.
Con voz falsa nada de esto marca: lo hace advance_fake."""
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (EquipmentAsset, Property, ServiceAppointment, ServiceCall, ServiceProvider, ServiceQuote, ServiceRequest, User)
from .providers import to_e164_mx
from .quote_extractor import Extractor, ManufacturerDraft, QuoteDraft, clean_excerpt, scrub
from .voice import CallContext, VoiceCaller

FINAL = ("completada", "sin_respuesta", "rechazo", "error", "omitida", "cancelada")
NO_ANSWER = {"dial_failed", "dial_no_answer", "dial_busy", "voicemail_reached", "machine_detected", "invalid_destination", "telephony_provider_permission_denied"}
STUCK_AFTER = timedelta(minutes=30)
WINDOWS = {"manana", "tarde", "dia"}


def _now() -> datetime:
    from .requests_flow import utcnow
    return utcnow()


def _is_real(voice: VoiceCaller) -> bool:
    return getattr(voice, "name", "") == "retell"


def _ctx(db: Session, req: ServiceRequest, call: ServiceCall) -> tuple[CallContext, str | None]:
    zone = ", ".join(x for x in [req.zone_colony, req.zone_city] if x)
    if call.purpose == "fabricante":
        a = db.get(EquipmentAsset, req.asset_id) if req.asset_id else None
        prop = db.get(Property, req.property_id) if req.property_id else None
        user = db.get(User, req.created_by) if req.created_by else None
        extra = {"marca": a.brand if a else None, "modelo": a.model if a else None, "serie": a.serial if a else None,
                 "titular": getattr(user, "name", None), "direccion": prop.address if prop else None, "telefono_titular": req.contact_phone}
        return CallContext(kind="fabricante", service=req.scope_text, equipment=req.equipment_label or "equipo", symptom=req.symptom,
                           urgency=req.urgency, zone=zone or (prop.city if prop else ""), extra=extra), None  # sin linea del fabricante todavia (pieza 9)
    p = db.get(ServiceProvider, call.provider_id)
    return CallContext(kind="cotizar", service=req.scope_text, equipment=req.equipment_label or "equipo", symptom=req.symptom,
                       urgency=req.urgency, zone=zone, business_name=p.name), p.phone_e164


def dispatch(db: Session, req: ServiceRequest, voice: VoiceCaller) -> None:
    """Marca la siguiente oleada: hasta `calls_wave` llamadas a la vez y sin pasar de las cotizaciones que se buscan."""
    if not _is_real(voice) or req.status != "buscando":
        return
    wave = get_settings().calls_wave
    calls = list(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id).order_by(ServiceCall.created_at, ServiceCall.label)))
    quotes = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id)) or 0
    activas = sum(1 for c in calls if c.status == "llamando")
    for c in calls:
        if c.status != "en_cola":
            continue
        if req.route == "tecnico" and quotes + activas >= req.target_quotes:
            break
        if activas >= wave:
            break
        ctx, phone = _ctx(db, req, c)
        p = db.get(ServiceProvider, c.provider_id) if c.provider_id else None
        if p and p.do_not_call:
            c.status = "omitida"
            continue
        if voice.dial(db, c, ctx, phone):
            activas += 1
        if c.status == "omitida" and c.purpose == "fabricante":
            break
    finalize(db, req)


def finalize(db: Session, req: ServiceRequest) -> None:
    if req.status != "buscando":
        return
    calls = list(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id)))
    if req.route == "fabricante":
        if calls and all(c.status in FINAL for c in calls) and not db.scalar(select(ServiceAppointment.id).where(ServiceAppointment.request_id == req.id)):
            req.status = "sin_cita"
        return
    n = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id)) or 0
    en_vuelo = any(c.status == "llamando" for c in calls)
    if n >= req.target_quotes:
        for c in calls:
            if c.status == "en_cola":
                c.status = "cancelada"
        req.status = "lista"
    elif not en_vuelo and not any(c.status == "en_cola" for c in calls):
        req.status = "lista" if n else "sin_respuesta"


def settle(db: Session, req: ServiceRequest, voice: VoiceCaller) -> None:
    """Se llama al consultar la solicitud: libera llamadas atoradas, marca las que siguen y cierra la búsqueda."""
    if not _is_real(voice) or req.status != "buscando":
        return
    now = _now()
    for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status == "llamando")):
        if c.created_at and now - c.created_at > STUCK_AFTER:
            c.status = "error"
    dispatch(db, req, voice)
    db.commit()


# ------------------------------------------------------------------ guardar resultados
def _slots(draft: QuoteDraft, today: date) -> list[dict]:
    out, seen = [], set()
    for s in draft.availability:
        try:
            d = date.fromisoformat(s.date)
        except ValueError:
            continue
        if not (today <= d <= today + timedelta(days=45)) or (d, s.window) in seen or s.window not in WINDOWS:
            continue
        seen.add((d, s.window))
        out.append({"date": d.isoformat(), "window": s.window})
    return sorted(out, key=lambda x: x["date"])[:3]


def apply_quote(db: Session, req: ServiceRequest, call: ServiceCall, draft: QuoteDraft, today: date) -> ServiceQuote | None:
    p = db.get(ServiceProvider, call.provider_id)
    p.attempts += 1
    p.last_called_at = _now()
    if draft.outcome == "rechaza":
        call.status, p.answered = "rechazo", p.answered + 1
        return None
    p.answered += 1
    call.status = "completada"
    lo, hi = draft.price_min, draft.price_max
    if draft.outcome != "cotiza" or lo is None or lo <= 0 or lo > 200_000:
        return None
    hi = lo if hi is None or draft.price_type == "fijo" else hi
    lo, hi = min(lo, hi), min(max(lo, hi), 200_000)
    n = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id)) or 0
    if n >= req.target_quotes or db.scalar(select(ServiceQuote.id).where(ServiceQuote.request_id == req.id, ServiceQuote.provider_id == p.id)):
        return None
    ptype = draft.price_type or ("fijo" if lo == hi else "rango")
    q = ServiceQuote(
        request_id=req.id, provider_id=p.id, call_id=call.id, label=call.label, rating=p.rating, reviews=p.reviews, distance_km=call.distance_km,
        scope_quoted=scrub(draft.scope_quoted), includes=[scrub(x) for x in draft.includes][:6], excludes=[scrub(x) for x in draft.excludes][:6],
        price_min=lo, price_max=hi, price_type=ptype, visit_fee=draft.visit_fee if draft.visit_fee is None or 0 <= draft.visit_fee <= 5000 else None,
        availability=_slots(draft, today), warranty_days=draft.warranty_days if draft.warranty_days is None or 0 <= draft.warranty_days <= 730 else None,
        invoice=draft.invoice, payment_methods=list(draft.payment_methods), matches=draft.matches, summary=scrub(draft.summary),
        excerpt=clean_excerpt(draft.technician_said, call.transcript or "", [p.name]),
        confidence={"precio": round(draft.confidence_price, 2), "alcance": round(draft.confidence_scope, 2)})
    db.add(q)
    p.quotes_given += 1
    return q


def apply_manufacturer(db: Session, req: ServiceRequest, call: ServiceCall, d: ManufacturerDraft, today: date) -> None:
    from .requests_flow import TZ
    call.status = "completada"
    try:
        day = date.fromisoformat(d.date) if d.date else None
    except ValueError:
        day = None
    if not d.scheduled or not day or not (today <= day <= today + timedelta(days=90)):
        req.status = "sin_cita"
        return
    h0 = d.start_hour if d.start_hour is not None and 0 <= d.start_hour <= 23 else 9
    h1 = d.end_hour if d.end_hour is not None and h0 < d.end_hour <= 24 else h0 + 4
    start = datetime.combine(day, datetime.min.time(), TZ).replace(hour=h0)
    end = datetime.combine(day, datetime.min.time(), TZ).replace(hour=min(h1, 23), minute=59 if h1 >= 24 else 0)
    db.add(ServiceAppointment(request_id=req.id, provider_kind="fabricante", location_type="centro" if d.center_name else "domicilio",
                              center_name=scrub(d.center_name), center_address=d.center_address, folio=(d.folio or "")[:60] or None,
                              bring=[scrub(x) for x in d.bring][:6], starts_at=start, ends_at=end, status="confirmada"))
    req.status = "agendada"


# ------------------------------------------------------------------ webhook
def _find_call(db: Session, call: dict) -> ServiceCall | None:
    cid = call.get("call_id")
    found = db.scalar(select(ServiceCall).where(ServiceCall.retell_call_id == cid)) if cid else None
    if found:
        return found
    try:
        return db.get(ServiceCall, uuid.UUID(str((call.get("metadata") or {}).get("call_id"))))
    except ValueError:
        return None


def handle_event(db: Session, payload: dict, extractor: Extractor, voice: VoiceCaller) -> str:
    """Devuelve qué se hizo (para el log y las pruebas). Es idempotente: una llamada ya cerrada no se vuelve a procesar."""
    event, data = payload.get("event"), payload.get("call") or {}
    call = _find_call(db, data)
    if not call:
        return "desconocida"
    req = db.get(ServiceRequest, call.request_id)
    if event == "call_started":
        return "ignorada"
    if call.status in FINAL:
        return "repetida"
    reason = data.get("disconnection_reason")
    if data.get("transcript"):
        call.transcript = str(data["transcript"])[:60_000]
    if data.get("duration_ms"):
        call.duration_s = int(data["duration_ms"] / 1000)
    cost = (data.get("call_cost") or {}).get("combined_cost")
    if isinstance(cost, (int, float)):
        call.cost_usd = round(cost / 100, 4)
    if reason in NO_ANSWER:
        call.status = "sin_respuesta"
        if call.provider_id:
            p = db.get(ServiceProvider, call.provider_id)
            p.attempts, p.last_called_at = p.attempts + 1, _now()
    elif event == "call_analyzed":
        today = _now().astimezone(__import__("zoneinfo").ZoneInfo("America/Mexico_City")).date()
        text = call.transcript or ""
        if len(text.strip()) < 40:
            call.status = "sin_respuesta"
        else:
            try:
                if call.purpose == "fabricante":
                    apply_manufacturer(db, req, call, extractor.manufacturer(text, today), today)
                else:
                    apply_quote(db, req, call, extractor.quote(text, req.scope_text or "", today), today)
            except Exception:
                call.status = "error"
    else:
        return "guardada"
    finalize(db, req)
    dispatch(db, req, voice)
    db.commit()
    return call.status

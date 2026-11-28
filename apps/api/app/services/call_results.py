"""Llamadas reales: marcar en oleadas y con reglas, recibir lo que paso (webhook), guardar cotizaciones y citas, recordatorios y cierre.
Con voz falsa nada de esto marca: lo hace advance_fake. `tick` lo corre Prefect (o `python -m admin.tick`) cada minuto."""
import logging
import uuid
from .people import given_name
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (EquipmentAsset, Property, ServiceAppointment, ServiceCall, ServiceProvider, ServiceQuote, ServiceRequest, User)
from . import call_policy
from .manufacturers import verified_line
from .quote_extractor import AppointmentDraft, Extractor, ManufacturerDraft, QuoteDraft, clean_excerpt, scrub
from .voice import CallContext, VoiceCaller
log = logging.getLogger("nidoguard.llamadas")
MAX_WAVE = 5  # nunca se marca a mas de 5 tecnicos a la vez (un lote)

FINAL = ("completada", "sin_respuesta", "rechazo", "error", "omitida", "cancelada")
NO_ANSWER = {"dial_failed", "dial_no_answer", "dial_busy", "voicemail_reached", "machine_detected", "invalid_destination", "telephony_provider_permission_denied"}
STUCK_AFTER = timedelta(minutes=30)
WINDOWS = {"manana", "tarde", "dia"}
MX = ZoneInfo("America/Mexico_City")
MAX_ATTEMPTS = 2
MAX_ROUNDS = 2


def _now() -> datetime:
    from .requests_flow import utcnow
    return utcnow()


def _is_real(voice: VoiceCaller) -> bool:
    return getattr(voice, "name", "") == "retell"


def _slot_text(slot: dict | None) -> str:
    if not slot:
        return ""
    from .requests_flow import today_mx  # noqa: F401
    d = date.fromisoformat(slot["date"])
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    return f"{dias[d.weekday()]} {d.day} por la {'mañana' if slot.get('window') == 'manana' else 'tarde' if slot.get('window') == 'tarde' else 'mañana o tarde'}"


def _money(q: ServiceQuote) -> str:
    if q.price_min is None:
        return ""
    return f"{q.price_min:.0f} pesos" if q.price_max in (None, q.price_min) else f"entre {q.price_min:.0f} y {q.price_max:.0f} pesos"


def _equipo_datos(db: Session, req: ServiceRequest) -> dict:
    """Marca y modelo del equipo: el tecnico los necesita para cotizar (no identifican a la persona; la serie no se da)."""
    a = db.get(EquipmentAsset, req.asset_id) if req.asset_id else None
    return {"marca": a.brand if a else None, "modelo": a.model if a else None}


def _ctx(db: Session, req: ServiceRequest, call: ServiceCall) -> tuple[CallContext, str | None]:
    zone = ", ".join(x for x in [req.zone_colony, req.zone_city] if x)
    if call.purpose == "fabricante":
        a = db.get(EquipmentAsset, req.asset_id) if req.asset_id else None
        prop = db.get(Property, req.property_id) if req.property_id else None
        user = db.get(User, req.created_by) if req.created_by else None
        line = verified_line(db, a.brand if a else None)  # una linea sin verificar nunca se llama
        extra = {"marca": a.brand if a else None, "modelo": a.model if a else None, "serie": a.serial if a else None,
                 "titular": getattr(user, "name", None), "direccion": prop.address if prop else None, "telefono_titular": req.contact_phone}
        return CallContext(kind="fabricante", service=req.scope_text, equipment=req.equipment_label or "equipo", symptom=req.symptom,
                           urgency=req.urgency, zone=zone or (prop.city if prop else ""), extra=extra), (line.phone_e164 if line else None)
    p = db.get(ServiceProvider, call.provider_id)
    if call.purpose in ("agendar", "recordatorio"):
        ap = db.scalar(select(ServiceAppointment).where(ServiceAppointment.request_id == req.id, ServiceAppointment.provider_id == call.provider_id)
                       .order_by(ServiceAppointment.created_at.desc()))
        q = db.get(ServiceQuote, ap.quote_id) if ap and ap.quote_id else None
        extra = {"precio": _money(q) if q else "", "franja_elegida": _slot_text(ap.requested_slot if ap else None), **_equipo_datos(db, req)}
        if call.purpose == "agendar":  # la direccion exacta y el nombre de pila solo salen aqui, despues de que la persona eligio
            prop = db.get(Property, req.property_id) if req.property_id else None
            user = db.get(User, req.created_by) if req.created_by else None
            extra["direccion"] = prop.address if prop else None
            extra["nombre"] = given_name(user)
            if ap and ap.access_notes:
                extra["acceso"] = ap.access_notes
            if ap and ap.share_phone and user and user.phone_e164:
                extra["telefono_cliente"] = user.phone_e164
        else:
            extra["franja_elegida"] = ap.starts_at.astimezone(MX).strftime("%d/%m a las %H:%M") if ap and ap.starts_at else ""
        return CallContext(kind=call.purpose, service=q.scope_quoted if q else req.scope_text, equipment=req.equipment_label or "equipo", symptom=None,
                           urgency=req.urgency, zone=zone, business_name=p.name, extra=extra), p.phone_e164
    return CallContext(kind="cotizar", service=req.scope_text, equipment=req.equipment_label or "equipo", symptom=req.symptom,
                       urgency=req.urgency, zone=zone, business_name=p.name, extra=_equipo_datos(db, req)), p.phone_e164


def resumes_at(db: Session, req: ServiceRequest, voice_name: str) -> datetime | None:
    """Si hay llamadas esperando a que abra el horario (busqueda o confirmacion de la visita), cuando siguen."""
    if voice_name != "retell" or req.status not in ("buscando", "agendada"):
        return None
    now = _now()
    if call_policy.in_window(now):
        return None
    if db.scalar(select(ServiceCall.id).where(ServiceCall.request_id == req.id, ServiceCall.status == "en_cola").limit(1)):
        return call_policy.next_open(now)
    return None


def _retry_pending(c: ServiceCall, now: datetime) -> bool:
    return c.status == "sin_respuesta" and c.purpose == "cotizar" and c.attempt < MAX_ATTEMPTS and c.scheduled_for is not None


# ------------------------------------------------------------------ marcar
def dispatch(db: Session, req: ServiceRequest, voice: VoiceCaller) -> None:
    """Marca la siguiente oleada: hasta `calls_wave` a la vez, solo en horario, sin pasar de la meta ni de los topes de costo."""
    if not _is_real(voice):
        return
    now = _now()
    if req.status == "buscando":
        _dial_search(db, req, voice, now)
        finalize(db, req)
    elif req.status == "agendada":
        _dial_pending(db, req, voice, now, ("agendar", "recordatorio"))


def _dial_search(db, req, voice, now):
    if not call_policy.in_window(now):
        return
    if call_policy.over_budget(db, req.id, now):
        for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status == "en_cola")):
            c.status = "cancelada"
        return
    wave = max(1, min(get_settings().calls_wave, MAX_WAVE))
    calls = list(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.purpose.in_(("cotizar", "fabricante")))
                            .order_by(ServiceCall.created_at, ServiceCall.label)))
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
        if p and (p.do_not_call):
            c.status = "omitida"
            continue
        if voice.dial(db, c, ctx, phone):
            activas += 1
        if c.status == "omitida" and c.purpose == "fabricante":
            break


def _dial_pending(db, req, voice, now, purposes):
    if not call_policy.in_window(now):
        return
    for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status == "en_cola", ServiceCall.purpose.in_(purposes))):
        ctx, phone = _ctx(db, req, c)
        voice.dial(db, c, ctx, phone)


def finalize(db: Session, req: ServiceRequest) -> None:
    if req.status != "buscando":
        return
    now = _now()
    calls = list(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id)))
    if req.route == "fabricante":
        if calls and all(c.status in FINAL for c in calls) and not db.scalar(select(ServiceAppointment.id).where(ServiceAppointment.request_id == req.id)):
            req.status = "sin_cita"
        return
    n = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id)) or 0
    pendiente = any(c.status in ("llamando", "en_cola") or _retry_pending(c, now) for c in calls)
    if n >= req.target_quotes:
        for c in calls:
            if c.status == "en_cola":
                c.status = "cancelada"
        req.status = "lista"
    elif not pendiente:
        req.status = "lista" if n else "sin_respuesta"


# ------------------------------------------------------------------ tick (Prefect / cron)
def settle(db: Session, req: ServiceRequest, voice: VoiceCaller) -> None:
    """Se llama al consultar la solicitud: libera llamadas atoradas, marca las que siguen y cierra la busqueda."""
    if not _is_real(voice) or req.status not in ("buscando", "agendada"):
        return
    now = _now()
    for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status == "llamando")):
        if c.created_at and now - c.created_at > STUCK_AFTER:
            c.status = "error"
    _retries(db, req, now)
    _expire(db, req, now)
    dispatch(db, req, voice)
    db.commit()


def _retries(db: Session, req: ServiceRequest, now: datetime) -> None:
    """Segundo intento a quien no contesto, despues de un rato y solo si todavia hace falta."""
    if req.status != "buscando" or req.route != "tecnico":
        return
    total = db.scalar(select(func.count()).select_from(ServiceCall).where(
        ServiceCall.request_id == req.id, ServiceCall.status.in_(("llamando", "completada", "sin_respuesta", "rechazo", "error")))) or 0  # las ya marcadas
    quotes = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id)) or 0
    for c in list(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status == "sin_respuesta", ServiceCall.purpose == "cotizar"))):
        if not _retry_pending(c, now) or c.scheduled_for > now or total >= 12 or quotes >= req.target_quotes:
            continue
        c.scheduled_for = None  # ya se programo el reintento
        db.add(ServiceCall(request_id=req.id, provider_id=c.provider_id, purpose="cotizar", label=c.label, distance_km=c.distance_km,
                           attempt=c.attempt + 1, status="en_cola"))
        total += 1


def _expire(db: Session, req: ServiceRequest, now: datetime) -> None:
    if req.status != "buscando" or not req.started_at:
        return
    if now - req.started_at > timedelta(hours=get_settings().request_ttl_hours):
        for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status.in_(("en_cola", "llamando")))):
            c.status = "cancelada"
        for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.scheduled_for.is_not(None))):
            c.scheduled_for = None
        finalize(db, req)


def tick(db: Session, voice: VoiceCaller) -> dict:
    """Un paso del flujo: avanza todas las busquedas en curso, las citas por agendar y los recordatorios del dia siguiente."""
    now = _now()
    n = {"busquedas": 0, "recordatorios": 0}
    for req in db.scalars(select(ServiceRequest).where(ServiceRequest.status.in_(("buscando", "agendada")))):
        settle(db, req, voice)
        n["busquedas"] += req.status == "buscando"
    n["recordatorios"] = send_reminders(db, voice, now)
    db.commit()
    return n


def send_reminders(db: Session, voice: VoiceCaller, now: datetime) -> int:
    """Recordatorio al tecnico el dia anterior: desde 24 h antes y solo en horario de llamadas."""
    if not _is_real(voice) or not call_policy.in_window(now):
        return 0
    sent = 0
    for ap in db.scalars(select(ServiceAppointment).where(
            ServiceAppointment.status == "confirmada", ServiceAppointment.provider_kind == "tecnico", ServiceAppointment.reminder_sent_at.is_(None),
            ServiceAppointment.starts_at.is_not(None), ServiceAppointment.starts_at > now, ServiceAppointment.starts_at <= now + timedelta(hours=24))):
        req = db.get(ServiceRequest, ap.request_id)
        label = db.get(ServiceQuote, ap.quote_id).label if ap.quote_id else "Técnico"
        call = ServiceCall(request_id=req.id, provider_id=ap.provider_id, purpose="recordatorio", label=label, status="en_cola")
        db.add(call)
        db.flush()
        ctx, phone = _ctx(db, req, call)
        voice.dial(db, call, ctx, phone)
        ap.reminder_sent_at = now
        sent += 1
    return sent


# ------------------------------------------------------------------ agendar
def request_schedule_call(db: Session, req: ServiceRequest, ap: ServiceAppointment, voice: VoiceCaller, attempt: int = 1) -> None:
    """Pide al asistente que llame al tecnico a confirmar la visita (solo con voz real)."""
    if not _is_real(voice):
        return
    label = db.get(ServiceQuote, ap.quote_id).label
    db.add(ServiceCall(request_id=req.id, provider_id=ap.provider_id, purpose="agendar", label=label, attempt=attempt, status="en_cola"))
    db.flush()
    _dial_pending(db, req, voice, _now(), ("agendar",))


def _hours(d: date, h0: int | None, h1: int | None, slot: dict | None) -> tuple[datetime, datetime]:
    w = (slot or {}).get("window")
    a = h0 if h0 is not None and 0 <= h0 <= 23 else (14 if w == "tarde" else 9)
    b = h1 if h1 is not None and a < h1 <= 24 else a + 3
    start = datetime.combine(d, datetime.min.time(), MX).replace(hour=a)
    return start, datetime.combine(d, datetime.min.time(), MX).replace(hour=min(b, 23), minute=59 if b >= 24 else 0)


def apply_appointment(db: Session, req: ServiceRequest, call: ServiceCall, ap: ServiceAppointment, draft: AppointmentDraft, today: date) -> None:
    call.status = "completada"
    try:
        day = date.fromisoformat(draft.date) if draft.date else None
    except ValueError:
        day = None
    ok_day = day is not None and today <= day <= today + timedelta(days=45)
    if draft.outcome == "confirma":
        d = day if ok_day else (date.fromisoformat(ap.requested_slot["date"]) if ap.requested_slot else None)
        if d is None:
            return
        ap.starts_at, ap.ends_at = _hours(d, draft.start_hour if ok_day else None, draft.end_hour if ok_day else None, ap.requested_slot)
        ap.status, ap.address_shared_at = "confirmada", _now()
        who = (scrub(draft.person_name) or "").strip().split(" ")[0][:60] if draft.person_name else ""
        if who:
            ap.visit_person = who
        ap.proposed_slot = None
    elif draft.outcome == "propone_otra" and ok_day and ap.proposal_round < MAX_ROUNDS:
        ap.proposed_slot = {"date": day.isoformat(), "start_hour": draft.start_hour, "end_hour": draft.end_hour}
        ap.proposal_round += 1
        ap.status = "por_reprogramar"
    else:  # rechaza, no pudo o ya se agotaron las rondas: se ofrece la siguiente cotizacion
        _decline(db, req, ap)


def _decline(db: Session, req: ServiceRequest, ap: ServiceAppointment) -> None:
    ap.status = "cancelada"
    if ap.quote_id:
        q = db.get(ServiceQuote, ap.quote_id)
        q.declined = True
    req.status, req.chosen_quote_id = "lista", None
    left = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id, ServiceQuote.declined.is_(False))) or 0
    if left == 0:
        req.status = "sin_respuesta"


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
    call.status = "completada"
    try:
        day = date.fromisoformat(d.date) if d.date else None
    except ValueError:
        day = None
    if not d.scheduled or not day or not (today <= day <= today + timedelta(days=90)):
        req.status = "sin_cita"
        return
    start, end = _hours(day, d.start_hour, d.end_hour, None)
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


def _open_appointment(db: Session, call: ServiceCall) -> ServiceAppointment | None:
    return db.scalar(select(ServiceAppointment).where(ServiceAppointment.request_id == call.request_id, ServiceAppointment.provider_id == call.provider_id,
                                                      ServiceAppointment.status == "por_confirmar").order_by(ServiceAppointment.created_at.desc()))


def _no_answer(db: Session, call: ServiceCall, req: ServiceRequest, now: datetime) -> None:
    call.status = "sin_respuesta"
    if call.provider_id:
        p = db.get(ServiceProvider, call.provider_id)
        p.attempts, p.last_called_at = p.attempts + 1, now
    if call.purpose == "cotizar" and call.attempt < MAX_ATTEMPTS:
        call.scheduled_for = now + timedelta(minutes=get_settings().calls_retry_after_min)  # segundo intento mas tarde
    elif call.purpose == "agendar":
        ap = _open_appointment(db, call)
        if ap and call.attempt < MAX_ATTEMPTS:
            db.add(ServiceCall(request_id=req.id, provider_id=call.provider_id, purpose="agendar", label=call.label, attempt=call.attempt + 1, status="en_cola"))
        elif ap:
            _decline(db, req, ap)  # no se pudo confirmar: se ofrece otra cotizacion


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
    now = _now()
    reason = data.get("disconnection_reason")
    if data.get("transcript"):
        call.transcript = str(data["transcript"])[:60_000]
    if data.get("duration_ms"):
        call.duration_s = int(data["duration_ms"] / 1000)
    cost = (data.get("call_cost") or {}).get("combined_cost")
    if isinstance(cost, (int, float)):
        call.cost_usd = round(cost / 100, 4)
    if reason in NO_ANSWER:
        _no_answer(db, call, req, now)
    elif event == "call_analyzed":
        today = now.astimezone(MX).date()
        text = call.transcript or ""
        if len(text.strip()) < 40:
            _no_answer(db, call, req, now)
        elif call.purpose == "recordatorio":
            call.status = "completada"
        else:
            try:
                if call.purpose == "fabricante":
                    apply_manufacturer(db, req, call, extractor.manufacturer(text, today), today)
                elif call.purpose == "agendar":
                    ap = _open_appointment(db, call)
                    if ap:
                        apply_appointment(db, req, call, ap, extractor.appointment(text, today, _slot_text(ap.requested_slot)), today)
                    else:
                        call.status = "completada"
                else:
                    apply_quote(db, req, call, extractor.quote(text, req.scope_text or "", today), today)
            except Exception:
                log.exception("No se pudo leer la llamada %s (%s): la llamada queda en error", call.id, call.purpose)
                call.status = "error"
    else:
        return "guardada"
    log.info("Llamada %s (%s) -> %s; duracion %ss; transcripcion %s caracteres", call.id, call.purpose, call.status, call.duration_s, len(call.transcript or ""))
    finalize(db, req)
    dispatch(db, req, voice)
    db.commit()
    return call.status

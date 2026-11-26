"""Solicitudes de servicio: crear, confirmar el alcance, buscar cotizaciones, agendar y cerrar.
Con la voz falsa todo avanza solo con el tiempo (advance_fake), asi se recorre el proceso completo sin llamar a nadie.
Regla de privacidad: lo que se entrega a las personas usuarias nunca incluye telefono, direccion, sitio ni nombre del tecnico
(el nombre solo cuando la visita ya esta confirmada)."""
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (User, AssetEvent, CareTask, Consent, EquipmentAsset, Property, ServiceAppointment, ServiceCall, ServiceProvider,
                      ServiceQuote, ServiceRequest, Warranty)
from . import safety
from .providers import SPECIALTIES, candidates, ensure_directory, get_source, specialty_for, to_e164_mx
from .scope import ScopeWriter
from .service_mode import service_mode
from .voice import CallContext, VoiceCaller

TZ = ZoneInfo("America/Mexico_City")
CONSENT_VERSION = "v1"
OPEN = ("borrador", "buscando", "lista", "sin_respuesta", "sin_cita", "agendada")
MAX_CALLS = 12


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def today_mx() -> date:
    return datetime.now(TZ).date()


def step_seconds() -> int:
    return get_settings().fake_voice_step_seconds


# ------------------------------------------------------------------ crear
def _property(db: Session, org_id) -> Property | None:
    return db.scalar(select(Property).where(Property.organization_id == org_id).order_by(Property.created_at))


def create_request(db: Session, org, user, *, asset_id=None, care_task_id=None, equipment_label=None, symptom=None,
                   urgency=None, writer: ScopeWriter) -> tuple[ServiceRequest, bool]:
    """Devuelve (solicitud, creada). Para una tarea de Cuidado solo hay una solicitud abierta: si ya existe, se devuelve."""
    task = None
    if care_task_id:
        task = db.scalar(select(CareTask).where(CareTask.id == care_task_id, CareTask.organization_id == org.id, CareTask.status != "descartada"))
        if not task:
            raise HTTPException(404, "No encontramos ese cuidado.")
        existing = db.scalar(select(ServiceRequest).where(ServiceRequest.care_task_id == task.id, ServiceRequest.status.in_(OPEN)))
        if existing:
            return existing, False
        asset_id = task.asset_id
    asset = None
    if asset_id:
        asset = db.scalar(select(EquipmentAsset).where(EquipmentAsset.id == asset_id, EquipmentAsset.organization_id == org.id))
        if not asset:
            raise HTTPException(404, "No encontramos ese equipo.")
    symptom = (symptom or "").strip() or None
    if not task and (not symptom or len(symptom) < 5):
        raise HTTPException(422, "Cuéntanos qué pasa con tu equipo.")
    if not asset and not (equipment_label or "").strip():
        raise HTTPException(422, "Dinos de qué equipo se trata.")
    label = asset.name if asset else equipment_label.strip()[:200]
    category = asset.category if asset else None
    draft = writer.write(label, category, asset.brand if asset else None, asset.model if asset else None,
                         task.title if task else None, symptom, urgency)
    alert = safety.check(symptom)
    if not alert and draft.safety_concern:
        alert = "otro"
    route = "tecnico"
    if asset and service_mode(asset.category) == "llevar":
        route = "fabricante"
    prop = _property(db, org.id)
    req = ServiceRequest(
        organization_id=org.id, property_id=prop.id if prop else None, asset_id=asset.id if asset else None,
        care_task_id=task.id if task else None, created_by=user.id, origin="tarea" if task else "libre", route=route,
        equipment_label=label, symptom=symptom, scope_text=draft.scope_text.strip(),
        specialty=specialty_for(category) if category else draft.specialty,
        urgency=urgency if urgency in ("hoy", "semana", "sin_prisa") else draft.urgency, safety_alert=alert)
    db.add(req)
    db.commit()
    return req, True


# ------------------------------------------------------------------ confirmar y buscar
def _consent(db: Session, user, org, req, type_: str):
    db.add(Consent(user_id=user.id, organization_id=org.id, request_id=req.id, type=type_, text_version=CONSENT_VERSION))


def start(db: Session, req: ServiceRequest, user, org, consent: bool, voice: VoiceCaller, phone: str | None = None) -> ServiceRequest:
    if req.status != "borrador":
        raise HTTPException(409, "Esta solicitud ya está en marcha.")
    if req.safety_alert and not req.safety_acknowledged:
        raise HTTPException(409, "Antes de seguir, confirma que estás a salvo.")
    if not consent:
        raise HTTPException(422, "Necesitamos tu permiso para llamar de tu parte.")
    if not (req.scope_text or "").strip():
        raise HTTPException(422, "Falta decir qué vamos a cotizar.")
    if req.route == "fabricante":
        return _start_manufacturer(db, req, user, org, voice, phone)
    prop = db.get(Property, req.property_id) if req.property_id else None
    if not prop or prop.lat is None or prop.lng is None:
        raise HTTPException(422, "Agrega la dirección de tu hogar para buscar técnicos cercanos.")
    spec = req.specialty if req.specialty in SPECIALTIES else "electrodomesticos"
    _consent(db, user, org, req, "llamar_en_su_nombre")
    req.zone_city, req.zone_colony, req.lat, req.lng, req.radius_km = prop.city, prop.colony, prop.lat, prop.lng, prop.search_radius_km
    req.status, req.started_at = "buscando", utcnow()
    ensure_directory(db, prop.city or "Ciudad de México", spec, get_source())
    _queue_calls(db, req, voice, spec)
    db.commit()
    return req


def _queue_calls(db: Session, req: ServiceRequest, voice: VoiceCaller, spec: str) -> int:
    """Agrega llamadas a los técnicos aún no llamados en esta solicitud (hasta MAX_CALLS en total)."""
    ya = set(db.scalars(select(ServiceCall.provider_id).where(ServiceCall.request_id == req.id)))
    total = db.scalar(select(func.count()).select_from(ServiceCall).where(ServiceCall.request_id == req.id)) or 0
    nuevos = [(p, d) for p, d in candidates(db, spec, req.lat, req.lng, req.radius_km, limit=MAX_CALLS) if p.id not in ya]
    nuevos = nuevos[: max(0, MAX_CALLS - total)]
    for i, (p, d) in enumerate(nuevos):
        call = ServiceCall(request_id=req.id, provider_id=p.id, purpose="cotizar", label=f"Técnico {total + i + 1}", distance_km=round(d, 1))
        db.add(call)
        voice.place(db, call, CallContext(kind="cotizar", service=req.scope_text, equipment=req.equipment_label or "equipo",
                                          symptom=req.symptom, urgency=req.urgency,
                                          zone=", ".join(x for x in [req.zone_colony, req.zone_city] if x),
                                          business_name=p.name, extra={"slot": total + i}))
    return len(nuevos)


def expand(db: Session, req: ServiceRequest, voice: VoiceCaller) -> ServiceRequest:
    if req.status not in ("sin_respuesta", "lista", "buscando") or req.route != "tecnico":
        raise HTTPException(409, "Esta solicitud no se puede ampliar.")
    req.radius_km = 25
    spec = req.specialty if req.specialty in SPECIALTIES else "electrodomesticos"
    ensure_directory(db, req.zone_city or "Ciudad de México", spec, get_source())
    if _queue_calls(db, req, voice, spec) == 0:
        db.commit()
        raise HTTPException(409, "No encontramos más técnicos en esa zona.")
    req.status = "buscando"
    db.commit()
    return req


def _start_manufacturer(db: Session, req: ServiceRequest, user, org, voice: VoiceCaller, phone: str | None) -> ServiceRequest:
    e164 = to_e164_mx(phone)
    if not e164:
        raise HTTPException(422, "Escribe tu teléfono a 10 dígitos: el fabricante lo pide para agendar.")
    if not req.asset_id:
        raise HTTPException(422, "Para agendar con el fabricante necesitamos el equipo en tu lista.")
    prop = db.get(Property, req.property_id) if req.property_id else None
    if not prop or not (prop.street and prop.city):
        raise HTTPException(422, "Agrega la dirección de tu hogar: el fabricante la pide para agendar.")
    a = db.get(EquipmentAsset, req.asset_id)
    _consent(db, user, org, req, "compartir_datos_con_fabricante")
    req.contact_phone = e164
    req.status, req.started_at = "buscando", utcnow()
    call = ServiceCall(request_id=req.id, purpose="fabricante", label="Fabricante")
    db.add(call)
    voice.place(db, call, CallContext(kind="fabricante", service=req.scope_text, equipment=req.equipment_label or "equipo",
                                      symptom=req.symptom, urgency=req.urgency, zone=prop.city or "",
                                      extra={"slot": 1, "brand": a.brand, "model": a.model, "serial": a.serial,
                                             "holder_name": user.name, "address": prop.address}))
    db.commit()
    return req


# ------------------------------------------------------------------ avance (voz falsa)
_PRICE = {"aire_acondicionado": 650, "refrigeracion": 600, "lavadoras": 550, "estufas_hornos": 500, "boiler": 700, "electrodomesticos": 450}
# resultado de cada llamada por posicion: (tipo, ajuste de precio, alcance distinto)
_PLAN = ["cotiza", "cotiza", "no_contesta", "cotiza", "distinto", "cotiza", "rechaza", "cotiza", "cotiza", "cotiza", "cotiza", "cotiza"]
_GARANTIAS = [30, 60, 15, 30, None, 30, 30, 15, 60, 30, 30, 30]


def _slots(i: int) -> list[dict]:
    d0 = today_mx()
    pick = [(1, "tarde"), (2, "manana"), (4, "tarde"), (3, "manana"), (5, "tarde")]
    return [{"date": (d0 + timedelta(days=pick[(i + k) % 5][0] + (i % 3))).isoformat(), "window": pick[(i + k) % 5][1]} for k in range(3)]


def _fake_quote(db: Session, req: ServiceRequest, call: ServiceCall, idx: int) -> ServiceQuote:
    p = db.get(ServiceProvider, call.provider_id)
    base = _PRICE.get(req.specialty or "", 500)
    distinto = _PLAN[idx % len(_PLAN)] == "distinto"
    rango = idx % 2 == 1
    scope = (req.scope_text or "").rstrip(".")
    if distinto:
        q = dict(scope_quoted="Solo la revisión. La reparación la cotiza en tu casa.", price_min=base * 0.8, price_max=base * 0.8,
                 price_type="solo_revision", matches="distinto", includes=["Revisión del equipo"], excludes=["Reparación y refacciones"])
    elif rango:
        q = dict(scope_quoted=f"{scope}.", price_min=base + 20 * idx, price_max=base + 20 * idx + 200, price_type="rango", matches="parcial",
                 includes=["Mano de obra", "Revisión del funcionamiento"], excludes=["Refacciones, si hubiera que cambiar alguna"])
    else:
        q = dict(scope_quoted=f"{scope}.", price_min=base - 10 * idx, price_max=base - 10 * idx, price_type="fijo", matches="igual",
                 includes=["Mano de obra", "Revisión del funcionamiento", "Limpieza y ajuste"], excludes=["Refacciones, si hubiera que cambiar alguna"])
    resumen = (f"Atiende este tipo de equipo. Por {'la revisión' if distinto else 'el servicio'} cobra "
               f"{'entre $%d y $%d' % (q['price_min'], q['price_max']) if q['price_type'] == 'rango' else '$%d' % q['price_min']}"
               f"{'' if idx % 3 else ', y no cobra la visita'}. Puede ir en los próximos días.")
    quote = ServiceQuote(
        request_id=req.id, provider_id=p.id, call_id=call.id, label=call.label, rating=p.rating, reviews=p.reviews,
        distance_km=call.distance_km, visit_fee=0 if idx % 3 == 0 else 150, availability=_slots(idx),
        warranty_days=_GARANTIAS[idx % len(_GARANTIAS)], invoice=idx % 3 != 2, payment_methods=["efectivo", "transferencia"],
        summary=resumen, confidence={"precio": 0.9, "alcance": 0.8}, **q)
    db.add(quote)
    p.quotes_given += 1
    return quote


def _ordered(calls) -> list[ServiceCall]:
    """Por numero de tecnico (Técnico 2 antes que Técnico 10)."""
    return sorted(calls, key=lambda c: int((c.label or "0").split()[-1]) if (c.label or "").split()[-1:] and (c.label or "").split()[-1].isdigit() else 0)


def advance_fake(db: Session, req: ServiceRequest, now: datetime | None = None) -> None:
    """Termina las llamadas falsas que ya les toca y cierra la búsqueda. También confirma citas falsas."""
    if get_settings().voice != "fake":
        return
    now = now or utcnow()
    if req.status == "buscando":
        calls = _ordered(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id)))
        if req.route == "fabricante":
            _advance_manufacturer(db, req, calls, now)
        else:
            _advance_quotes(db, req, calls, now)
    elif req.status == "agendada":
        for ap in db.scalars(select(ServiceAppointment).where(ServiceAppointment.request_id == req.id, ServiceAppointment.status == "por_confirmar")):
            if ap.created_at + timedelta(seconds=step_seconds() * 2) <= now:
                _confirm_fake_appointment(db, req, ap, now)
    db.commit()


def _advance_quotes(db, req, calls, now):
    n_quotes = db.scalar(select(func.count()).select_from(ServiceQuote).where(ServiceQuote.request_id == req.id)) or 0
    for call in calls:
        if call.status != "en_cola":
            continue
        if n_quotes >= req.target_quotes:
            call.status = "cancelada"
            continue
        if call.scheduled_for and call.scheduled_for > now:
            continue
        pos = int(call.label.split()[-1]) - 1
        kind = _PLAN[pos % len(_PLAN)]
        p = db.get(ServiceProvider, call.provider_id)
        p.attempts += 1
        p.last_called_at = now
        if kind == "no_contesta":
            call.status = "sin_respuesta"
        elif kind == "rechaza":
            call.status, p.answered = "rechazo", p.answered + 1
        else:
            call.status, call.duration_s, p.answered = "completada", 60 + 7 * pos, p.answered + 1
            _fake_quote(db, req, call, pos)
            n_quotes += 1
    if n_quotes >= req.target_quotes or not any(c.status == "en_cola" for c in calls):
        for c in calls:
            if c.status == "en_cola":
                c.status = "cancelada"
        req.status = "lista" if n_quotes else "sin_respuesta"


def _advance_manufacturer(db, req, calls, now):
    call = next((c for c in calls if c.purpose == "fabricante" and c.status == "en_cola"), None)
    if not call or (call.scheduled_for and call.scheduled_for > now):
        return
    asset = db.get(EquipmentAsset, req.asset_id) if req.asset_id else None
    if "sin linea" in (asset.brand or "").lower():  # marca de prueba: el fabricante no acepta al asistente
        call.status, req.status = "rechazo", "sin_cita"
        return
    call.status, call.duration_s = "completada", 420
    start_day = today_mx() + timedelta(days=8)
    start = datetime.combine(start_day, datetime.min.time(), TZ).replace(hour=10)
    brand = (asset.brand if asset and asset.brand else "del fabricante")
    db.add(ServiceAppointment(
        request_id=req.id, provider_kind="fabricante", location_type="centro", center_name=f"Centro de servicio {brand}",
        center_address="Av. Ejemplo 456, Col. Centro, CDMX", folio=f"OS-{int(str(req.id.int)[-5:]):05d}",
        bring=["El equipo con sus accesorios", "Tu garantía o factura", "Una identificación"],
        starts_at=start, ends_at=start + timedelta(hours=4), status="confirmada"))
    req.status = "agendada"


def _confirm_fake_appointment(db, req, ap, now):
    slot = ap.requested_slot or {}
    d = date.fromisoformat(slot["date"]) if slot.get("date") else today_mx() + timedelta(days=2)
    hora = 16 if slot.get("window") == "tarde" else 10
    ap.starts_at = datetime.combine(d, datetime.min.time(), TZ).replace(hour=hora)
    ap.ends_at = ap.starts_at + timedelta(hours=2)
    ap.status, ap.address_shared_at = "confirmada", now


# ------------------------------------------------------------------ agendar con un tecnico
def schedule(db: Session, req: ServiceRequest, user, org, quote_id, slot_index: int, consent: bool) -> ServiceAppointment:
    if req.status not in ("lista", "buscando"):
        raise HTTPException(409, "Esta solicitud no se puede agendar ahora.")
    q = db.scalar(select(ServiceQuote).where(ServiceQuote.id == quote_id, ServiceQuote.request_id == req.id))
    if not q:
        raise HTTPException(404, "No encontramos esa cotización.")
    if not q.availability or not (0 <= slot_index < len(q.availability)):
        raise HTTPException(422, "Elige un horario de los que dio el técnico.")
    if not consent:
        raise HTTPException(422, "Necesitamos tu permiso para dar tu dirección al técnico cuando confirme la visita.")
    _consent(db, user, org, req, "compartir_datos_para_visita")
    ap = ServiceAppointment(request_id=req.id, quote_id=q.id, provider_id=q.provider_id, provider_kind="tecnico", location_type="domicilio",
                            requested_slot=q.availability[slot_index], status="por_confirmar")
    db.add(ap)
    req.status, req.chosen_quote_id = "agendada", q.id
    for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.status == "en_cola")):
        c.status = "cancelada"
    db.commit()
    return ap


def finish(db: Session, req: ServiceRequest, ap: ServiceAppointment, user, final_cost: float | None) -> None:
    ap.status, ap.final_cost = "realizada", final_cost
    req.status = "terminada"
    if req.asset_id:
        db.add(AssetEvent(asset_id=req.asset_id, organization_id=req.organization_id, type="servicio_realizado", actor_id=user.id,
                          payload={"servicio": req.scope_text, "con": ap.provider_kind, "costo_final": final_cost,
                                   "folio": ap.folio, "solicitud": str(req.id)}))
    db.commit()


# ------------------------------------------------------------------ lo que ve la persona
def _tags(quotes: list[ServiceQuote]) -> dict[uuid.UUID, list[str]]:
    out: dict[uuid.UUID, list[str]] = {q.id: [] for q in quotes}
    comparables = [q for q in quotes if q.matches != "distinto" and q.price_min is not None]
    if comparables:
        out[min(comparables, key=lambda q: (q.price_min, q.price_max or 0)).id].append("mas_barata")
    con_fecha = [q for q in quotes if q.availability]
    if con_fecha:
        out[min(con_fecha, key=lambda q: q.availability[0]["date"]).id].append("mas_pronto")
    con_dist = [q for q in quotes if q.distance_km is not None]
    if con_dist:
        out[min(con_dist, key=lambda q: q.distance_km).id].append("mas_cerca")
    return out


def quote_out(q: ServiceQuote, tags: list[str] | None = None) -> dict:
    return {"id": str(q.id), "label": q.label, "rating": q.rating, "reviews": q.reviews, "distance_km": q.distance_km,
            "scope_quoted": q.scope_quoted, "includes": q.includes, "excludes": q.excludes,
            "price_min": q.price_min, "price_max": q.price_max, "price_type": q.price_type, "visit_fee": q.visit_fee,
            "availability": q.availability, "warranty_days": q.warranty_days, "invoice": q.invoice,
            "payment_methods": q.payment_methods, "matches": q.matches, "summary": q.summary, "tags": tags or []}


def appointment_out(db: Session, ap: ServiceAppointment) -> dict:
    out = {"id": str(ap.id), "kind": ap.provider_kind, "status": ap.status, "location_type": ap.location_type,
           "center_name": ap.center_name, "center_address": ap.center_address, "folio": ap.folio, "bring": ap.bring,
           "starts_at": ap.starts_at.isoformat() if ap.starts_at else None, "ends_at": ap.ends_at.isoformat() if ap.ends_at else None,
           "requested_slot": ap.requested_slot, "registered_by_user": ap.registered_by_user, "final_cost": ap.final_cost,
           "technician_name": None, "agreed": None}
    if ap.quote_id:
        q = db.get(ServiceQuote, ap.quote_id)
        out["agreed"] = {"label": q.label, "scope": q.scope_quoted, "price_min": q.price_min, "price_max": q.price_max,
                         "price_type": q.price_type, "visit_fee": q.visit_fee, "warranty_days": q.warranty_days, "invoice": q.invoice,
                         "rating": q.rating, "reviews": q.reviews}
        if ap.status in ("confirmada", "realizada") and ap.provider_id:
            out["technician_name"] = db.get(ServiceProvider, ap.provider_id).name  # solo con la visita confirmada
    return out


def _manufacturer_out(db: Session, req: ServiceRequest, prop: Property | None) -> dict:
    """Los datos propios de la persona y del equipo que se le dan al fabricante (los ve ella antes de autorizar)."""
    a = db.get(EquipmentAsset, req.asset_id) if req.asset_id else None
    u = db.get(User, req.created_by) if req.created_by else None
    w = db.scalar(select(Warranty).where(Warranty.asset_id == a.id)) if a else None
    return {"brand": a.brand if a else None, "model": a.model if a else None, "serial": a.serial if a else None,
            "holder_name": u.name if u else None, "phone": req.contact_phone, "address": prop.address if prop else None,
            "warranty_ends_on": w.ends_on.isoformat() if w else None}


def request_out(db: Session, req: ServiceRequest, detail: bool = True) -> dict:
    quotes = sorted(db.scalars(select(ServiceQuote).where(ServiceQuote.request_id == req.id)),
                    key=lambda q: int(q.label.split()[-1]))
    calls = _ordered(db.scalars(select(ServiceCall).where(ServiceCall.request_id == req.id, ServiceCall.purpose == "cotizar")))
    by_call = {q.call_id: q for q in quotes}
    ap = db.scalar(select(ServiceAppointment).where(ServiceAppointment.request_id == req.id, ServiceAppointment.status != "cancelada")
                   .order_by(ServiceAppointment.created_at.desc()))
    warranty = None
    if req.asset_id:
        w = db.scalar(select(Warranty).where(Warranty.asset_id == req.asset_id))
        if w and w.ends_on >= today_mx():
            warranty = {"ends_on": w.ends_on.isoformat(), "days_left": (w.ends_on - today_mx()).days, "provider": w.provider}
    prop = db.get(Property, req.property_id) if req.property_id else None
    out = {
        "id": str(req.id), "origin": req.origin, "route": req.route, "status": req.status, "equipment_label": req.equipment_label,
        "asset_id": str(req.asset_id) if req.asset_id else None, "care_task_id": str(req.care_task_id) if req.care_task_id else None,
        "symptom": req.symptom, "scope_text": req.scope_text, "specialty": req.specialty, "urgency": req.urgency,
        "safety": safety.alert_out(req.safety_alert, req.safety_acknowledged), "warranty": warranty,
        "zone": ", ".join(x for x in [req.zone_colony or (prop.colony if prop else None), req.zone_city or (prop.city if prop else None)] if x) or None,
        "address_complete": bool(prop and prop.lat is not None), "radius_km": req.radius_km, "target_quotes": req.target_quotes,
        "created_at": req.created_at.isoformat(), "quote_count": len(quotes),
        "appointment": appointment_out(db, ap) if ap else None,
        "manufacturer": _manufacturer_out(db, req, prop) if req.route == "fabricante" else None,
    }
    if detail:
        tags = _tags(quotes)
        out["quotes"] = [quote_out(q, tags[q.id]) for q in quotes]
        out["calls"] = [{"label": c.label, "distance_km": c.distance_km, "status": c.status,
                         "price_min": by_call[c.id].price_min if c.id in by_call else None,
                         "price_max": by_call[c.id].price_max if c.id in by_call else None} for c in calls]
    return out

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Organization, ServiceAppointment, ServiceQuote, ServiceRequest, User
from ..security import current_org, current_user
from ..services import call_results
from ..services import requests_flow as F
from ..services.scope import ScopeWriter, get_scope_writer
from ..services.voice import VoiceCaller, get_voice

router = APIRouter(tags=["servicios"])


class NewRequest(BaseModel):
    asset_id: uuid.UUID | None = None
    equipment_label: str | None = Field(default=None, max_length=200)
    symptom: str | None = Field(default=None, max_length=2000)
    urgency: str | None = None


class ScopeIn(BaseModel):
    scope_text: str | None = Field(default=None, min_length=5, max_length=1000)
    route: str | None = Field(default=None, pattern="^(tecnico|fabricante)$")
    urgency: str | None = Field(default=None, pattern="^(hoy|semana|sin_prisa)$")
    property_id: uuid.UUID | None = None


class StartIn(BaseModel):
    consent: bool = False
    phone: str | None = Field(default=None, max_length=30)  # solo para la ruta del fabricante


class ScheduleIn(BaseModel):
    quote_id: uuid.UUID
    slot_index: int = 0
    consent: bool = False
    share_phone: bool = False
    access_notes: str | None = Field(default=None, max_length=300)


class RespondIn(BaseModel):
    accept: bool = False
    slot_index: int | None = Field(default=None, ge=0, le=10)


class RegisterIn(BaseModel):
    date: date
    window: str = Field(pattern="^(manana|tarde)$")
    folio: str | None = Field(default=None, max_length=60)
    center_name: str | None = Field(default=None, max_length=200)
    center_address: str | None = Field(default=None, max_length=300)


class DoneIn(BaseModel):
    final_cost: float | None = Field(default=None, ge=0, le=1_000_000)


def _req(db: Session, org: Organization, request_id: uuid.UUID, advance: bool = True) -> ServiceRequest:
    r = db.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.organization_id == org.id))
    if not r:
        raise HTTPException(404, "No encontramos esa solicitud.")
    if advance:
        F.advance_fake(db, r)
        call_results.settle(db, r, get_voice())
        db.refresh(r)
    return r


@router.post("/service-requests", status_code=201)
def create(body: NewRequest, user: User = Depends(current_user), org: Organization = Depends(current_org),
           db: Session = Depends(get_db), writer: ScopeWriter = Depends(get_scope_writer)):
    r, _ = F.create_request(db, org, user, asset_id=body.asset_id, equipment_label=body.equipment_label,
                            symptom=body.symptom, urgency=body.urgency, writer=writer)
    return F.request_out(db, r)


@router.post("/care/{task_id}/quote-request")
def from_task(task_id: uuid.UUID, user: User = Depends(current_user), org: Organization = Depends(current_org),
              db: Session = Depends(get_db), writer: ScopeWriter = Depends(get_scope_writer)):
    r, created = F.create_request(db, org, user, care_task_id=task_id, writer=writer)
    return F.request_out(db, r)


@router.get("/service-requests")
def list_requests(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(ServiceRequest).where(ServiceRequest.organization_id == org.id).order_by(ServiceRequest.created_at.desc())))
    for r in rows:
        if r.status in ("buscando", "agendada"):
            F.advance_fake(db, r)
            call_results.settle(db, r, get_voice())
    return {"requests": [F.request_out(db, r, detail=False) for r in rows]}


@router.get("/service-requests/{request_id}")
def get_request(request_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return F.request_out(db, _req(db, org, request_id))


@router.post("/service-requests/{request_id}/scope")
def set_scope(request_id: uuid.UUID, body: ScopeIn, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    r = _req(db, org, request_id, advance=False)
    if r.status != "borrador":
        raise HTTPException(409, "Esta solicitud ya está en marcha.")
    if body.scope_text:
        r.scope_text = body.scope_text.strip()
    if body.route:
        r.route = body.route
    if body.urgency:
        r.urgency = body.urgency
    if body.property_id:
        F.set_property(db, org, r, body.property_id)
    db.commit()
    return F.request_out(db, r)


@router.post("/service-requests/{request_id}/ack-safety")
def ack_safety(request_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    r = _req(db, org, request_id, advance=False)
    r.safety_acknowledged = True
    db.commit()
    return F.request_out(db, r)


@router.post("/service-requests/{request_id}/start")
def start(request_id: uuid.UUID, body: StartIn, user: User = Depends(current_user), org: Organization = Depends(current_org),
          db: Session = Depends(get_db), voice: VoiceCaller = Depends(get_voice)):
    r = _req(db, org, request_id, advance=False)
    F.start(db, r, user, org, body.consent, voice, body.phone)
    return F.request_out(db, r)


@router.post("/service-requests/{request_id}/expand")
def expand(request_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db),
           voice: VoiceCaller = Depends(get_voice)):
    r = _req(db, org, request_id, advance=False)
    F.expand(db, r, voice)
    return F.request_out(db, r)


@router.post("/service-requests/{request_id}/cancel")
def cancel(request_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    r = _req(db, org, request_id, advance=False)
    if r.status in ("terminada", "cancelada"):
        raise HTTPException(409, "Esta solicitud ya terminó.")
    r.status = "cancelada"
    from ..models import ServiceCall
    for c in db.scalars(select(ServiceCall).where(ServiceCall.request_id == r.id, ServiceCall.status == "en_cola")):
        c.status = "cancelada"
    for ap in db.scalars(select(ServiceAppointment).where(ServiceAppointment.request_id == r.id, ServiceAppointment.status.in_(["por_confirmar", "confirmada"]))):
        ap.status = "cancelada"
    db.commit()
    return F.request_out(db, r)


@router.get("/service-requests/{request_id}/quotes/{quote_id}")
def get_quote(request_id: uuid.UUID, quote_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    r = _req(db, org, request_id)
    q = db.scalar(select(ServiceQuote).where(ServiceQuote.id == quote_id, ServiceQuote.request_id == r.id))
    if not q:
        raise HTTPException(404, "No encontramos esa cotización.")
    quotes = list(db.scalars(select(ServiceQuote).where(ServiceQuote.request_id == r.id)))
    return {"quote": F.quote_out(q, F._tags(quotes)[q.id]), "scope_text": r.scope_text, "equipment_label": r.equipment_label}


@router.post("/service-requests/{request_id}/schedule")
def schedule(request_id: uuid.UUID, body: ScheduleIn, user: User = Depends(current_user), org: Organization = Depends(current_org),
             db: Session = Depends(get_db)):
    r = _req(db, org, request_id)
    F.schedule(db, r, user, org, body.quote_id, body.slot_index, body.consent, body.share_phone, get_voice(), body.access_notes)
    return F.request_out(db, r)


@router.post("/appointments/{appointment_id}/respond")
def respond_appointment(appointment_id: uuid.UUID, body: RespondIn, org: Organization = Depends(current_org), db: Session = Depends(get_db),
                        voice: VoiceCaller = Depends(get_voice)):
    ap = _appointment(db, org, appointment_id)
    r = db.get(ServiceRequest, ap.request_id)
    F.respond(db, r, ap, body.accept, body.slot_index, voice)
    db.commit()
    return F.request_out(db, r)


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: uuid.UUID, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    ap = _appointment(db, org, appointment_id)
    if ap.status in ("cancelada", "realizada"):
        raise HTTPException(409, "Esta cita ya no se puede cancelar.")
    ap.status = "cancelada"
    r = db.get(ServiceRequest, ap.request_id)
    r.status = "lista" if ap.provider_kind == "tecnico" else "sin_cita"
    r.chosen_quote_id = None
    db.commit()
    return F.request_out(db, r)


@router.post("/service-requests/{request_id}/register")
def register_appointment(request_id: uuid.UUID, body: RegisterIn, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """La persona agendó por su cuenta con el fabricante (p. ej. tras 'agéndala tú') y nos dice cuándo quedó."""
    from datetime import datetime, timedelta
    r = _req(db, org, request_id, advance=False)
    if r.status not in ("sin_cita", "sin_respuesta", "borrador", "lista") or r.route != "fabricante":
        raise HTTPException(409, "No se puede registrar una cita en esta solicitud.")
    hora = 16 if body.window == "tarde" else 10
    start = datetime.combine(body.date, datetime.min.time(), F.TZ).replace(hour=hora)
    db.add(ServiceAppointment(request_id=r.id, provider_kind="fabricante", location_type="centro", center_name=body.center_name,
                              center_address=body.center_address, folio=body.folio, starts_at=start, ends_at=start + timedelta(hours=3),
                              status="confirmada", registered_by_user=True))
    r.status = "agendada"
    db.commit()
    return F.request_out(db, r)


@router.post("/appointments/{appointment_id}/done")
def done(appointment_id: uuid.UUID, body: DoneIn, user: User = Depends(current_user), org: Organization = Depends(current_org),
         db: Session = Depends(get_db)):
    ap = _appointment(db, org, appointment_id)
    if ap.status != "confirmada":
        raise HTTPException(409, "Solo se puede cerrar una cita confirmada.")
    r = db.get(ServiceRequest, ap.request_id)
    F.finish(db, r, ap, user, body.final_cost)
    return F.request_out(db, r)


def _appointment(db: Session, org: Organization, appointment_id: uuid.UUID) -> ServiceAppointment:
    ap = db.scalar(select(ServiceAppointment).join(ServiceRequest, ServiceRequest.id == ServiceAppointment.request_id)
                   .where(ServiceAppointment.id == appointment_id, ServiceRequest.organization_id == org.id))
    if not ap:
        raise HTTPException(404, "No encontramos esa cita.")
    return ap

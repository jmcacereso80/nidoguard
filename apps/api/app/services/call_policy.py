"""Reglas de las llamadas reales: horario, descanso de cada tecnico y topes de costo. Todo es funcion pura o consulta simple."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ServiceCall, ServiceProvider

TZ = ZoneInfo("America/Mexico_City")
SPENT_STATUS = ("completada", "sin_respuesta", "rechazo", "llamando", "error")


def in_window(now: datetime) -> bool:
    s = get_settings()
    if not s.calls_window_enabled:
        return True
    t = now.astimezone(TZ)
    return t.weekday() < 6 and s.calls_window_start <= t.hour < s.calls_window_end  # lunes a sabado


def next_open(now: datetime) -> datetime:
    """Proxima hora en que se puede llamar (ahora mismo si ya se puede)."""
    s = get_settings()
    if in_window(now):
        return now
    t = now.astimezone(TZ)
    day = t.replace(hour=s.calls_window_start, minute=0, second=0, microsecond=0)
    if t >= day:
        day += timedelta(days=1)
    while day.weekday() == 6:
        day += timedelta(days=1)
    return day.astimezone(timezone.utc)


def cooling_down(db: Session, p: ServiceProvider, request_id, now: datetime) -> bool:
    """True si otra solicitud ya le llamo hace menos de N dias. Los tecnicos de prueba no descansan."""
    if p.source == "prueba":
        return False
    since = now - timedelta(days=get_settings().calls_provider_cooldown_days)
    return bool(db.scalar(select(ServiceCall.id).where(
        ServiceCall.provider_id == p.id, ServiceCall.request_id != request_id, ServiceCall.created_at > since,
        ServiceCall.status.in_(SPENT_STATUS)).limit(1)))


def spent(db: Session, request_id=None, since: datetime | None = None) -> float:
    q = select(func.coalesce(func.sum(ServiceCall.cost_usd), 0.0))
    if request_id is not None:
        q = q.where(ServiceCall.request_id == request_id)
    if since is not None:
        q = q.where(ServiceCall.created_at >= since)
    return float(db.scalar(q) or 0.0)


def over_budget(db: Session, request_id, now: datetime) -> bool:
    s = get_settings()
    day = now.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return spent(db, request_id) >= s.max_cost_per_request_usd or spent(db, since=day) >= s.max_cost_per_day_usd

"""Llamadas de voz detras de una interfaz: VoiceCaller. 'fake' simula todo con retardos y no llama a nadie;
'retell' (etapa B) hace llamadas reales y recibe los resultados por webhook."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ServiceCall, ServiceRequest


@dataclass
class CallContext:
    kind: str  # cotizar | fabricante
    service: str  # alcance confirmado
    equipment: str
    symptom: str | None
    urgency: str
    zone: str  # colonia y ciudad, nunca la direccion exacta
    business_name: str | None = None  # solo para saludar al contestar
    extra: dict = field(default_factory=dict)  # fabricante: marca, modelo, serie, fecha de compra, datos del titular


class VoiceCaller(Protocol):
    name: str

    def place(self, db: Session, call: ServiceCall, ctx: CallContext) -> None:
        """Pone la llamada en marcha. No debe bloquear."""

    def collect(self, db: Session, req: ServiceRequest, now: datetime) -> None:
        """Recoge resultados pendientes. Con webhook (Retell) no hace nada."""


class FakeVoice:
    """Cada llamada 'termina' unos segundos despues de la anterior; el resultado lo decide el flujo de cotizaciones."""
    name = "fake"

    def place(self, db, call, ctx):
        slot = int(ctx.extra.get("slot", 0))
        call.status = "en_cola"
        call.scheduled_for = datetime.now(timezone.utc) + timedelta(seconds=get_settings().fake_voice_step_seconds * (slot + 1))

    def collect(self, db, req, now):
        return None  # lo hace flows.advance_fake


def get_voice() -> VoiceCaller:
    if get_settings().voice == "retell":
        from .retell import RetellCaller  # etapa B
        return RetellCaller()
    return FakeVoice()

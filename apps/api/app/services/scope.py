"""Redacta el alcance a cotizar a partir de una tarea de Cuidado o de lo que cuenta la persona.
Interfaz + implementacion con Claude + falsa para pruebas. La persona siempre puede corregirlo antes de que se llame a nadie."""
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from ..config import get_settings
from .providers import SPECIALTIES, specialty_for

Urgency = Literal["hoy", "semana", "sin_prisa"]


class ScopeDraft(BaseModel):
    scope_text: str = Field(description="Lo que se le va a pedir cotizar al tecnico, en una o dos frases en espanol de Mexico, sin jerga. "
                                        "Para una falla: revision del problema y precio aproximado de la reparacion. Sin marcas ni nombres de personas")
    specialty: Literal["aire_acondicionado", "refrigeracion", "lavadoras", "estufas_hornos", "boiler", "electrodomesticos"]
    urgency: Urgency
    safety_concern: bool = Field(description="true solo si lo que cuenta la persona sugiere riesgo fisico (gas, chispas, humo, descarga, agua con electricidad)")


PROMPT = (
    "Eres el concierge de NidoGuard, para hogares en Mexico. Te doy un equipo y un cuidado pendiente o un problema que "
    "cuenta la persona. Redacta lo que se va a cotizar con un tecnico: claro, concreto y corto, en espanol de Mexico y lenguaje simple. "
    "Si es una falla, el alcance es revisar y diagnosticar el problema y dar un precio aproximado de la reparacion (no inventes la causa). "
    "Elige la especialidad de la lista y la urgencia (hoy, semana, sin_prisa) segun lo que cuente la persona; si no dice, usa semana. "
    "No incluyas direcciones, telefonos ni nombres de personas."
)


class ScopeWriter(Protocol):
    name: str

    def write(self, equipment: str, category: str | None, brand: str | None, model: str | None,
              task_title: str | None, symptom: str | None, urgency: str | None) -> ScopeDraft: ...


class ClaudeScopeWriter:
    def __init__(self, model: str | None = None):
        import anthropic
        s = get_settings()
        self.client = anthropic.Anthropic(api_key=s.claude_key)
        self.name = model or s.care_model

    def write(self, equipment, category, brand, model, task_title, symptom, urgency):
        datos = [f"Equipo: {equipment}", f"Tipo: {category or 'no se sabe'}"]
        if brand:
            datos.append(f"Marca: {brand}")
        if model:
            datos.append(f"Modelo: {model}")
        if task_title:
            datos.append(f"Cuidado pendiente: {task_title}")
        if symptom:
            datos.append(f"Lo que cuenta la persona: {symptom}")
        if urgency:
            datos.append(f"Urgencia elegida: {urgency}")
        tool = {"name": "registrar_alcance", "description": "Registra el alcance a cotizar", "input_schema": ScopeDraft.model_json_schema()}
        resp = self.client.messages.create(
            model=self.name, max_tokens=800, tools=[tool], tool_choice={"type": "tool", "name": "registrar_alcance"},
            messages=[{"role": "user", "content": PROMPT + "\n\n" + "\n".join(datos)}])
        block = next(b for b in resp.content if b.type == "tool_use")
        return ScopeDraft.model_validate(block.input)


class FakeScopeWriter:
    name = "falso"

    def write(self, equipment, category, brand, model, task_title, symptom, urgency):
        if task_title:
            text = f"{task_title.rstrip('.')} de {equipment}."
        else:
            text = f"Revisar y reparar {equipment}. Problema: {(symptom or '').strip().rstrip('.')}. Dar un precio aproximado de la reparación."
        return ScopeDraft(scope_text=text, specialty=specialty_for(category or equipment),
                          urgency=urgency if urgency in ("hoy", "semana", "sin_prisa") else "semana", safety_concern=False)


def get_scope_writer() -> ScopeWriter:
    return ClaudeScopeWriter() if get_settings().claude_key else FakeScopeWriter()

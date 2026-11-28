"""Cuidados de un equipo: reglas de fechas y generador con IA detras de una interfaz (como PlateReader)."""
import calendar
from datetime import date, timedelta
from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator

from ..config import get_settings

Unit = Literal["dia", "semana", "mes", "anio"]
Priority = Literal["alta", "media", "baja"]
MAX_TASKS = 8
MIN_TASKS = 3
MAX_TECH_TASKS = 3
PLAN_VERSION = 2  # sube cuando cambia el prompt: los planes compartidos sin verificar se regeneran una vez


def add_every(d: date, n: int, unit: str) -> date:
    """Suma n dias, semanas, meses o anios de calendario (31 ene + 1 mes = 28 feb)."""
    if unit == "dia":
        return d + timedelta(days=n)
    if unit == "semana":
        return d + timedelta(weeks=n)
    months = n if unit == "mes" else n * 12 if unit == "anio" else None
    if months is None:
        raise ValueError(f"Unidad desconocida: {unit}")
    total = d.year * 12 + (d.month - 1) + months
    y, m = divmod(total, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def first_due(today: date, n: int, unit: str) -> date:
    """Primera fecha de un cuidado nuevo: lo que dura su frecuencia, pero nunca mas de 30 dias,
    para que la primera revision llegue pronto y despues siga su ritmo."""
    return min(add_every(today, n, unit), today + timedelta(days=30))


class CareItem(BaseModel):
    title: str = Field(description="Que hacer, en espanol de Mexico, con verbo en infinitivo. Maximo 70 caracteres")
    detail: str = Field(description="Para que sirve, en una frase corta (maximo 100 caracteres)")
    instructions: str = Field(description="Pasos claros y simples, uno por linea, sin jerga tecnica. Empieza con apagar y desconectar si aplica")
    every_n: int = Field(ge=1, le=60, description="Cada cuantas unidades")
    every_unit: Unit = Field(description="dia, semana, mes o anio")
    priority: Priority = Field(description="alta si afecta seguridad o evita danos; media; baja si es comodidad")
    needs_technician: bool = Field(default=False, description="true solo si lo debe hacer un tecnico profesional (abrir el equipo, gas, refrigerante, electricidad por dentro)")

    @field_validator("title", "detail", "instructions", mode="before")
    @classmethod
    def _limpia(cls, v):
        return v.strip() if isinstance(v, str) else v


class CarePlan(BaseModel):
    tasks: list[CareItem] = Field(description=f"Entre {MIN_TASKS} y {MAX_TASKS} cuidados, con frecuencias distintas")


PROMPT = (
    "Eres el concierge de mantenimiento de NidoGuard, para hogares en Mexico. Te doy el tipo de equipo y, si se conocen, "
    "su marca y modelo. Propon los cuidados recurrentes que de verdad alargan la vida de ese tipo de equipo, "
    f"entre {MIN_TASKS} y {MAX_TASKS}, con frecuencias variadas (diario, semanal, mensual, cada 3 o 6 meses, anual o cada 2 anios, "
    "segun lo que corresponda; no fuerces una frecuencia si no hace falta). "
    "Reglas: lenguaje simple, sin jerga tecnica, en espanol de Mexico. Son recomendaciones GENERALES por tipo de equipo: "
    "NO inventes cifras, codigos, piezas ni pasos propios del modelo; si algo depende del modelo, dilo asi: 'revisa tu manual'. "
    "Los cuidados que hace la persona NO requieren abrir el equipo ni tocar la electricidad por dentro. "
    f"Si el tipo de equipo de verdad necesita un servicio profesional (por ejemplo, mantenimiento preventivo anual), agrega de 1 a {MAX_TECH_TASKS} "
    "con needs_technician=true, con frecuencia realista y titulo como 'Mantenimiento preventivo con un tecnico'; sus instrucciones dicen que revise un tecnico y que pasos NO debe intentar la persona. "
    "Si no hace falta ninguno, no inventes uno. "
    "Cada cuidado lleva titulo, para que sirve, instrucciones paso a paso, frecuencia y prioridad."
)


class CarePlanner(Protocol):
    name: str

    def plan(self, category: str | None, name: str, brand: str | None, model: str | None) -> CarePlan: ...


class ClaudeCarePlanner:
    def __init__(self, model: str | None = None):
        import anthropic
        s = get_settings()
        self.client = anthropic.Anthropic(api_key=s.claude_key)
        self.name = model or s.care_model

    def plan(self, category: str | None, name: str, brand: str | None, model: str | None) -> CarePlan:
        datos = [f"Tipo de equipo: {category or name}"]
        if brand:
            datos.append(f"Marca: {brand}")
        if model:
            datos.append(f"Modelo: {model}")
        tool = {"name": "registrar_cuidados", "description": "Registra los cuidados recomendados",
                "input_schema": CarePlan.model_json_schema()}
        kwargs = dict(
            model=self.name, max_tokens=3000, tools=[tool],
            tool_choice={"type": "tool", "name": "registrar_cuidados"},
            messages=[{"role": "user", "content": PROMPT + "\n\n" + "\n".join(datos)}],
        )
        try:
            resp = self.client.messages.create(**kwargs)
        except Exception as e:
            if "tool_choice" not in str(e):
                raise
            resp = self.client.messages.create(**{**kwargs, "tool_choice": {"type": "auto"}})
        block = next(b for b in resp.content if b.type == "tool_use")
        return CarePlan.model_validate(block.input)


def get_planner() -> CarePlanner:
    return ClaudeCarePlanner()

"""Lectura de placas con IA detras de una interfaz, para poder cambiar de proveedor."""
import base64
import io
from typing import Protocol

from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from ..config import get_settings


class Field_(BaseModel):
    value: str | None = Field(default=None, description="Valor leido tal cual, o null si no se lee")
    confidence: float = Field(default=0.0, ge=0, le=1)


class PlateExtraction(BaseModel):
    legible: bool = Field(description="false si la foto no permite leer la placa")
    suggested_name: str | None = Field(default=None, description="Nombre corto en espanol, p. ej. 'Lavadora'")
    category: Field_ = Field(default_factory=Field_)
    brand: Field_ = Field(default_factory=Field_)
    model: Field_ = Field(default_factory=Field_)
    serial: Field_ = Field(default_factory=Field_)
    product_number: Field_ = Field(default_factory=Field_)
    manufacture_date: Field_ = Field(default_factory=Field_)
    voltage: Field_ = Field(default_factory=Field_)
    frequency: Field_ = Field(default_factory=Field_)
    power: Field_ = Field(default_factory=Field_)
    capacity: Field_ = Field(default_factory=Field_)
    refrigerant: Field_ = Field(default_factory=Field_)
    country: Field_ = Field(default_factory=Field_)
    certifications: Field_ = Field(default_factory=Field_)
    transcript: str = Field(default="", description="Todo el texto visible de la placa, literal")


FIELD_NAMES = ["category", "brand", "model", "serial", "product_number", "manufacture_date", "voltage",
               "frequency", "power", "capacity", "refrigerant", "country", "certifications"]

PROMPT = (
    "Eres un lector de placas de equipos del hogar (lavadoras, refrigeradores, aires, televisores, etc.). "
    "Lee la foto de la placa de datos. Reglas: copia los valores EXACTAMENTE como aparecen; si un dato no "
    "se ve o no estas seguro, usa null y confianza baja; NUNCA inventes ni completes con lo que sabes de la "
    "marca. Marca legible=false si la foto esta borrosa, cortada o no muestra una placa. "
    "En 'category' usa una palabra en espanol (lavadora, refrigerador, aire acondicionado, television...). "
    "'suggested_name' es un nombre corto en espanol para el equipo. 'transcript' es todo el texto visible."
)


class PlateReader(Protocol):
    name: str

    def read(self, image: bytes, content_type: str) -> PlateExtraction: ...


def prepare_image(raw: bytes, max_side: int = 1800) -> tuple[bytes, str]:
    """Corrige la rotacion, quita EXIF (ubicacion GPS, etc.) y reduce el tamano."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)  # al re-guardar no se copia el EXIF
    return out.getvalue(), "image/jpeg"


class ClaudePlateReader:
    def __init__(self, model: str | None = None, effort: str | None = "medium"):
        import anthropic
        s = get_settings()
        self.client = anthropic.Anthropic(api_key=s.claude_key)
        self.name = model or s.plate_model
        self.effort = effort

    def read(self, image: bytes, content_type: str) -> PlateExtraction:
        data, mt = prepare_image(image)
        tool = {"name": "registrar_placa", "description": "Registra los datos leidos de la placa",
                "input_schema": PlateExtraction.model_json_schema()}
        kwargs = dict(
            model=self.name, max_tokens=2000, tools=[tool],
            tool_choice={"type": "tool", "name": "registrar_placa"},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mt,
                                             "data": base64.b64encode(data).decode()}},
                {"type": "text", "text": PROMPT}]}],
        )
        if self.effort:
            kwargs["extra_body"] = {"output_config": {"effort": self.effort}}
        try:
            resp = self.client.messages.create(**kwargs)
        except Exception:
            if not self.effort:
                raise
            kwargs.pop("extra_body")
            resp = self.client.messages.create(**kwargs)
        block = next(b for b in resp.content if b.type == "tool_use")
        return PlateExtraction.model_validate(block.input)


def get_reader() -> PlateReader:
    return ClaudePlateReader()


def get_fallback_reader() -> PlateReader:
    return ClaudePlateReader(model=get_settings().plate_fallback_model, effort="medium")

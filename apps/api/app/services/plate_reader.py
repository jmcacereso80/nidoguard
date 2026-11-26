"""Lectura de placas con IA detras de una interfaz, para poder cambiar de proveedor."""
import base64
import io
from typing import Protocol

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()  # los iPhone guardan HEIC; Pillow solo no lo abre
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
    transcript: str = Field(default="", description="Todo el texto visible de la placa, literal")


# Se estandariza a tres datos para todos los equipos (televisores, hornos, etc. no traen mas).
# El tipo ("category") solo sirve para ponerle nombre al equipo. Lo demas (voltaje, capacidad...)
# queda en la transcripcion literal y se aprovechara despues en documentos y cuidado.
FIELD_NAMES = ["category", "brand", "model", "serial"]

PROMPT = (
    "Eres un lector de placas de equipos del hogar (lavadoras, refrigeradores, aires, televisores, etc.). "
    "Recibes fotos etiquetadas: 'placa de datos' (puede haber varias, de la misma placa) y 'equipo completo'. "
    "De las placas copia marca, modelo y serie EXACTAMENTE como aparecen. La SERIE solo se toma de las placas. "
    "Si la placa no trae marca o modelo, puedes identificarlos en las fotos del equipo completo, SOLO si se ven "
    "con claridad (logotipo, panel, etiqueta a la vista), con la confianza que corresponda. Tambien las fotos del "
    "equipo sirven para el tipo y el nombre. Si un dato no se ve o no estas seguro, usa null y confianza baja; "
    "NUNCA inventes. Marca legible=false solo si ninguna placa es legible. "
    "En 'category' usa una palabra en espanol (lavadora, refrigerador, aire acondicionado, television...). "
    "Extrae SOLO marca, modelo y numero de serie; ignora voltaje, potencia, capacidad y demas datos. "
    "'suggested_name' es un nombre corto en espanol para el equipo. 'transcript' es todo el texto visible."
)


class PlateReader(Protocol):
    name: str

    def read(self, image: bytes, content_type: str, extra: list[tuple[bytes, str, str]] | None = None) -> PlateExtraction: ...


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

    def read(self, image: bytes, content_type: str, extra: list[tuple[bytes, str, str]] | None = None) -> PlateExtraction:
        tool = {"name": "registrar_placa", "description": "Registra los datos leidos de la placa",
                "input_schema": PlateExtraction.model_json_schema()}
        content = []
        photos = [(image, "placa")] + [(e[0], e[2]) for e in (extra or [])]
        for i, (raw, kind) in enumerate(photos, start=1):
            data, mt = prepare_image(raw)
            label = f"Foto {i}: {'placa de datos' if kind == 'placa' else 'equipo completo'}."
            content.append({"type": "text", "text": label})
            content.append({"type": "image", "source": {"type": "base64", "media_type": mt,
                                                        "data": base64.b64encode(data).decode()}})
        content.append({"type": "text", "text": PROMPT})
        kwargs = dict(
            model=self.name, max_tokens=2000, tools=[tool],
            tool_choice={"type": "tool", "name": "registrar_placa"},
            messages=[{"role": "user", "content": content}],
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

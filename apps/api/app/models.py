import enum
import uuid
from datetime import date, datetime
from sqlalchemy import (
    Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, Boolean, Float, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def now():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KitStatus(str, enum.Enum):
    fabricado = "fabricado"
    inventario = "inventario"
    vendido = "vendido"
    reclamado = "reclamado"


class TagStatus(str, enum.Enum):
    en_kit = "en_kit"
    disponible = "disponible"
    vinculada = "vinculada"
    reemplazada = "reemplazada"
    baja = "baja"


class AssetStatus(str, enum.Enum):
    registrado = "registrado"
    leido = "leido"
    por_confirmar = "por_confirmar"
    necesita_foto = "necesita_foto"
    faltan_datos = "faltan_datos"
    completo = "completo"


class ReadingStatus(str, enum.Enum):
    procesando = "procesando"
    lista = "lista"
    necesita_foto = "necesita_foto"
    faltan_datos = "faltan_datos"
    error = "error"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    clerk_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(200))
    first_name: Mapped[str | None] = mapped_column(String(120))
    last_name: Mapped[str | None] = mapped_column(String(160))
    phone_e164: Mapped[str | None] = mapped_column(String(20))  # para agendar; solo se comparte con permiso
    created_at: Mapped[datetime] = now()


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = now()


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="owner")
    created_at: Mapped[datetime] = now()
    __table_args__ = (Index("uq_membership", "user_id", "organization_id", unique=True),)


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[uuid.UUID] = pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500))
    street: Mapped[str | None] = mapped_column(String(200))  # calle y numero
    colony: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    search_radius_km: Mapped[int] = mapped_column(Integer, default=15, server_default=text("15"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now()


class Space(Base):
    __tablename__ = "spaces"
    id: Mapped[uuid.UUID] = pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = now()


class TagBatch(Base):
    __tablename__ = "tag_batches"
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(120))
    tags_per_kit: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = now()


class Kit(Base):
    __tablename__ = "kits"
    id: Mapped[uuid.UUID] = pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tag_batches.id"), index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    short_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[KitStatus] = mapped_column(Enum(KitStatus, name="kit_status"), default=KitStatus.fabricado)
    claimed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now()
    tags: Mapped[list["SmartTag"]] = relationship(back_populates="kit")


class SmartTag(Base):
    __tablename__ = "smart_tags"
    id: Mapped[uuid.UUID] = pk()
    kit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kits.id"), index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[TagStatus] = mapped_column(Enum(TagStatus, name="tag_status"), default=TagStatus.en_kit)
    created_at: Mapped[datetime] = now()
    kit: Mapped[Kit] = relationship(back_populates="tags")


class EquipmentAsset(Base):
    __tablename__ = "equipment_assets"
    id: Mapped[uuid.UUID] = pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    tag_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("smart_tags.id"), unique=True)
    space_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("spaces.id"))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus, name="asset_status"), default=AssetStatus.registrado)
    category: Mapped[str | None] = mapped_column(String(80))
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial: Mapped[str | None] = mapped_column(String(120))
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = now()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssetReading(Base):
    __tablename__ = "asset_readings"
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(20))  # ia | manual
    status: Mapped[ReadingStatus] = mapped_column(Enum(ReadingStatus, name="reading_status"), default=ReadingStatus.procesando)
    fields: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    confidence: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    transcript: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now()


class AssetImage(Base):
    __tablename__ = "asset_images"
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # placa | equipo
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(80))
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = now()


class AssetEvent(Base):
    """Historial de solo agregar."""
    __tablename__ = "asset_events"
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = now()


class ClaimAttempt(Base):
    __tablename__ = "claim_attempts"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    ip: Mapped[str | None] = mapped_column(String(64), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = now()


class AssetDocument(Base):
    """Garantia o factura del equipo (archivo privado en R2). El hash evita procesar dos veces el mismo archivo."""
    __tablename__ = "asset_documents"
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # garantia | factura
    filename: Mapped[str] = mapped_column(String(200))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(80))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = now()


class Warranty(Base):
    """Garantia confirmada por la persona: fecha de vencimiento (obligatoria), proveedor y precio (opcionales)."""
    __tablename__ = "warranties"
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), unique=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("asset_documents.id", ondelete="CASCADE"))
    ends_on: Mapped[date] = mapped_column(Date)
    provider: Mapped[str | None] = mapped_column(String(200))
    price: Mapped[float | None] = mapped_column(Float)  # MXN; se puede corregir despues
    updated_at: Mapped[datetime] = now()


class ModelKnowledge(Base):
    """Base de conocimiento por modelo (marca + modelo normalizados): se busca una vez y se reutiliza.
    Es compartida entre hogares: nunca guarda datos de personas (serie, fotos, direccion)."""
    __tablename__ = "model_knowledge"
    id: Mapped[uuid.UUID] = pk()
    model_key: Mapped[str] = mapped_column(String(200), unique=True)
    brand: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20))  # buscando | listo | no_encontrado
    title: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(800))  # primer enlace sugerido
    links: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # hasta 3 paginas: [{url, title}]
    storage_key: Mapped[str | None] = mapped_column(String(500))  # no se usa: no guardamos copias de manuales
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_try_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = now()


class ModelResearchRun(Base):
    """Cada corrida de busqueda de manual (estado, fecha y detalle), para saber que paso."""
    __tablename__ = "model_research_runs"
    id: Mapped[uuid.UUID] = pk()
    model_key: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(20))  # listo | no_encontrado | error
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = now()


class CareTask(Base):
    """Cuidado recurrente de un equipo (p. ej. limpiar el filtro cada 3 meses).
    origen: 'sugerencia' (la propone NidoGuard, por confirmar) o 'manual' (viene del manual del fabricante; fase posterior).
    estado: 'sugerida' (por confirmar), 'confirmada' (la persona dijo 'Me sirve') o 'descartada' ('No aplica')."""
    __tablename__ = "care_tasks"
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(String(300))
    instructions: Mapped[str | None] = mapped_column(Text)
    every_n: Mapped[int] = mapped_column(Integer)
    every_unit: Mapped[str] = mapped_column(String(10))  # dia | semana | mes | anio
    priority: Mapped[str] = mapped_column(String(10), default="media")  # alta | media | baja
    needs_technician: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    source: Mapped[str] = mapped_column(String(12), default="sugerencia")
    status: Mapped[str] = mapped_column(String(12), default="sugerida")
    next_due: Mapped[date] = mapped_column(Date, index=True)
    last_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now()


class CareRecord(Base):
    """Cada vez que la persona marca un cuidado como realizado. Solo se agrega."""
    __tablename__ = "care_records"
    id: Mapped[uuid.UUID] = pk()
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("care_tasks.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_assets.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    done_on: Mapped[date] = mapped_column(Date)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = now()


class CareTemplate(Base):
    """Plan de cuidados aprendido una sola vez y compartido: por marca y modelo ('modelo|lg|wa17') o,
    si no hay modelo, por tipo de equipo ('tipo|lavadora'). No guarda datos de ninguna persona.
    source: 'sugerencia' (propuesto por IA, sin verificar) o 'manual' (leido del manual; fase posterior)."""
    __tablename__ = "care_templates"
    id: Mapped[uuid.UUID] = pk()
    key: Mapped[str] = mapped_column(String(300), unique=True)
    kind: Mapped[str] = mapped_column(String(10))  # modelo | tipo
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(80))
    items: Mapped[list] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(12), default="sugerencia")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    planner: Mapped[str | None] = mapped_column(String(80))
    uses: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = now()


class ServiceProvider(Base):
    """Tecnico del directorio compartido (se busca una vez y se reutiliza). No pertenece a ningun hogar.
    Teléfono, dirección y sitio son solo de uso interno: nunca se entregan a las personas usuarias."""
    __tablename__ = "service_providers"
    id: Mapped[uuid.UUID] = pk()
    source: Mapped[str] = mapped_column(String(20))  # maps | manual | fake
    source_id: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    phone_e164: Mapped[str | None] = mapped_column(String(20), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    colony: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    specialties: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    brands: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    rating: Mapped[float | None] = mapped_column(Float)
    reviews: Mapped[int | None] = mapped_column(Integer)
    hours: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="activo")  # activo | descartado
    do_not_call: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    answered: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    quotes_given: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    last_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = now()


class ProviderSearch(Base):
    """Cada busqueda en el mapa por ciudad y especialidad. La clave unica evita repetirla (y volver a pagar)."""
    __tablename__ = "provider_searches"
    id: Mapped[uuid.UUID] = pk()
    key: Mapped[str] = mapped_column(String(200), unique=True)  # ciudad|especialidad
    city: Mapped[str] = mapped_column(String(120))
    specialty: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20))  # buscando | lista | error
    results: Mapped[int] = mapped_column(Integer, default=0)
    new_providers: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = now()


class ServiceRequest(Base):
    """Solicitud de servicio: viene de una tarea de Cuidado o la abre la persona por su cuenta ('libre').
    status: borrador | buscando | lista | sin_respuesta | agendada | terminada | cancelada
    route: tecnico (va a la casa) | fabricante (centro de servicio)"""
    __tablename__ = "service_requests"
    id: Mapped[uuid.UUID] = pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"))
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("equipment_assets.id", ondelete="SET NULL"), index=True)
    care_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("care_tasks.id", ondelete="SET NULL"), index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    origin: Mapped[str] = mapped_column(String(10))  # tarea | libre
    route: Mapped[str] = mapped_column(String(12), default="tecnico")
    equipment_label: Mapped[str | None] = mapped_column(String(200))
    symptom: Mapped[str | None] = mapped_column(Text)
    scope_text: Mapped[str | None] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(String(40))
    urgency: Mapped[str] = mapped_column(String(12), default="semana")  # hoy | semana | sin_prisa
    safety_alert: Mapped[str | None] = mapped_column(String(20))  # gas | chispas | humo | quemado | agua_electricidad
    safety_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    contact_phone: Mapped[str | None] = mapped_column(String(20))  # solo para la ruta del fabricante, con consentimiento
    status: Mapped[str] = mapped_column(String(14), default="borrador", index=True)
    zone_city: Mapped[str | None] = mapped_column(String(120))
    zone_colony: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[int] = mapped_column(Integer, default=15, server_default=text("15"))
    target_quotes: Mapped[int] = mapped_column(Integer, default=5, server_default=text("5"))
    chosen_quote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ServiceCall(Base):
    """Una llamada hecha por NidoGuard (a un tecnico o al fabricante). Solo uso interno: transcripcion y grabacion
    contienen datos de terceros y nunca se entregan a las personas usuarias."""
    __tablename__ = "service_calls"
    id: Mapped[uuid.UUID] = pk()
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_providers.id"))
    purpose: Mapped[str] = mapped_column(String(12))  # cotizar | agendar | recordatorio | fabricante
    label: Mapped[str | None] = mapped_column(String(20))  # "Técnico 3"
    distance_km: Mapped[float | None] = mapped_column(Float)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(14), default="en_cola")  # en_cola | llamando | completada | sin_respuesta | rechazo | error
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # solo la voz falsa lo usa
    retell_call_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    duration_s: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    transcript: Mapped[str | None] = mapped_column(Text)
    recording_key: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = now()


class ServiceQuote(Base):
    """Lo que dijo un tecnico por telefono, ya estructurado. Es lo unico que ve la persona: sin nombre ni contacto."""
    __tablename__ = "service_quotes"
    id: Mapped[uuid.UUID] = pk()
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_providers.id"))
    call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_calls.id"))
    label: Mapped[str] = mapped_column(String(20))  # "Técnico 1"
    rating: Mapped[float | None] = mapped_column(Float)
    reviews: Mapped[int | None] = mapped_column(Integer)
    distance_km: Mapped[float | None] = mapped_column(Float)
    scope_quoted: Mapped[str | None] = mapped_column(Text)
    includes: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    excludes: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    price_min: Mapped[float | None] = mapped_column(Float)
    price_max: Mapped[float | None] = mapped_column(Float)
    price_type: Mapped[str | None] = mapped_column(String(30))  # fijo | rango | solo_revision | revision_mas_reparacion
    visit_fee: Mapped[float | None] = mapped_column(Float)
    availability: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))  # [{date, window}]
    warranty_days: Mapped[int | None] = mapped_column(Integer)
    invoice: Mapped[bool | None] = mapped_column(Boolean)
    payment_methods: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    matches: Mapped[str | None] = mapped_column(String(10))  # igual | parcial | distinto
    summary: Mapped[str | None] = mapped_column(Text)
    declined: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))  # el tecnico no pudo o no contesto al agendar
    excerpt: Mapped[str | None] = mapped_column(Text)  # lo que dijo el tecnico sobre trabajo y precio, sin nombres ni datos
    confidence: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = now()
    __table_args__ = (Index("uq_quote_request_provider", "request_id", "provider_id", unique=True),)


class ServiceAppointment(Base):
    """Cita acordada: con un tecnico (a domicilio) o con el fabricante (casi siempre en un centro de servicio).
    status: por_confirmar | confirmada | por_reprogramar | cancelada | realizada"""
    __tablename__ = "service_appointments"
    id: Mapped[uuid.UUID] = pk()
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_quotes.id"))
    provider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_providers.id"))
    provider_kind: Mapped[str] = mapped_column(String(10))  # tecnico | fabricante
    location_type: Mapped[str] = mapped_column(String(10), default="domicilio")  # domicilio | centro
    center_name: Mapped[str | None] = mapped_column(String(200))
    center_address: Mapped[str | None] = mapped_column(String(300))
    folio: Mapped[str | None] = mapped_column(String(60))
    bring: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    requested_slot: Mapped[dict | None] = mapped_column(JSONB)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="por_confirmar")
    registered_by_user: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    proposal_round: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))  # veces que el tecnico propuso otra hora
    proposed_slot: Mapped[dict | None] = mapped_column(JSONB)  # {date, start_hour, end_hour}
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    share_phone: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    visit_person: Mapped[str | None] = mapped_column(String(120))  # nombre de pila de quien ira a la visita (lo dice el tecnico al confirmar)
    address_shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    final_cost: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = now()


class Consent(Base):
    """Permisos dados por la persona, con la version del texto que acepto."""
    __tablename__ = "consents"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_requests.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(40))  # llamar_en_su_nombre | compartir_datos_para_visita | compartir_datos_con_fabricante
    text_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = now()


class ManufacturerServiceLine(Base):
    """Linea de servicio de una marca. Solo se llama si status == 'verificada' (la verifica una persona)."""
    __tablename__ = "manufacturer_service_lines"
    id: Mapped[uuid.UUID] = pk()
    brand_key: Mapped[str] = mapped_column(String(80), unique=True)
    brand: Mapped[str] = mapped_column(String(120))
    phone_e164: Mapped[str] = mapped_column(String(20))
    hours: Mapped[str | None] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20), default="telefono", server_default="telefono")
    requires_account_holder: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    data_requested: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    source: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(14), default="por_verificar", server_default="por_verificar")  # por_verificar | verificada | descartada
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = now()

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

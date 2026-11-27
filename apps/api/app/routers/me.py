from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Membership, Organization, Property, Space, User
from ..security import current_org, current_user
from ..services.providers import to_e164_mx
from ..services.geocoder import Geocoder, get_geocoder

router = APIRouter(tags=["cuenta"])

SUGGESTED_SPACES = ["Cocina", "Sala", "Recámara", "Baño", "Lavandería", "Terraza"]


class HomeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AddressIn(BaseModel):
    street: str = Field(min_length=3, max_length=200)
    colony: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    city: str = Field(min_length=2, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    search_radius_km: int = Field(default=15, pattern=None)


class PropertyIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PhoneIn(BaseModel):
    phone: str | None = Field(default=None, max_length=30)


class SpaceIn(BaseModel):
    property_id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    icon: str | None = Field(default=None, max_length=40)


def _address_out(p: Property):
    """La direccion es completa solo si ya tiene coordenadas: sin ellas no se puede buscar tecnicos cerca."""
    return {"street": p.street, "colony": p.colony, "postal_code": p.postal_code, "city": p.city,
            "state": p.state, "search_radius_km": p.search_radius_km,
            "complete": p.lat is not None and p.lng is not None}


def _org_out(db: Session, org: Organization):
    props = db.scalars(select(Property).where(Property.organization_id == org.id).order_by(Property.created_at)).all()
    return {"id": str(org.id), "name": org.name,
            "properties": [{"id": str(p.id), "name": p.name, "address": _address_out(p)} for p in props]}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.scalar(
        select(Organization).join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    return {"user": {"id": str(user.id), "email": user.email, "name": user.name, "phone": user.phone_e164},
            "home": _org_out(db, org) if org else None,
            "suggested_spaces": SUGGESTED_SPACES}


@router.post("/home", status_code=201)
def create_home(body: HomeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    existing = db.scalar(select(Membership).where(Membership.user_id == user.id))
    if existing:
        org = db.get(Organization, existing.organization_id)
        return _org_out(db, org)
    org = Organization(name=body.name.strip())
    db.add(org)
    db.flush()
    db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    db.add(Property(organization_id=org.id, name=body.name.strip()))
    db.commit()
    return _org_out(db, org)


@router.get("/spaces")
def list_spaces(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    rows = db.scalars(select(Space).where(Space.organization_id == org.id).order_by(Space.created_at)).all()
    return [{"id": str(s.id), "name": s.name, "icon": s.icon, "property_id": str(s.property_id)} for s in rows]


@router.post("/spaces", status_code=201)
def create_space(body: SpaceIn, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    prop = None
    if body.property_id:
        prop = db.scalar(select(Property).where(Property.id == body.property_id, Property.organization_id == org.id))
    else:
        prop = db.scalar(select(Property).where(Property.organization_id == org.id).order_by(Property.created_at))
    if not prop:
        from fastapi import HTTPException
        raise HTTPException(404, "No encontramos esa propiedad")
    s = Space(organization_id=org.id, property_id=prop.id, name=body.name.strip(), icon=body.icon)
    db.add(s)
    db.commit()
    return {"id": str(s.id), "name": s.name, "icon": s.icon, "property_id": str(prop.id)}


@router.post("/properties", status_code=201)
def add_property(body: PropertyIn, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """Otra direccion (casa de la familia, oficina...). Se le pone su direccion con PUT /properties/{id}/address."""
    n = db.scalar(select(func.count()).select_from(Property).where(Property.organization_id == org.id)) or 0
    if n >= 5:
        raise HTTPException(409, "Puedes guardar hasta 5 direcciones.")
    prop = Property(organization_id=org.id, name=body.name.strip())
    db.add(prop)
    db.commit()
    return {"id": str(prop.id), "name": prop.name, "address": _address_out(prop)}


@router.put("/me/phone")
def set_phone(body: PhoneIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Telefono para agendar. No se comparte con el tecnico salvo que la persona lo autorice al agendar."""
    if body.phone is None or not body.phone.strip():
        user.phone_e164 = None
    else:
        e164 = to_e164_mx(body.phone)
        if not e164:
            raise HTTPException(422, "Escribe tu teléfono a 10 dígitos.")
        user.phone_e164 = e164
    db.commit()
    return {"phone": user.phone_e164}


@router.put("/properties/{property_id}/address")
def set_address(property_id: str, body: AddressIn, org: Organization = Depends(current_org),
                db: Session = Depends(get_db), geo: Geocoder = Depends(get_geocoder)):
    prop = db.scalar(select(Property).where(Property.id == property_id, Property.organization_id == org.id))
    if not prop:
        raise HTTPException(404, "No encontramos esa propiedad")
    if body.search_radius_km not in (10, 15, 25):
        raise HTTPException(422, "Elige 10, 15 o 25 km.")
    point = geo.geocode(body.street.strip(), body.colony, body.postal_code, body.city.strip(), body.state)
    if point is None:
        raise HTTPException(422, "No pudimos ubicar esa dirección en el mapa. Revisa la calle, el número y el código postal.")
    prop.street, prop.colony, prop.postal_code = body.street.strip(), body.colony, body.postal_code
    prop.city, prop.state, prop.search_radius_km = body.city.strip(), body.state, body.search_radius_km
    prop.address = ", ".join(x for x in [prop.street, prop.colony, prop.city, prop.state] if x)
    prop.lat, prop.lng, prop.geocoded_at = point.lat, point.lng, datetime.now(timezone.utc)
    db.commit()
    return _address_out(prop)

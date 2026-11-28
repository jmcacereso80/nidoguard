from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import EquipmentAsset, Membership, Organization, Property, Space, User
from ..security import current_org, current_user
from ..services.providers import to_e164_mx
from ..services.people import full_name
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
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_primary: bool | None = None


class PropertyIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProfileIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)


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
            "complete": p.lat is not None and p.lng is not None, "is_primary": p.is_primary}


def _org_out(db: Session, org: Organization):
    props = db.scalars(select(Property).where(Property.organization_id == org.id).order_by(Property.is_primary.desc(), Property.created_at)).all()
    counts = dict(db.execute(select(Space.property_id, func.count(EquipmentAsset.id)).join(EquipmentAsset, EquipmentAsset.space_id == Space.id)
                             .where(Space.organization_id == org.id).group_by(Space.property_id)).all())
    return {"id": str(org.id), "name": org.name,
            "properties": [{"id": str(p.id), "name": p.name, "address": _address_out(p), "assets_count": counts.get(p.id, 0)} for p in props]}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.scalar(
        select(Organization).join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    return {"user": {"id": str(user.id), "email": user.email, "name": full_name(user), "first_name": user.first_name,
                     "last_name": user.last_name, "phone": user.phone_e164},
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
    db.add(Property(organization_id=org.id, name=body.name.strip(), is_primary=True))
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
        prop = db.scalar(select(Property).where(Property.organization_id == org.id).order_by(Property.is_primary.desc(), Property.created_at))
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
    prop = Property(organization_id=org.id, name=body.name.strip(), is_primary=n == 0)
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


@router.put("/me/profile")
def set_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Nombres, apellidos y telefono. El telefono solo se cambia si viene en la peticion."""
    user.first_name = body.first_name.strip()
    user.last_name = (body.last_name or "").strip() or None
    user.name = full_name(user)
    if "phone" in body.model_fields_set:
        if body.phone is None or not body.phone.strip():
            user.phone_e164 = None
        else:
            e164 = to_e164_mx(body.phone)
            if not e164:
                raise HTTPException(422, "Escribe tu teléfono a 10 dígitos.")
            user.phone_e164 = e164
    db.commit()
    return {"first_name": user.first_name, "last_name": user.last_name, "name": user.name, "phone": user.phone_e164}


@router.delete("/properties/{property_id}")
def delete_property(property_id: str, move_to: str | None = None, org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    """Quita una direccion. Sus lugares (y equipos) no se borran: se pasan a otra direccion."""
    prop = db.scalar(select(Property).where(Property.id == property_id, Property.organization_id == org.id))
    if not prop:
        raise HTTPException(404, "No encontramos esa dirección")
    otras = db.scalars(select(Property).where(Property.organization_id == org.id, Property.id != prop.id)
                       .order_by(Property.is_primary.desc(), Property.created_at)).all()
    if not otras:
        raise HTTPException(409, "Es tu única dirección. Agrega otra antes de quitarla.")
    n_spaces = db.scalar(select(func.count()).select_from(Space).where(Space.property_id == prop.id)) or 0
    destino = None
    if n_spaces:
        if not move_to:
            raise HTTPException(409, "Esta dirección tiene lugares y equipos. Elige a qué dirección pasarlos.")
        destino = next((o for o in otras if str(o.id) == move_to), None)
        if not destino:
            raise HTTPException(404, "No encontramos la dirección a la que quieres pasarlos")
        for sp in db.scalars(select(Space).where(Space.property_id == prop.id)):
            sp.property_id = destino.id
    was_primary = prop.is_primary
    db.flush()
    from ..models import ServiceRequest
    for r in db.scalars(select(ServiceRequest).where(ServiceRequest.property_id == prop.id)):
        r.property_id = destino.id if destino else None
    db.flush()
    db.delete(prop)
    if was_primary:
        (destino or otras[0]).is_primary = True
    db.commit()
    return _org_out(db, org)


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
    if body.name:
        prop.name = body.name.strip()
    if body.is_primary:
        for o in db.scalars(select(Property).where(Property.organization_id == org.id)):
            o.is_primary = o.id == prop.id
    prop.street, prop.colony, prop.postal_code = body.street.strip(), body.colony, body.postal_code
    prop.city, prop.state, prop.search_radius_km = body.city.strip(), body.state, body.search_radius_km
    prop.address = ", ".join(x for x in [prop.street, prop.colony, prop.city, prop.state] if x)
    prop.lat, prop.lng, prop.geocoded_at = point.lat, point.lng, datetime.now(timezone.utc)
    db.commit()
    return _address_out(prop)

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Membership, Organization, Property, Space, User
from ..security import current_org, current_user

router = APIRouter(tags=["cuenta"])

SUGGESTED_SPACES = ["Cocina", "Sala", "Recámara", "Baño", "Lavandería", "Terraza"]


class HomeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SpaceIn(BaseModel):
    property_id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    icon: str | None = Field(default=None, max_length=40)


def _org_out(db: Session, org: Organization):
    props = db.scalars(select(Property).where(Property.organization_id == org.id)).all()
    return {"id": str(org.id), "name": org.name,
            "properties": [{"id": str(p.id), "name": p.name} for p in props]}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = db.scalar(
        select(Organization).join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    return {"user": {"id": str(user.id), "email": user.email, "name": user.name},
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

import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import Membership, Organization, User

_jwks_client: jwt.PyJWKClient | None = None


def _client() -> jwt.PyJWKClient:
    global _jwks_client
    url = get_settings().clerk_jwks_url
    if not url:
        raise HTTPException(503, "El inicio de sesion no esta configurado")
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(url, cache_keys=True)
    return _jwks_client


def verify_token(token: str) -> dict:
    try:
        key = _client().get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["RS256"], options={"verify_aud": False})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Sesion no valida")


def _user_from_claims(db: Session, claims: dict) -> User:
    clerk_id = claims["sub"]
    user = db.scalar(select(User).where(User.clerk_id == clerk_id))
    if not user:
        user = User(clerk_id=clerk_id, email=claims.get("email"), name=claims.get("name"))
        db.add(user)
        db.commit()
    return user


def optional_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return _user_from_claims(db, verify_token(authorization[7:]))


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(401, "Inicia sesion para continuar")
    return user


def current_org(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Organization:
    org = db.scalar(
        select(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at)
    )
    if not org:
        raise HTTPException(409, "Primero crea tu hogar")
    return org


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"

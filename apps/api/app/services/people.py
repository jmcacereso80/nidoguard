"""Nombre de la persona: nombres + apellidos; si solo hay `name` antiguo, se usa ese."""
from ..models import User


def given_name(user: User | None) -> str | None:
    if not user:
        return None
    if user.first_name and user.first_name.strip():
        return user.first_name.strip().split(" ")[0]
    return (user.name or "").strip().split(" ")[0] or None


def full_name(user: User | None) -> str | None:
    if not user:
        return None
    parts = [x.strip() for x in (user.first_name, user.last_name) if x and x.strip()]
    return " ".join(parts) if parts else ((user.name or "").strip() or None)

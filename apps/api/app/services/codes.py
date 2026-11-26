import hashlib
import secrets

# Sin 0/O/1/I para que se puedan teclear sin confusion.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _rand(n: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def new_activation_code() -> str:
    """Codigo largo de un solo uso que va dentro del QR del kit (120 bits)."""
    return _rand(24)


def new_short_code() -> str:
    """Codigo corto que el usuario puede teclear: XXXXX-XXXXX."""
    raw = _rand(10)
    return f"{raw[:5]}-{raw[5:]}"


def new_tag_token() -> str:
    """Token de la etiqueta que va en la URL /t/<token> (110 bits)."""
    return _rand(22)


def normalize(code: str) -> str:
    return "".join(c for c in code.upper() if c.isalnum())


def hash_code(code: str) -> str:
    return hashlib.sha256(normalize(code).encode()).hexdigest()

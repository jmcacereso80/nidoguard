"""Archivo .ics servido por enlace (el iPhone no abre los enlaces de datos): abre "Agregar a Calendario".

POST /calendar/link (con sesion) firma el evento y devuelve una ruta corta y temporal; GET /calendar/<token>.ics no
necesita sesion (Safari no manda el encabezado) pero solo sirve lo que firmamos, y caduca. No guarda nada en la base.
"""
import base64
import hashlib
import hmac
import json
import time
import zlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security import current_user
from app.models import User

router = APIRouter(tags=["calendar"])
TTL_S = 30 * 60


class EventIn(BaseModel):
    title: str = Field(max_length=200)
    start: datetime
    end: datetime
    location: str | None = Field(default=None, max_length=300)
    details: str = Field(default="", max_length=2000)


def _key() -> bytes:
    s = get_settings()
    return (getattr(s, "calendar_secret", "") or s.clerk_secret_key or "nidoguard-dev").encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(t: str) -> bytes:
    return base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))


def sign(ev: dict, now: float | None = None) -> str:
    body = _b64(zlib.compress(json.dumps({**ev, "exp": int((now or time.time()) + TTL_S)}, ensure_ascii=False).encode()))
    return f"{body}.{_b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:18])}"


def unsign(token: str, now: float | None = None) -> dict:
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(sig, _b64(hmac.new(_key(), body.encode(), hashlib.sha256).digest()[:18])):
            raise ValueError
        ev = json.loads(zlib.decompress(_unb64(body), 0, 20000))
        if ev["exp"] < (now or time.time()):
            raise ValueError
        return ev
    except Exception:
        raise HTTPException(404, "Este enlace ya caducó. Vuelve a tocar Apple en la app.")


def _esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\;").replace("\r", "").replace("\n", "\\n")


def _stamp(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(ev: dict) -> str:
    uid = hashlib.sha1(f"{ev['title']}{ev['start']}".encode()).hexdigest()[:20]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NidoGuard//ES", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "BEGIN:VEVENT", f"UID:{uid}@nidoguard.com",
             f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}", f"DTSTART:{_stamp(ev['start'])}", f"DTEND:{_stamp(ev['end'])}", f"SUMMARY:{_esc(ev['title'])}"]
    if ev.get("location"):
        lines.append(f"LOCATION:{_esc(ev['location'])}")
    if ev.get("details"):
        lines.append(f"DESCRIPTION:{_esc(ev['details'])}")
    lines += ["BEGIN:VALARM", "TRIGGER:-PT1H", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(ev['title'])}", "END:VALARM", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


@router.post("/calendar/link")
def link(body: EventIn, user: User = Depends(current_user)):
    ev = {"title": body.title, "start": body.start.isoformat(), "end": body.end.isoformat(), "location": body.location, "details": body.details}
    return {"path": f"/calendar/{sign(ev)}.ics"}


@router.get("/calendar/{token}.ics")
def ics(token: str):
    return Response(build_ics(unsign(token)), media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'inline; filename="nidoguard.ics"', "Cache-Control": "no-store"})

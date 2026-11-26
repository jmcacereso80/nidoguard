import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..services import call_results
from ..services.quote_extractor import Extractor, get_extractor
from ..services.retell import verify_signature
from ..services.voice import VoiceCaller, get_voice

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/retell")
async def retell(request: Request, x_retell_signature: str | None = Header(default=None), db: Session = Depends(get_db),
                 extractor: Extractor = Depends(get_extractor), voice: VoiceCaller = Depends(get_voice)):
    raw = await request.body()
    if not verify_signature(raw, x_retell_signature, get_settings().retell_api_key):
        raise HTTPException(401, "Firma inválida.")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Cuerpo inválido.")
    return {"ok": True, "result": call_results.handle_event(db, payload, extractor, voice)}

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import assets, care, documents, kits, me, service_requests, tags, webhooks

_h = logging.StreamHandler()
_h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
_l = logging.getLogger("nidoguard")
_l.setLevel(logging.INFO)
if not _l.handlers:
    _l.addHandler(_h)

app = FastAPI(title="NidoGuard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(me.router)
app.include_router(kits.router)
app.include_router(tags.router)
app.include_router(assets.router)
app.include_router(documents.router)
app.include_router(care.router)
app.include_router(service_requests.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"ok": True}

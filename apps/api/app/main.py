from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import kits, me, tags

app = FastAPI(title="NidoGuard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(me.router)
app.include_router(kits.router)
app.include_router(tags.router)


@app.get("/health")
def health():
    return {"ok": True}

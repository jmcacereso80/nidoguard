"""Busqueda del manual de uso por marca y modelo (D-014). Flujo de Prefect: buscar, descargar, guardar copia, registrar.

Se busca una sola vez por modelo y se reutiliza. Solo marca y modelo confirmados; nunca datos de la persona.
"""
import hashlib
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from prefect import flow, task
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal
from ..models import ModelKnowledge, ModelResearchRun
from .storage import Storage, get_knowledge_storage

log = logging.getLogger("nidoguard.manuales")
MAX_PDF_BYTES = 50 * 1024 * 1024
RETRY_AFTER = timedelta(hours=24)
STALE_AFTER = timedelta(minutes=20)  # una busqueda "buscando" sin avance se considera caida
SKIP_DOMAINS = ("amazon.", "mercadolibre.", "ebay.", "walmart.", "aliexpress.", "scribd.", "pdfcoffee.")


def norm(texto: str) -> str:
    """Minusculas, sin acentos ni simbolos: 'Mabe' y 'MABE ' son la misma marca."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def model_key(brand: str, model: str) -> str:
    return f"{norm(brand)}|{norm(model)}"


def ensure_search(db: Session, brand: str, model: str) -> str | None:
    """Marca el modelo como 'buscando' si hace falta. Devuelve la clave solo si hay que lanzar la busqueda."""
    key = model_key(brand, model)
    ahora = datetime.now(timezone.utc)
    row = db.scalar(select(ModelKnowledge).where(ModelKnowledge.model_key == key))
    if row is None:
        row = ModelKnowledge(model_key=key, brand=brand.strip(), model=model.strip(), status="buscando", attempts=0)
        db.add(row)
    elif row.status == "listo":
        return None
    elif row.status == "buscando" and row.updated_at and ahora - row.updated_at < STALE_AFTER:
        return None  # ya hay una busqueda en curso: no duplicar
    elif row.status == "no_encontrado" and row.next_try_at and row.next_try_at > ahora:
        return None  # se reintenta despues
    row.status = "buscando"
    row.updated_at = ahora
    db.commit()
    return key


def ordenar_candidatos(candidatos: list[tuple[str, str]], brand: str) -> list[tuple[str, str]]:
    """Primero los PDF del sitio de la marca; se descartan tiendas de venta y paginas sin manual."""
    marca = norm(brand)

    def puntaje(c: tuple[str, str]) -> int:
        url, title = c[0].lower(), (c[1] or "").lower()
        s = 0
        if url.endswith(".pdf"): s += 2
        if any(p in url or p in title for p in ("manual", "guide", "guia", "user", "usuario")): s += 2
        if marca and marca in norm(url): s += 3  # el dominio o la ruta es de la marca
        if any(d in url for d in SKIP_DOMAINS): s -= 10
        return -s
    sin_tiendas = [c for c in candidatos if not any(d in c[0].lower() for d in SKIP_DOMAINS)]
    filtrados = [c for c in sin_tiendas if c[0].lower().endswith(".pdf") or "manual" in c[0].lower()]
    return sorted(filtrados, key=puntaje)


def buscar_candidatos(brand: str, model: str) -> list[tuple[str, str]]:
    """Claude busca con la busqueda web; devolvemos los enlaces que encontro (url, titulo)."""
    import anthropic
    s = get_settings()
    client = anthropic.Anthropic(api_key=s.claude_key)
    resp = client.messages.create(
        model=s.plate_model, max_tokens=1200,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        messages=[{"role": "user", "content":
                   f"Busca el manual de uso oficial en PDF del fabricante para {brand} modelo {model}. "
                   "Prefiere el sitio oficial de la marca. Responde con una lista corta de enlaces directos."}],
    )
    urls: list[tuple[str, str]] = []
    for bloque in resp.content:
        if getattr(bloque, "type", "") == "web_search_tool_result" and isinstance(bloque.content, list):
            for r in bloque.content:
                urls.append((r.url, getattr(r, "title", "") or ""))
    return urls


def descargar_pdf(url: str) -> bytes | None:
    """Descarga el archivo. Solo se acepta si los bytes son un PDF real y no pasa del tamano maximo."""
    with httpx.Client(follow_redirects=True, timeout=45, headers={"User-Agent": "NidoGuard/1.0"}) as c:
        r = c.get(url)
    if r.status_code != 200 or len(r.content) > MAX_PDF_BYTES or not r.content.startswith(b"%PDF-"):
        return None
    return r.content


def buscar_y_guardar(db: Session, key: str, brand: str, model: str, candidatos_fn, descargar_fn, storage: Storage) -> str:
    """Nucleo del flujo (sin Prefect para poder probarlo). Devuelve el estado final."""
    row = db.scalar(select(ModelKnowledge).where(ModelKnowledge.model_key == key))
    estado, detalle = "no_encontrado", "sin manual valido en los enlaces encontrados"
    try:
        for url, titulo in ordenar_candidatos(candidatos_fn(brand, model), brand)[:3]:
            try:
                data = descargar_fn(url)
            except Exception as e:  # un enlace roto no detiene la busqueda
                log.info("enlace fallido %s: %s", url, e)
                continue
            if not data:
                continue
            digest = hashlib.sha256(data).hexdigest()
            storage_key = f"manuales/{hashlib.sha256(key.encode()).hexdigest()[:16]}/{digest}.pdf"
            storage.put_bytes(storage_key, data, "application/pdf")
            row.status, row.source_url = "listo", url[:800]
            row.title = (titulo or f"Manual de uso {brand} {model}")[:300]
            row.storage_key = storage_key
            row.next_try_at = None
            estado, detalle = "listo", f"manual guardado desde {url}"
            break
    except Exception as e:
        log.exception("fallo la busqueda de manual %s", key)
        estado, detalle = "error", str(e)[:500]
    if estado != "listo":
        row.status = "no_encontrado"
        row.next_try_at = datetime.now(timezone.utc) + RETRY_AFTER
    row.attempts = (row.attempts or 0) + 1
    row.updated_at = datetime.now(timezone.utc)
    db.add(ModelResearchRun(model_key=key, status=estado, detail=detalle))
    db.commit()
    return estado


@task(retries=1, retry_delay_seconds=30)
def t_candidatos(brand: str, model: str):
    return buscar_candidatos(brand, model)


@flow(name="buscar-manual")
def buscar_manual_flow(key: str, brand: str, model: str) -> str:
    with SessionLocal() as db:
        return buscar_y_guardar(db, key, brand, model, t_candidatos, descargar_pdf, get_knowledge_storage())


def run_search(key: str, brand: str, model: str) -> None:
    """Lo llama la API en segundo plano."""
    try:
        buscar_manual_flow(key, brand, model)
    except Exception:
        log.exception("el flujo de manual fallo")


def pedir_manual(db: Session, asset, tasks) -> None:
    """Si el equipo ya tiene marca y modelo confirmados, lanza la busqueda (si no hay manual ya)."""
    from ..models import AssetStatus
    if asset.status != AssetStatus.completo or not asset.brand or not asset.model:
        return
    key = ensure_search(db, asset.brand, asset.model)
    if key:
        tasks.add_task(run_search, key, asset.brand, asset.model)


def manual_view(db: Session, asset, storage: Storage | None = None) -> list[dict]:
    """Lo que ve la persona en Documentos."""
    if not asset.brand or not asset.model:
        return []
    row = db.scalar(select(ModelKnowledge).where(ModelKnowledge.model_key == model_key(asset.brand, asset.model)))
    if row is None:
        return []
    url = None
    if row.status == "listo" and row.storage_key:
        url = (storage or get_knowledge_storage()).presign_get(row.storage_key, expires=3600)
    dominio = None
    if row.source_url:
        dominio = re.sub(r"^https?://(www\.)?", "", row.source_url).split("/")[0]
    note = f"Encontrado por NidoGuard · PDF · Fuente: {dominio}" if row.status == "listo" and dominio else None
    return [{"id": str(row.id), "title": row.title or f"Manual de uso {row.brand} {row.model}",
             "note": note, "url": url, "status": row.status}]

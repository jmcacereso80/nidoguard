"""Manual de uso por marca y modelo (D-014), como enlaces.

Google (Apify) devuelve paginas que tienen el manual. Elegimos las 3 mas acertadas para el modelo
y las guardamos como enlaces, con una nota de que podemos equivocarnos. No se descarga ni se guarda el PDF.
Flujo de Prefect: buscar, elegir y registrar. Se busca una vez por modelo y se reutiliza.
"""
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import httpx
from prefect import flow, task
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal
from ..models import AssetStatus, ModelKnowledge, ModelResearchRun

log = logging.getLogger("nidoguard.manuales")
RETRY_AFTER = timedelta(hours=24)
STALE_AFTER = timedelta(minutes=20)  # una busqueda "buscando" sin avance se considera caida
MAX_LINKS = 3
APIFY_ACTOR = "apify~google-search-scraper"
# Tiendas, marketplaces y documentos de usuarios: no son el manual oficial del modelo.
SKIP_DOMAINS = ("mercadolibre.", "amazon.", "ebay.", "walmart.", "aliexpress.", "liverpool.", "chedraui.",
                "scribd.", "studocu.", "wikipedia.", "youtube.", "facebook.", "pinterest.")
NOTA = "Sugerencia: revisa que sea tu modelo. Podemos equivocarnos."


def norm(texto: str) -> str:
    """Minusculas, sin acentos ni simbolos."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def canon_modelo(texto: str) -> str:
    """Como norm, pero O y 0 cuentan igual (en las etiquetas se confunden)."""
    return norm(texto).replace("o", "0")


def model_key(brand: str, model: str) -> str:
    return f"{norm(brand)}|{norm(model)}"


def _clave_corta(model: str) -> str:
    """Los primeros 7 caracteres del modelo: el enlace casi nunca trae el modelo completo."""
    c = canon_modelo(model)
    return c[:7] if len(c) >= 7 else c


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
        return None  # ya hay una busqueda en curso
    elif row.status == "no_encontrado" and row.next_try_at and row.next_try_at > ahora:
        return None  # se reintenta despues
    row.status = "buscando"
    row.updated_at = ahora
    db.commit()
    return key


def parse_apify_items(items: list[dict]) -> list[tuple[str, str]]:
    """Saca (url, titulo) de los resultados organicos del actor de Google."""
    out: list[tuple[str, str]] = []
    for item in items or []:
        for r in item.get("organicResults") or []:
            if r.get("url"):
                out.append((r["url"], r.get("title") or ""))
    return out


def buscar_en_google(brand: str, model: str) -> list[tuple[str, str]]:
    """Consulta Google con Apify. Formato que ya funciono: 'marca modelo manual'; O y 0 con ambas grafias."""
    token = get_settings().apify_token
    if not token:
        return []
    variantes = {model, model.upper().replace("O", "0")} if ("O" in model.upper() or "0" in model) else {model}
    consultas: list[str] = []
    for v in sorted(variantes):
        consultas += [f"{brand} {v} manual", f"manual de usuario {brand} {v} pdf"]
    items: list[dict] = []
    with httpx.Client(timeout=200) as c:
        for q in consultas:
            r = c.post(f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items",
                       headers={"Authorization": f"Bearer {token}"},
                       json={"queries": q, "resultsPerPage": 20, "maxPagesPerQuery": 1,
                             "languageCode": "es", "countryCode": "mx"})
            r.raise_for_status()
            items.extend(r.json())
    return parse_apify_items(items)


def elegir_paginas(candidatos: list[tuple[str, str]], brand: str, model: str, n: int = MAX_LINKS) -> list[tuple[str, str]]:
    """Las n paginas mas acertadas: que mencionen el modelo y digan 'manual'. Sin coincidencia de modelo, no se sugiere nada."""
    clave = _clave_corta(model)
    marca = norm(brand)
    vistos: set[str] = set()
    puntuadas: list[tuple[int, str, str]] = []
    for url, titulo in candidatos:
        if url in vistos or any(d in url.lower() for d in SKIP_DOMAINS):
            continue
        vistos.add(url)
        texto = url + " " + titulo
        if not clave or clave not in canon_modelo(texto):
            continue  # la pagina no es de este modelo
        s = 3
        if canon_modelo(model) and canon_modelo(model) in canon_modelo(texto):
            s += 4  # modelo completo, no solo el prefijo que comparte con otro modelo
        if "manual" in norm(texto) or "instruc" in norm(texto):
            s += 3
        if "ficha" in norm(texto):
            s -= 2  # una ficha comercial no es el manual
        if marca and marca in norm(texto):
            s += 1
        puntuadas.append((s, url, titulo))
    puntuadas.sort(key=lambda x: -x[0])
    return [(u, t) for _, u, t in puntuadas[:n]]


@task(retries=1, retry_delay_seconds=30)
def t_buscar(brand: str, model: str) -> list[tuple[str, str]]:
    return buscar_en_google(brand, model)


def buscar_y_registrar(db: Session, key: str, brand: str, model: str, candidatos_fn) -> str:
    """Nucleo del flujo (sin Prefect para poder probarlo). Devuelve el estado final."""
    row = db.scalar(select(ModelKnowledge).where(ModelKnowledge.model_key == key))
    ahora = datetime.now(timezone.utc)
    try:
        paginas = elegir_paginas(candidatos_fn(brand, model), brand, model)
        detalle = f"{len(paginas)} paginas sugeridas" if paginas else "sin paginas del modelo en Google"
        estado = "listo" if paginas else "no_encontrado"
    except Exception as e:
        log.exception("fallo la busqueda de manual %s", key)
        paginas, detalle, estado = [], str(e)[:500], "error"
    if paginas:
        row.status = "listo"
        row.links = [{"url": u[:800], "title": (t or f"Manual de uso {brand} {model}")[:300]} for u, t in paginas]
        row.source_url, row.title = paginas[0][0][:800], (paginas[0][1] or "")[:300]
        row.next_try_at = None
    else:
        row.status = "no_encontrado"
        row.links = None
        row.next_try_at = ahora + RETRY_AFTER
    row.attempts = (row.attempts or 0) + 1
    row.updated_at = ahora
    db.add(ModelResearchRun(model_key=key, status=estado, detail=detalle))
    db.commit()
    return estado


@flow(name="buscar-manual")
def buscar_manual_flow(key: str, brand: str, model: str) -> str:
    with SessionLocal() as db:
        return buscar_y_registrar(db, key, brand, model, t_buscar)


def run_search(key: str, brand: str, model: str) -> None:
    """Lo llama la API en segundo plano."""
    try:
        buscar_manual_flow(key, brand, model)
    except Exception:
        log.exception("el flujo de manual fallo")


def pedir_manual(db: Session, asset, tasks) -> None:
    """Si el equipo ya tiene marca y modelo confirmados, lanza la busqueda (si no hay manual ya)."""
    if asset.status != AssetStatus.completo or not asset.brand or not asset.model:
        return
    key = ensure_search(db, asset.brand, asset.model)
    if key:
        tasks.add_task(run_search, key, asset.brand, asset.model)


def manual_view(db: Session, asset) -> list[dict]:
    """Lo que ve la persona en Documentos: hasta 3 enlaces con la nota de que podemos equivocarnos."""
    if not asset.brand or not asset.model:
        return []
    row = db.scalar(select(ModelKnowledge).where(ModelKnowledge.model_key == model_key(asset.brand, asset.model)))
    if row is None:
        return []
    if row.status == "listo" and row.links:
        return [{"id": f"{row.id}-{i}", "title": l.get("title") or "Manual de uso", "note": NOTA,
                 "url": l["url"], "status": "listo"} for i, l in enumerate(row.links[:MAX_LINKS])]
    return [{"id": str(row.id), "title": f"Manual de uso {row.brand} {row.model}", "note": None,
             "url": None, "status": row.status}]

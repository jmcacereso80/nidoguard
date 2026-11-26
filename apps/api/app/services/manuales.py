"""Busqueda del manual de uso por marca y modelo (D-014). Flujo de Prefect: buscar, descargar, guardar copia, registrar.

Se busca una sola vez por modelo y se reutiliza. Solo marca y modelo confirmados; nunca datos de la persona.
"""
import hashlib
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

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
MANUAL_WORDS = ("manual", "instrucc", "guia", "guide", "usuario", "user")
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


FICHA_WORDS = ("ficha", "comercial", "hojatecnica", "datasheet", "catalogo", "brochure")


def _es_ficha(url: str) -> bool:
    """Una ficha comercial o catalogo no es el manual, aunque el texto del enlace diga 'manuales'."""
    return any(w in norm(urlparse(url).path) for w in FICHA_WORDS)


def _es_pdf(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")  # ignora ?context=... de los sitios de la marca


def ordenar_candidatos(candidatos: list[tuple[str, str]], brand: str, model: str = "") -> list[tuple[str, str]]:
    """PDF del sitio de la marca primero, con el modelo exacto; se descartan tiendas y paginas de listado."""
    marca, modelo = norm(brand), norm(model)
    modelo_corto = modelo[:9] if len(modelo) >= 9 else modelo  # el modelo completo casi nunca aparece igual en la URL

    def puntaje(c: tuple[str, str]) -> int:
        url, title = c[0], (c[1] or "")
        url_l, title_l, n_url = url.lower(), title.lower(), norm(url + " " + title)
        s = 0
        if _es_pdf(url): s += 3
        if any(p in url_l or p in title_l for p in ("manual", "guide", "guia", "user", "usuario", "instrucc")): s += 2
        if marca and marca in norm(url): s += 3  # el dominio o la ruta es de la marca
        if modelo_corto and modelo_corto in n_url: s += 4  # el manual es de este modelo
        return -s
    sin_tiendas = [c for c in candidatos if not any(d in c[0].lower() for d in SKIP_DOMAINS)]
    # Solo PDF que digan ser manual o instrucciones (una ficha comercial no sirve como manual).
    filtrados = [c for c in sin_tiendas if _es_pdf(c[0]) and not _es_ficha(c[0])
                 and any(w in norm(c[0] + " " + (c[1] or "")) for w in MANUAL_WORDS)]
    return sorted(filtrados, key=puntaje)


APIFY_ACTOR = "apify~google-search-scraper"


def parse_apify_items(items: list[dict]) -> list[tuple[str, str]]:
    """Saca (url, titulo) de los resultados organicos que devuelve el actor de Google."""
    out: list[tuple[str, str]] = []
    for item in items or []:
        for r in item.get("organicResults") or []:
            if r.get("url"):
                out.append((r["url"], r.get("title") or ""))
    return out


def buscar_en_google(brand: str, model: str) -> list[tuple[str, str]]:
    """Consulta Google con Apify (apify/google-search-scraper) con dos formulaciones del manual."""
    token = get_settings().apify_token
    if not token:
        return []
    variantes = {model, model.upper().replace("O", "0")} if "O" in model.upper() or "0" in model else {model}
    consultas = []
    for v in sorted(variantes):  # Google trata O y 0 distinto: buscamos con las dos grafias
        # Primero el formato que ya dio el resultado correcto: "marca modelo manual".
        consultas += [f"{brand} {v} manual", f"manual de usuario {brand} {v} pdf", f"{v} manual"]
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


PDF_LINK = re.compile(r'<a[^>]+href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def pdfs_de_pagina(url: str) -> list[tuple[str, str]]:
    """Paginas del modelo que enlazan su manual: sacamos los PDF que se presentan como manual."""
    with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": "NidoGuard/1.0"}) as c:
        r = c.get(url)
    if r.status_code != 200:
        return []
    out = []
    for href, texto in PDF_LINK.findall(r.text):
        href = httpx.URL(url).join(href.replace("&amp;", "&")).__str__()
        out.append((href, re.sub(r"<[^>]+>|\s+", " ", texto).strip()))
    return out


def enriquecer_con_paginas(candidatos: list[tuple[str, str]], model: str) -> list[tuple[str, str]]:
    """Abre hasta 3 paginas que son del modelo exacto y suma los PDF de manual que enlazan."""
    extra: list[tuple[str, str]] = []
    paginas = [c for c in candidatos if not _es_pdf(c[0]) and _es_del_modelo(c, model)][:3]
    for url, _ in paginas:
        try:
            extra.extend(pdfs_de_pagina(url))
        except Exception as e:
            log.info("no pude leer la pagina %s: %s", url, e)
    return candidatos + extra


def buscar_candidatos(brand: str, model: str) -> list[tuple[str, str]]:
    """Primero Google (Apify) y las paginas del modelo; si no da nada util, Claude como respaldo."""
    try:
        encontrados = buscar_en_google(brand, model)
        if encontrados:
            return enriquecer_con_paginas(encontrados, model)
    except Exception:
        log.exception("fallo la busqueda con Apify; se usa Claude")
    return buscar_candidatos_claude(brand, model)


def buscar_candidatos_claude(brand: str, model: str) -> list[tuple[str, str]]:
    """Claude busca con la busqueda web; devolvemos los enlaces que encontro (url, titulo)."""
    import anthropic
    s = get_settings()
    client = anthropic.Anthropic(api_key=s.claude_key)
    resp = client.messages.create(
        model=s.plate_model, max_tokens=1200,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content":
                   f"Busca el manual de uso en PDF del modelo EXACTO {model} de {brand} "
                   "(si el modelo tiene una O o un cero al final, busca con ambas grafías). "
                   "No sirve el manual de otro modelo parecido. Prefiere el sitio oficial de la marca. "
                   "Responde con una lista corta de enlaces directos."}],
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


def canon_modelo(texto: str) -> str:
    """Igual que norm, pero O y 0 cuentan igual (en las etiquetas se confunden)."""
    return norm(texto).replace("o", "0")


def _es_del_modelo(c: tuple[str, str], model: str) -> bool:
    modelo = canon_modelo(model)
    corto = modelo[:9] if len(modelo) >= 9 else modelo
    return bool(corto) and corto in canon_modelo(c[0] + " " + (c[1] or ""))


def buscar_y_guardar(db: Session, key: str, brand: str, model: str, candidatos_fn, descargar_fn, storage: Storage) -> str:
    """Nucleo del flujo (sin Prefect para poder probarlo). Devuelve el estado final."""
    row = db.scalar(select(ModelKnowledge).where(ModelKnowledge.model_key == key))
    estado, detalle = "no_encontrado", "sin manual valido en los enlaces encontrados"
    try:
        # Solo manuales del modelo exacto: un manual de un modelo parecido puede no servir.
        exactos = [c for c in ordenar_candidatos(candidatos_fn(brand, model), brand, model)
                   if _es_del_modelo(c, model)]
        if not exactos:
            detalle = "no hay manual del modelo exacto en los enlaces encontrados"
        for url, titulo in exactos[:8]:
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

# NidoGuard - reglas del proyecto

PWA de Patrimonio Inteligente: etiquetas NFC + QR, lectura de placas con IA y concierge, para identificar, mantener, valorar y revender los equipos del hogar. Mexico primero (es-MX, MXN). Lema: "Mejor vida. Mas valor."
Marca: #183B56 / #7399B5 / #C18B58 / #F6F2EC, fuente Manrope, estilo Liquid Glass.

## Reglas
- Textos de usuario en espanol de Mexico, lenguaje simple, sin jerga tecnica.
- NUNCA imprimir, copiar o registrar valores de `.env`. Solo nombres de variables.
- Pedir permiso antes de: crear buckets de R2, cambiar Cloudflare/Clerk, tocar una base real o borrar datos.
- Dominio: nidoguard.com (app. y api. como subdominios).

## Stack (aprobado)
Next.js + TypeScript estricto, Tailwind, Radix, TanStack Query, Serwist (PWA); FastAPI, Pydantic v2, SQLAlchemy 2, Alembic; PostgreSQL 17 (pgcrypto, citext, pg_trgm); Clerk (login); Cloudflare R2 (archivos privados, URLs firmadas); Prefect (flujos); Claude API para leer placas (Haiku 5.5 esfuerzo medio, respaldo Sonnet 5.5 con baja confianza; salida estructurada Pydantic detras de una interfaz `PlateReader`).
Monorepo pnpm + Turborepo: apps/web, apps/api, apps/worker, packages/design-tokens, packages/api-client.
Despliegue inicial: un solo servidor Ubuntu con todo; luego se expande.

## Alcance etapa 1
Cuenta y hogar, kits y activacion por QR (codigo de un solo uso con hash en BD + codigo corto escribible), rutas /k/<codigo> y /t/<token>, escaner dentro de la app, alta rapida (etiqueta + foto de placa + ubicacion + nombre), lectura de placa con IA, expediente basico.

## Documentos
`docs/ESTADO_ETAPA_1.md` (qué está hecho y qué falta), `docs/DECISIONES_RESUMEN.md` (decisiones vigentes). Plan, modelo de datos y decisiones completas viven en el Project NIDOGUARD de claude.ai.

## Cómo correr y probar (en el Mac del usuario; usa su Postgres 17 de Postgres.app)
- Raiz: `cp .env.example .env` si no existe. El `.env` ya existe en la carpeta del usuario; no lo imprimas.
- API: `python3 -m venv .venv && source .venv/bin/activate && pip install -e "apps/api[dev]"`, luego `cd apps/api && alembic upgrade head && uvicorn app.main:app --reload --port 8000`.
- Web: `pnpm install && pnpm --filter @nidoguard/web dev` (http://localhost:3000). La clave publicable de Clerk esta en `CLERK_API_KEY`; `next.config.ts` la expone y lee el `.env` de la raiz.
- Pruebas API: crea una base vacia `nidoguard_test` y `TEST_DATABASE_URL=postgresql+psycopg://USUARIO:CLAVE@localhost:5432/nidoguard_test pytest` en `apps/api` (la prueba BORRA el esquema public de esa base: nunca la apuntes a la real). Web: `pnpm --filter @nidoguard/web test`.
- Lotes de kits: `cd apps/api && python -m admin.gen_batch --name "Lote 1" --kits 5 --tags-per-kit 20 --out ./salida` (no subas `salida/`).

## Pendiente de la etapa 1 (ver docs/ESTADO_ETAPA_1.md)
1. Probar de punta a punta con Clerk real: registro, crear hogar, `/k/<codigo>` con un lote de prueba, escaner, alta rapida, "Por confirmar". Corregir lo que falle.
2. R2: pedir permiso, crear buckets `nidoguard-private` y `nidoguard-knowledge`, probar subida con URL firmada y la lectura de la placa con una foto real.
3. Row Level Security en Postgres; Playwright de punta a punta; Sentry; iconos de la PWA y Serwist; revisar el parametro de esfuerzo medio en `plate_reader.py`.
4. Evaluar la lectura con 50 a 100 placas reales (D-009).
5. Despliegue: un servidor Ubuntu (Docker, Postgres 17, API, web) con `app.` y `api.` en Cloudflare.

## Forma de trabajo
Una rama por tarea (`fase-...`), pruebas antes de subir, mensajes de commit en espanol. Si algo cambia una decision, actualiza `docs/DECISIONES_RESUMEN.md`.

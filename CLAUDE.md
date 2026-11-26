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

Estado actual: docs/ESTADO_ETAPA_1.md. Los documentos de decisiones, plan y modelo de datos viven en el Project NIDOGUARD de claude.ai.

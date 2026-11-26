# NidoGuard — Estado de la etapa 1 (2026-11-25)

Base: PostgreSQL 17. Un solo servidor Ubuntu al inicio. Dominio `nidoguard.com` (`app.` y `api.`).

## Hecho y probado
- **Fase 0:** monorepo (pnpm + Turborepo), modelo y migración inicial (sube y baja limpia en PG 17), tokens de diseño.
- **Fase 1:** `/me`, `/home`, `/spaces` (ubicaciones propias, con "+ Nueva"); aislamiento entre hogares probado.
- **Fase 2:** generador de lotes (`admin/gen_batch.py`): hashes en base, CSV para NFC, PDF de hojas con QR y código corto. Reclamo del kit de un solo uso, idempotente para su dueño, límite de 10 intentos fallidos por hora por usuario o IP. Rutas `/k/<código>` y `/t/<token>`.
- **Fase 3:** `GET /tags/{token}` con los cuatro casos (sin sesión, disponible, vinculada, ajena sin datos privados). Escáner QR en la app que solo acepta URLs de NidoGuard (probado).
- **Fase 4:** alta rápida (etiqueta, foto, ubicación, nombre), modo ráfaga, URL firmada de R2 con validación de tipo y tamaño, "Por confirmar" individual y en bloque, datos a mano.
- **Fase 5:** lectura de placas con Claude Haiku 5.5, respaldo Sonnet 5.5 si hay baja confianza, `null` para lo ilegible, transcripción literal, EXIF eliminado. Probado con la API real en placas sintéticas: lectura correcta con confianza alta; foto borrosa → "necesita otra foto" sin inventar.
- **Fase 6:** expediente básico (`GET /assets/{id}`, historial de solo agregar, pantalla del equipo).
- Pruebas: 17 de API y 2 de web; la web compila (`next build`).

## Pendiente o sin probar
- **R2:** los buckets no están creados y la escritura no se probó. Requiere tu autorización.
- **Clerk con una cuenta real:** la verificación del token (JWKS) y el flujo de login no se han ejecutado de punta a punta; se necesita correr la web con tus llaves.
- **Prefect:** `apps/worker/flows.py` está escrito, no probado. Hoy la lectura corre en segundo plano dentro de la API.
- **Row Level Security** en Postgres (segunda barrera): no implementado. Hoy el aislamiento se garantiza con filtros por hogar en la API, probados.
- **Playwright de punta a punta, Sentry, íconos de la PWA y caché sin conexión (Serwist):** pendientes.
- **Evaluación de lectura con 50 a 100 placas reales** (D-009): pendiente; hasta ahora solo placas sintéticas.
- **NFC y cámara en celular real:** sin probar.
- **Parámetro de esfuerzo "medio"** en la llamada a Claude: se envía y, si la API lo rechaza, se reintenta sin él; no verifiqué cuál de los dos ocurrió.

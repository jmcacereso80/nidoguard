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
- **Documentos del equipo:** garantía y factura (foto o PDF, fecha de vencimiento que escribe la persona, precio editable, documento de respaldo sin IA). Migración 0002.
- **Manual de uso:** búsqueda por marca y modelo confirmados con Apify (Google) y Prefect; se guardan hasta 3 enlaces con la nota "podemos equivocarnos". Migraciones 0003 y 0004.
- **Cuidados (fase cuidado básico):** tareas por frecuencia generadas con Claude (`CARE_MODEL`, por defecto `claude-haiku-5-5`), planes compartidos por modelo (`care_templates`), marcar como realizado con historial, reprogramar, "Me sirve" y "No aplica", menú Cuidado con Próximas, Vencidas, Garantías, Historial y vista Semana | Mes. Migraciones 0005 y 0006.
- Pruebas: API 61 y web 33 (al cierre de cuidados).

- **Cotizar y agendar servicio (etapas A y B):** direcciones del hogar, directorio de técnicos (Google Maps vía Apify, se busca una vez por ciudad y especialidad), solicitudes, cotizaciones por llamada con Retell en oleadas, webhook firmado y extractor. Todo apagado por defecto. Migraciones 0007 a 0010 aplicadas en la base de desarrollo.
- Pruebas de cotizar: API 103 de 103, web 42 de 42, `build` compila todas las rutas.
- Directorio real probado en Tepoztlán, Morelos (refrigeración): 3 técnicos con teléfono mexicano válido. Costo del actor de Maps: US$0.004 por lugar.
- Retell: agente de prueba creado con el guion de `docs/agente_cotizador.md` (idioma es-419, voz Claudia). El número de salida es el de la cuenta.

## Pendiente o sin probar
- **Prueba de llamadas con Retell de punta a punta:** falta agregar una dirección del hogar en Inicio, y después una prueba con `CALLS_ENABLED=true` y `CALLS_ALLOWLIST` solo con tu número. Luego se regresa a `false`.
- **Grabaciones de llamadas:** requieren crear un bucket de R2; pendiente de tu permiso.
- **Pieza 6 (Prefect para cotizaciones):** pendiente de tu permiso para alojarla.
- **R2:** los buckets no están creados y la escritura no se probó. Requiere tu autorización.
- **Clerk con una cuenta real:** la verificación del token (JWKS) y el flujo de login no se han ejecutado de punta a punta; se necesita correr la web con tus llaves.
- **Prefect:** los flujos de manuales y de cuidados corren desde la API; `apps/worker/flows.py` (lectura de placas) sigue sin probar contra un servidor de Prefect.
- **Cuidados pendientes:** recordatorio semanal por push o WhatsApp; cuidados leídos del manual por modelo (requiere el bucket `nidoguard-knowledge`, con permiso).
- **Cuidados sin probar de punta a punta con cuenta real de Clerk:** pasos de la lista de prueba pendientes de confirmar en el celular.
- **Row Level Security** en Postgres (segunda barrera): no implementado. Hoy el aislamiento se garantiza con filtros por hogar en la API, probados.
- **Playwright de punta a punta, Sentry, íconos de la PWA y caché sin conexión (Serwist):** pendientes.
- **Evaluación de lectura con 50 a 100 placas reales** (D-009): pendiente; hasta ahora solo placas sintéticas.
- **NFC y cámara en celular real:** sin probar.
- **Parámetro de esfuerzo "medio"** en la llamada a Claude: se envía y, si la API lo rechaza, se reintenta sin él; no verifiqué cuál de los dos ocurrió.

# Especificación: Documentos y Cuidado dentro del equipo

Resume lo ya decidido en el Project NIDOGUARD (D-013, D-014, D-007, D-009; modelo de datos y flujos 5 y 6). Si algo de aquí contradice una decisión, avisa a Juan antes de construir.

## Qué existe hoy
- Expediente del equipo (`apps/web/app/equipos/[id]/page.tsx`) con pestañas Resumen e Historial funcionando. **Documentos** y **Cuidado** son pantallas "Muy pronto" (componente `Pronto`).
- La lectura de placa extrae solo marca, modelo y número de serie (más el tipo para nombrar el equipo). El resto del texto de la placa queda en `AssetReading.transcript`.
- Diseño: `docs/DISENO_LIQUID_GLASS.md` y `docs/mockups/` (`EquipoDocs`, `EquipoCuidado`, `EquipoHistorial`). El mockup manda.

## Pestaña Documentos (D-013, ajustada por Juan)
- **Manual de uso: lo busca la IA, la persona no lo sube.** Cuando marca y modelo están confirmados, un flujo de Prefect busca el manual oficial del modelo (o lo toma de la base de conocimiento si ya existe) y lo deja en esta pestaña con enlace a la fuente. Estados: `buscando`, `listo`, `no_encontrado` (se reintenta después). Sin modelo confirmado no se busca.
- **Garantía: la persona la sube** con foto o PDF (botones "Tomar foto" y "Subir PDF"). **Factura**: igual, opcional ("si la tiene").
- Flujo de subida: `POST /assets/{id}/documents/upload-url` (kind, filename, content_type, size) devuelve URL firmada de R2 y `document_id`; el navegador hace PUT del archivo; `POST /assets/{id}/documents/{document_id}/process` lanza la lectura. Validar el tipo real del archivo (imagen o PDF) y un tamaño máximo.
- Claude extrae fecha de inicio, duración, cobertura, proveedor y folio, con confianza por campo. La persona revisa y confirma; lo que no se lee queda vacío. Al confirmar se crea `Warranty`.
- `AssetDocument` guarda el hash del archivo para no procesarlo dos veces. Los documentos privados **nunca** entran a la base compartida.
- `GET /assets/{id}/documents` devuelve `{ manuals[], warranty|null, invoice|null }` (formato en `apps/web/lib/care.ts`).

## Pestaña Cuidado (D-013, ajustada por Juan)
Son los cuidados del equipo a lo largo del tiempo, **agrupados por frecuencia**: diario, semanal, mensual, bimestral, trimestral, semestral, anual, bianual (cada 2 años) y más largos.
- Cada tarea: título, frecuencia estructurada `every = {n, unit: dia|semana|mes|anio}`, próxima fecha (`next_due`), detalle, instrucciones paso a paso, y **origen**: "Fuente: manual del fabricante" o "Sugerencia de NidoGuard, por confirmar".
- Las tareas con origen "manual" salen del manual de la base de conocimiento del modelo (D-014). Mientras no exista, Claude genera tareas generales por tipo de equipo, siempre como sugerencia por confirmar.
- La garantía por vencer (60 días o menos) se muestra arriba **solo si está confirmada**. Una garantía estimada nunca alerta.
- Hasta confirmar el modelo, el plan se marca "Basado en datos sin confirmar" (Q-015, ver abajo).
- "Registrar cuidado" marca la tarea como hecha, calcula el siguiente `next_due` según `every` y agrega un evento al Historial (`AssetEvent`, solo agregar).
- Recordatorios agrupados en un resumen semanal (push o WhatsApp) que se puede silenciar; los cuidados diarios no mandan una notificación cada uno.
- `GET /assets/{id}/care` devuelve `{ model_confirmed, tasks[] }`. Modelo: `MaintenancePlan`, `MaintenanceTask`, `MaintenanceRecord`, `Reminder`, `Notification`.

## Base de conocimiento por modelo (D-014)
- Se investiga **una vez por modelo** (clave marca + modelo normalizada) y se reutiliza. Vive en la misma PostgreSQL con `pgvector` y en R2 (`nidoguard-knowledge`).
- Flujo de Prefect: buscar manual, descargarlo, extraer texto, dividir en fragmentos con embeddings; Claude lo lee una sola vez y extrae especificaciones, plan de mantenimiento, códigos de error y refacciones, con fuente y confianza. Todo queda "sin verificar" hasta revisarse.
- Evitar investigaciones simultáneas del mismo modelo. Si no hay manual, registrar el resultado y reintentar después. Registrar cada corrida en `ModelResearchRun` (estado, fecha, costo).
- Se aloja copia propia de los manuales, conservando enlace y fuente originales. Riesgo: son de los fabricantes; pendiente revisión legal y un proceso para retirarlos a petición.
- El número de serie y todo dato de la persona **nunca** entra a esta base.

## Reglas de construcción
- Textos en español de México, lenguaje simple. Estilo Liquid Glass del mockup, sin inventar datos: si algo no existe todavía, "Muy pronto".
- Pedir permiso a Juan antes de crear buckets de R2, tocar Cloudflare/Clerk, una base real o borrar datos. Nunca imprimir valores de `.env`.
- Prefect ejecuta y Postgres es la fuente de verdad; cada paso es idempotente.
- Una rama por tarea, pruebas antes de subir, commits en español. Actualiza `docs/DECISIONES_RESUMEN.md` si algo cambia una decisión.

## Orden sugerido (cada paso en su rama)
0. **Pantallas** ya hechas en la rama `fase-documentos-cuidado-ui` (Documentos, Cuidado agrupado por frecuencia, subida de garantía/factura). Falta el backend.
1. **Garantía y factura** (`fase-documentos-garantia`): endpoints de subida y lectura con Claude, confirmación, `Warranty`. Requiere R2 (pedir permiso).
2. **Cuidado básico** (`fase-cuidado-basico`): tareas por frecuencia generadas con Claude por tipo de equipo, etiquetadas "Sugerencia de NidoGuard, por confirmar"; "Registrar cuidado" al Historial; alerta de garantía.
3. **Búsqueda de manual y base de conocimiento por modelo** (`fase-conocimiento-modelo`): búsqueda automática del manual, `pgvector`, investigación única con Prefect; Cuidado pasa a "Fuente: manual del fabricante". Requiere confirmar que el Postgres.app de Juan trae `pgvector`.

## Decisiones abiertas (preguntar a Juan antes del paso que las necesite)
- Q-014: si solo se conoce la fecha de compra, ¿se muestra una garantía **estimada**, marcada "Estimada, por confirmar"?
- Q-015: ¿el plan de cuidado del modelo se oculta hasta confirmar el modelo, o se muestra marcado "basado en datos sin confirmar"?
- ¿El precio de compra de la factura se guarda solo o únicamente si la persona lo confirma?
- ¿Cada cuántos meses se refresca el conocimiento de un modelo y quién lo marca como verificado?
- Q-011: revisión legal de alojar copias de manuales.

## Estado: cuidados de cada equipo (rama `fase-cuidado-basico`)
Hecho, con pruebas: tablas `care_tasks` y `care_records` (migración 0005), generador `ClaudeCarePlanner` detrás de la interfaz `CarePlanner` (`apps/api/app/services/care_planner.py`, modelo en `CARE_MODEL`), y estas rutas:
- `GET /assets/{id}/care` y `POST /assets/{id}/care/generate` (idempotente; si falla la IA responde 503 y no guarda nada).
- `POST /care/{id}/done` (siguiente fecha = fecha en que se hizo + frecuencia de calendario, nunca en el pasado; también confirma la sugerencia y agrega "cuidado_hecho" al Historial), `/reschedule`, `/confirm` ("Me sirve"), `/dismiss` ("No aplica", no se vuelve a sugerir).
- `GET /care`: todos los cuidados del hogar con nombre del equipo y ubicación, para la pantalla Cuidado del menú.
Reglas: todo sale con origen "sugerencia" (el manual solo se enlaza, no se lee; el origen "manual del fabricante" llega con la base de conocimiento). La primera fecha es la frecuencia pero nunca más de 30 días. El día de hoy se cuenta en hora de la Ciudad de México.
Pendiente: pantalla global `/cuidado` (mockup `Cuidado.dc.html`: Próximas, Vencidas, Garantías, Historial), resumen semanal de recordatorios, y cuidados con origen en el manual del fabricante.

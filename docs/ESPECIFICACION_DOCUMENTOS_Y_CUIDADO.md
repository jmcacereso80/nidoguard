# Especificación: Documentos y Cuidado dentro del equipo

Resume lo ya decidido en el Project NIDOGUARD (D-013, D-014, D-007, D-009; modelo de datos y flujos 5 y 6). Si algo de aquí contradice una decisión, avisa a Juan antes de construir.

## Qué existe hoy
- Expediente del equipo (`apps/web/app/equipos/[id]/page.tsx`) con pestañas Resumen e Historial funcionando. **Documentos** y **Cuidado** son pantallas "Muy pronto" (componente `Pronto`).
- La lectura de placa extrae solo marca, modelo y número de serie (más el tipo para nombrar el equipo). El resto del texto de la placa queda en `AssetReading.transcript`.
- Diseño: `docs/DISENO_LIQUID_GLASS.md` y `docs/mockups/` (`EquipoDocs`, `EquipoCuidado`, `EquipoHistorial`). El mockup manda.

## Pestaña Documentos (D-013)
- Tres bloques: **Manuales**, **Garantía** y **Factura**. Garantía y factura son opcionales ("si la tiene").
- Garantía y factura: la persona sube una foto o un PDF escaneado, al comprar el equipo o después. Subida directa a R2 privado con URL firmada y validación del tipo real del archivo.
- Claude extrae: fecha de inicio, duración, cobertura, proveedor y folio, con confianza por campo. La persona revisa y confirma; lo que no se lee queda vacío.
- Al confirmar se crea o actualiza `Warranty` (inicio, duración, vencimiento, proveedor, cobertura, folio, vínculo al documento).
- `AssetDocument` guarda el hash del archivo para no procesarlo dos veces. Los documentos privados **nunca** entran a la base compartida de conocimiento.
- Manuales: vienen de la base de conocimiento por modelo (ver abajo). Mostrar enlace y fuente originales.

## Pestaña Cuidado (D-013)
- Recomendaciones generadas con Claude, **siempre etiquetadas**: "Fuente: manual del fabricante" frente a "Sugerencia de NidoGuard, por confirmar".
- La garantía por vencer se muestra aquí **solo si está confirmada**.
- El plan específico del modelo no se muestra hasta confirmar el modelo, o aparece marcado "basado en datos sin confirmar".
- Modelo: `MaintenancePlan`, `MaintenanceTask`, `MaintenanceRecord`, `Reminder`, `Notification`.
- Registrar un cuidado hecho (botón "Registrar cuidado") agrega un evento al Historial (`AssetEvent`, solo agregar).
- Recordatorios agrupados en un resumen semanal (push o WhatsApp) que se puede silenciar. No uno por equipo.

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
1. **Garantía y factura** (`fase-documentos-garantia`): subida, lectura con Claude, confirmación, `Warranty`, pestaña Documentos real. Requiere R2 (pedir permiso).
2. **Cuidado básico** (`fase-cuidado-basico`): tareas generales por tipo de equipo generadas con Claude y etiquetadas "Sugerencia de NidoGuard, por confirmar"; "Registrar cuidado" al Historial; alerta de garantía.
3. **Base de conocimiento por modelo** (`fase-conocimiento-modelo`): manuales, `pgvector`, investigación única con Prefect; Cuidado pasa a "Fuente: manual del fabricante". Requiere confirmar que el Postgres.app de Juan trae `pgvector`.

## Decisiones abiertas (preguntar a Juan antes del paso que las necesite)
- Q-014: si solo se conoce la fecha de compra, ¿se muestra una garantía **estimada**, marcada "Estimada, por confirmar"?
- Q-015: ¿el plan de cuidado del modelo se oculta hasta confirmar el modelo, o se muestra marcado "basado en datos sin confirmar"?
- ¿El precio de compra de la factura se guarda solo o únicamente si la persona lo confirma?
- ¿Cada cuántos meses se refresca el conocimiento de un modelo y quién lo marca como verificado?
- Q-011: revisión legal de alojar copias de manuales.

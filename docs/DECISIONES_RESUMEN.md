# NidoGuard — Decisiones vigentes (resumen para desarrollo)

Versión completa en el Project NIDOGUARD de claude.ai (`docs/DECISIONS.md`). Dominio definitivo: **nidoguard.com** (`app.` PWA, `api.` FastAPI). Donde la versión completa dice `.mx`, vale `.com`.

## Aprobadas
- **D-001** La cuenta se crea primero; sin cuenta no hay equipos ni uso de etiquetas.
- **D-002** Solo valen etiquetas de NidoGuard; un token que no existe en el sistema es inválido.
- **D-003/D-004** El kit es la unidad de activación. Se reclama una sola vez y deja disponibles todas sus etiquetas. La hoja trae un QR que lleva solo el código corto (XXXXX-XXXXX, sin 0/O/1/I), que se imprime debajo y también se puede teclear. (Cambio 2026-11-26: antes el QR llevaba una URL con código largo de 120 bits; se cambió para que el escáner lea el mismo código que se escribe a mano.) Intentos fallidos limitados por usuario e IP. Límites hipotéticos: 20 (Basic), 45 (Premium).
- **D-010** El escaneo ocurre dentro de la app; las URLs viven en el dominio de la app; el escáner solo acepta URLs de NidoGuard con token válido. Rutas: `/k/<codigo>` (kit) y `/t/<token>` (etiqueta). El subdominio de la app queda fijo una vez impreso.
- **D-005** Clerk + Next.js + FastAPI + PostgreSQL. **D-007** Prefect para flujos (Postgres es la fuente de verdad, pasos idempotentes).
- **D-015** Alta rápida: solo foto de placa, ubicación y nombre. Todo lo demás opcional y después. Ubicación nueva en el momento. Datos a mano si la placa no se lee. Modo ráfaga con contador del kit ("7 de 20"). Lectura en segundo plano; los problemas aparecen después ("Foto borrosa", "Faltan datos"). Pantalla "Por confirmar" con confirmación individual y en bloque.
- **D-012** Ubicaciones definidas por el usuario (se sugieren Cocina, Sala…). **D-013** Pestañas del expediente: Resumen, Documentos (manuales, garantía, factura opcionales), Cuidado (siempre etiquetado: manual del fabricante vs sugerencia por confirmar), Historial. **D-014** Una investigación por modelo, reutilizada; manuales con copia propia; lo privado nunca entra a la base compartida. **D-006** Dirección visual Liquid Glass.

## Propuestas en uso
- **D-008** R2: bucket privado `nidoguard-private` (fotos/placas/facturas), `nidoguard-knowledge` para manuales; subida directa con URL firmada; nombres sin datos personales; borrar subidas no confirmadas en 24 h; quitar EXIF.
- **D-009** Claude lee la placa desde el backend con salida estructurada y solo extrae marca, modelo y número de serie, iguales para todos los equipos (el tipo solo nombra el equipo; voltaje, capacidad y demás quedan en la transcripción para Documentos y Cuidado); `null` para lo ilegible, nunca adivinar, guardar transcripción literal. Interfaz `PlateReader`. Haiku 5.5 esfuerzo medio, respaldo Sonnet 5.5; decidir con 50 a 100 placas reales de México.
- Tabla `AssetEvent` de solo agregar. RLS como segunda barrera (pendiente).

## Abiertas que afectan el código
Q-007 métodos de login (hoy: lo que Clerk ofrezca) · Q-010 Prefect Cloud o propio · Q-013 nombre sugerido por IA (el mockup lo supone) · Q-014 garantía estimada · Q-015 plan de cuidado oculto hasta confirmar modelo · Q-012 cómo llega el pedido para marcar un kit "vendido".

## Flujo del cliente (resumen)
Nuevo: escanea QR de la hoja → "Crea tu cuenta para activar tu kit" → kit reclamado → crea hogar → escanea etiqueta dentro de la app → foto de placa + nombre + ubicación → lectura en segundo plano → "Por confirmar". Con cuenta: sin sesión inicia sesión y regresa; compra otro kit y lo reclama directo; etiqueta disponible de su kit se vincula; etiqueta vinculada abre el expediente; etiqueta ajena no muestra nada privado. En iPhone, Safari y la PWA no comparten sesión: guiar la instalación tras reclamar el kit.

## Cotizar y agendar servicio (2026-11-26)
- **NidoGuard no cobra por el servicio.** El pago es directo entre la persona y el técnico.
- **Cotizaciones anónimas:** al técnico se le da la zona (colonia y ciudad), nunca la dirección ni el nombre de la persona.
- **Llamadas en oleadas de 3, hasta 5 cotizaciones:** se detiene al llegar a 5.
- **Todo apagado por defecto:** `CALLS_ENABLED=false`. Solo se marca a `CALLS_ALLOWLIST` mientras se prueba.

## Mi casa (2026-11-27)
- **Todo lo personal vive en Mi casa (`/hogar`):** nombres, apellidos, teléfono y hasta 5 direcciones. El teléfono ya no está en la pantalla de dirección.
- **Nombre de pila al técnico = primera palabra de "nombres";** los apellidos solo van al fabricante cuando agenda garantía.
- **Dirección principal:** una por hogar; se usa si no se elige otra. Al eliminar una dirección, sus lugares y equipos pasan a otra (nunca se borran).
- **Teléfono:** se comparte con el técnico solo si la persona lo permite en cada cita.

## Llamada de cita (2026-11-27)
- **La visita ya viene acordada:** la llamada de agendar confirma, no pregunta si el técnico puede ir. Solo pide hora aproximada y quién irá; después le da la dirección exacta y el nombre de pila de la persona.
- **La persona ve quién irá:** nombre de pila que dice el técnico al confirmar (migración 0014, `visit_person`).
- **Contacto recíproco:** teléfono de la persona al técnico solo con su permiso; si lo da, ve el del técnico al confirmarse la visita. Nota de acceso opcional (migración 0015). Sin guardar documentos.
- **Sin descanso del técnico (2026-11-27):** se quitó la regla de no llamar a un técnico más de una vez cada 7 días entre solicitudes distintas. Si tiene disponibilidad, él acepta o rechaza en la llamada. Siguen: do_not_call, máx. 2 intentos y topes de costo.
- **Cancelar siempre (2026-11-27):** la persona puede cancelar en cualquier momento: al comparar cotizaciones, al pedir la visita, con la visita confirmada. Cancelar la visita también cancela la llamada de confirmación en cola. Si la confirmación espera por el horario de llamadas (lun-sáb 9-19), la app dice cuándo se llama al técnico.
- **Aviso de cancelación (2026-11-27):** si la persona cancela una visita que el técnico ya confirmó, se le llama para avisarle (propósito `cancelar`, agente de agenda; sin dirección, nombre ni teléfono; no se reagenda). Si la visita no estaba confirmada, no se llama. Antes de cancelar cualquier cosa la app muestra un popup de confirmación.
- **PRUEBAS: llamadas 24 horas (2026-11-27):** `calls_window_enabled` quedó en `False` por defecto. **ANTES DE PRODUCCIÓN volver a `True`** (lun-sáb 9-19, hora de México) y quitar `CALLS_ALLOWLIST` de pruebas. La API avisa en el arranque si hay llamadas habilitadas sin horario.

## Calificación y calendario (2026-11-27)
- **Calificación 1 a 5 estrellas** de la atención, al cerrar el servicio ("Ya me atendieron") o después desde la solicitud terminada, con comentario opcional (300 caracteres). Solo la ve la persona; por ahora se guarda por cita (`service_rating`, migración 0016) y no cambia las estrellas del directorio. Pendiente decidir cómo usarla para recomendar técnicos.
- **Agregar al calendario:** Apple (archivo .ics, con aviso 1 h antes), Google y Outlook (personal y Microsoft 365), con fecha, técnico y su teléfono (si se compartió), lo acordado y precio, garantía, acceso y la dirección de la persona. En la cita con el fabricante: centro, folio y qué llevar. Los enlaces de Google y Outlook se arman en el navegador de la persona; NidoGuard no se conecta a su calendario.
- **Razón real al fallar con el fabricante (2026-11-27):** la app ya no dice siempre "puede que pida al titular". `manufacturer.reason`: `sin_linea` (no hay línea verificada de la marca), `no_se_llamo` (llamadas apagadas o número fuera de la lista), `no_contestaron`, `no_se_pudo` (sí se llamó y no se agendó). Para probar con una marca hace falta una línea verificada (`python -m admin.fabricantes agregar/verificar`).

## Líneas de servicio de las marcas: búsqueda automática (2026-11-27)
- **NidoGuard busca solo el teléfono de servicio de cada marca** (Claude con búsqueda web, `line_finder.py`) cuando una solicitud va con el fabricante, en segundo plano y una sola vez por marca (si no encuentra, reintenta tras 14 días). Lo guarda `por_verificar` con la página donde lo vio (`source`).
- **Lo encontrado se le muestra a la persona de inmediato** (para que llame ella) con "Me contestaron aquí / No era esa línea". **El asistente de voz NO llama a una línea sin verificar**: una persona de NidoGuard la verifica (`python -m admin.fabricantes verificar`). `listar` marca las que ya tienen 3 confirmaciones y ningún "no" como listas para verificar. Con 2 "no" y más "no" que "sí" se descarta sola.
- Cada marca que se va encontrando le sirve a todos los clientes siguientes. Para llenar la tabla antes: `python -m admin.fabricantes buscar-pendientes`.
- `LINE_FINDER=off` apaga la búsqueda; `LINE_FINDER_MODEL` cambia el modelo. La herramienta de búsqueda web de Claude (`web_search_20250305`) no está verificada contra el servicio real: el CLI debe probarla con una marca conocida.

## Apify para las líneas, y contactos de la persona (2026-11-27)
- **La búsqueda de la línea de servicio usa Apify primero** (`apify~google-search-scraper`, el mismo actor de los manuales): solo toma un teléfono mexicano que aparezca en una página OFICIAL de la marca (dominio con el nombre de la marca; se ignoran tiendas, marketplaces y directorios). Si Apify no encuentra nada, cae a Claude con búsqueda web. `LINE_FINDER=auto|apify|claude|off`, `APIFY_SEARCH_ACTOR`. Los nombres de campos del actor los confirma el CLI con una corrida real.
- **La persona guarda en el perfil del equipo (pestaña Documentos → "Servicio y garantía")**: nombre y teléfono del fabricante, y de la tienda donde lo compró, con la fecha hasta la que la tienda cubre la garantía (ej. Liverpool el primer año y después el fabricante). Se guarda en `extra.servicio` (sin migración). Mientras la tienda cubra la garantía, "agendar con el fabricante" no llama: la app dice que se agenda primero con la tienda y muestra su teléfono.
- **El asistente de voz NO llama a números que la persona escribe**: se le muestran a ella para que llame. Solo se llama a líneas verificadas por NidoGuard (evita usar el asistente para llamar a un tercero).
- Las pruebas fuerzan `line_finder=off`: nunca gastan Apify ni Claude.

## Voz: fallo y dictado de la dirección
- El agente presenta el fallo como "el cliente reporta que…" (equipo, fallo con las palabras del cliente, qué se necesita), confirma que se entendió y nunca inventa causas. Bloque "CÓMO PRESENTAR EL FALLO" en todos los agentes.
- En la confirmación de la cita avisa "le voy a dictar la dirección… ¿tiene dónde anotar o lo espero?", espera, dicta despacio en partes y pregunta si lo anotó completo. La llamada `agendar` ahora lleva `sintoma`.
- Aplicar con `python -m admin.agentes ajustar --aplicar`.

## Calendario de Apple en iPhone
- El enlace de datos (`data:text/calendar`) no abre en Safari del iPhone. Ahora el botón Apple pide `POST /calendar/link` (con sesión) y abre `GET /calendar/<token>.ics` (sin sesión, firmado con HMAC, caduca a los 30 min, no guarda nada) con `Content-Type: text/calendar` y `inline`; así iOS muestra "Agregar a Calendario". Secreto: `CALENDAR_SECRET` (si falta, usa `CLERK_SECRET_KEY`).
- Nota: el evento (con la dirección) viaja dentro del enlace firmado y puede verse en los registros del servidor; si molesta, se quita la dirección del evento.

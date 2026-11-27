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

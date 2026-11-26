# Diseño Liquid Glass de NidoGuard

Fuente de verdad visual: los archivos de `docs/mockups/` (exportados del lienzo "NidoGuard — Mockup Liquid Glass"). Abre `canvas.json` para ver el orden de las pantallas. Si el código y el mockup no coinciden, gana el mockup.

## Reglas
- Fondo marfil `#F6F2EC` con cuatro manchas de color (azul `#7399B5` arriba, cobre `#C18B58` abajo). Sin las manchas el desenfoque no se nota.
- Tres niveles de vidrio (clases `.g`, `.gs`, `.gd` en `apps/web/app/globals.css`):
  - `.g`: tarjetas y filas. Blanco 58 %, desenfoque 20 px.
  - `.gs`: elementos que flotan (barra inferior, selector de hogar). Blanco 66 %, desenfoque 28 px.
  - `.gd`: tarjeta destacada. Degradado azul `#7399B5` a `#183B56`, texto blanco.
- Siempre borde blanco de 1 px y brillo interior arriba (`inset 0 1px 0`). Sombra azul marino suave.
- Radios: tarjeta grande 30, tarjeta 26 a 28, fila 22, ficha de icono 14, botones y barra en pastilla.
- Texto: títulos `#102B40`, secundario `#526574`, Manrope 500 a 800. Cifras grandes 48 px peso 800.
- Botón principal en vidrio oscuro; la acción estrella en cobre (`.btn-copper`); la secundaria en cristal (`.btn-ghost`).
- Barra inferior flotante con botón central de escanear (círculo 70 px, borde blanco).
- Accesibilidad: foco visible de 3 px, alternativa sin desenfoque y modo de alto contraste ya incluidos.

## Estado
- Alineado al mockup: Inicio (y Inicio sin equipos), Equipos, Escanear, Nuevo equipo con hoja "Nueva ubicación", Por confirmar, Expediente (Resumen e Historial), entrada (bienvenida, crear cuenta, código por correo, iniciar sesión) con tema de Clerk en `apps/web/lib/clerkAppearance.ts`.
- Barra inferior de cinco pestañas: Inicio, Equipos, Escanear, Cuidado, Servicios.
- "Muy pronto" (sin servidor todavía, etapas posteriores): Cuidado, Servicios, y las pestañas Documentos y Cuidado del expediente. Se muestran con el mismo estilo, sin datos inventados.
- Lectura de placa estandarizada: solo marca, modelo y número de serie (el tipo solo sirve para nombrar el equipo). Lo demás queda en la transcripción para Documentos y Cuidado.
- Pendiente: Alta manual sin etiqueta (requiere cambio en la API), modos "Placa del equipo" y "Manual" del escáner, nombre "Sugerido" por IA, campana de notificaciones, pantallas de carga, modo oscuro, logotipo vectorial oficial (hoy es una reconstrucción en `components/Logo.tsx`) y decidir si la variante oscura (cian y naranja) es oficial.

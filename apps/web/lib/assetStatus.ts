// Textos de estado del equipo, en lenguaje simple (es-MX).
// "tono": wait = todavia trabajando, ok = listo, action = necesita algo de ti.
export type Tone = "wait" | "ok" | "action";

export const ASSET_STATUS: Record<string, { label: string; detail: string; tone: Tone }> = {
  registrado: { label: "Leyendo la placa", detail: "Estamos leyendo la foto. Suele tardar menos de un minuto.", tone: "wait" },
  leido: { label: "Leyendo la placa", detail: "Ya casi. Estamos terminando de leer los datos.", tone: "wait" },
  por_confirmar: { label: "Listo para revisar", detail: "Leímos los datos. Revísalos y confírmalos cuando quieras.", tone: "ok" },
  necesita_foto: { label: "Necesita otra foto", detail: "No se leyó bien la placa. Toma otra foto de cerca y con buena luz.", tone: "action" },
  faltan_datos: { label: "Faltan datos", detail: "Leímos parte de la placa (por ejemplo, la serie). Agrega una foto del equipo o escribe lo que falta.", tone: "action" },
  completo: { label: "Completo", detail: "Equipo confirmado. Ya está en tu expediente.", tone: "ok" },
};

/** Estados en los que el equipo todavia no tiene resultado de lectura. */
export const STILL_READING = ["registrado", "leido"];

export function statusInfo(status: string) {
  return ASSET_STATUS[status] ?? { label: status, detail: "", tone: "wait" as Tone };
}

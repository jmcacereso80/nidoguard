// Tipos y reglas de Servicios: cotizar y agendar con un técnico o con el fabricante.
// Los datos vienen de la API (/service-requests). Nunca hay datos de contacto del técnico: solo "Técnico N".
export type Urgency = "hoy" | "semana" | "sin_prisa";
export type Route = "tecnico" | "fabricante";
export type ReqStatus = "borrador" | "buscando" | "lista" | "sin_respuesta" | "sin_cita" | "agendada" | "terminada" | "cancelada";
export type PriceType = "fijo" | "rango" | "solo_revision" | "revision_mas_reparacion";
export type Slot = { date: string; window: "manana" | "tarde" };
export type Safety = { kind: string; title: string; advice: string; acknowledged: boolean };
export type Quote = {
  id: string; label: string; rating: number | null; reviews: number | null; distance_km: number | null;
  scope_quoted: string | null; includes: string[]; excludes: string[];
  price_min: number | null; price_max: number | null; price_type: PriceType | null; visit_fee: number | null;
  availability: Slot[]; warranty_days: number | null; invoice: boolean | null; payment_methods: string[];
  matches: "igual" | "parcial" | "distinto" | null; summary: string | null; tags: ("mas_barata" | "mas_pronto" | "mas_cerca")[];
};
export type CallRow = { label: string; distance_km: number | null; status: string; price_min: number | null; price_max: number | null };
export type Appointment = {
  id: string; kind: "tecnico" | "fabricante"; status: "por_confirmar" | "confirmada" | "por_reprogramar" | "cancelada" | "realizada";
  location_type: "domicilio" | "centro"; center_name: string | null; center_address: string | null; folio: string | null; bring: string[];
  starts_at: string | null; ends_at: string | null; requested_slot: Slot | null; registered_by_user: boolean; final_cost: number | null;
  technician_name: string | null;
  agreed: { label: string; scope: string | null; price_min: number | null; price_max: number | null; price_type: PriceType | null; visit_fee: number | null;
            warranty_days: number | null; invoice: boolean | null; rating: number | null; reviews: number | null } | null;
};
export type ServiceRequest = {
  id: string; origin: "tarea" | "libre"; route: Route; status: ReqStatus; equipment_label: string | null; asset_id: string | null;
  care_task_id: string | null; symptom: string | null; scope_text: string | null; specialty: string | null; urgency: Urgency;
  safety: Safety | null; warranty: { ends_on: string; days_left: number; provider: string | null } | null;
  zone: string | null; address_complete: boolean; radius_km: number; target_quotes: number; created_at: string; quote_count: number;
  appointment: Appointment | null; quotes?: Quote[]; calls?: CallRow[];
  manufacturer: { brand: string | null; model: string | null; serial: string | null; holder_name: string | null; phone: string | null; address: string | null; warranty_ends_on: string | null } | null;
};
export type Address = { street: string | null; colony: string | null; postal_code: string | null; city: string | null; state: string | null; search_radius_km: number; complete: boolean };

export const NO_COBRO = "NidoGuard no cobra por el servicio. Solo te conectamos con el técnico; pagas directo a él.";
export const NO_COBRO_FABRICANTE = "NidoGuard no cobra por conectarte con el fabricante. Lo que cobre el servicio lo pagas directo a ellos, si no lo cubre la garantía.";

export const URGENCY_LABEL: Record<Urgency, string> = { hoy: "Hoy", semana: "Esta semana", sin_prisa: "Sin prisa" };

const money0 = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
export function money(n: number): string { return money0.format(Math.round(n)); }

/** "$550", "$600 a $800". */
export function priceLabel(q: Pick<Quote, "price_min" | "price_max" | "price_type">): string {
  if (q.price_min == null) return "Sin precio";
  if (q.price_max != null && Math.round(q.price_max) !== Math.round(q.price_min)) return `${money(q.price_min)} a ${money(q.price_max)}`;
  return money(q.price_min);
}
export function priceNote(t: PriceType | null): string {
  return t === "fijo" ? "precio fijo" : t === "rango" ? "según lo que encuentre" : t === "solo_revision" ? "solo la revisión"
    : t === "revision_mas_reparacion" ? "revisión más reparación" : "";
}
export function distanceLabel(km: number | null): string { return km == null ? "" : `${km.toFixed(1)} km aprox.`; }
export function warrantyLabel(days: number | null): string { return days ? `Garantía ${days} días` : "No dijo garantía"; }
export function invoiceLabel(v: boolean | null): string { return v == null ? "No dijo si da factura" : v ? "Da factura" : "Sin factura"; }

const dayFmt = (iso: string, o: Intl.DateTimeFormatOptions) => new Date(`${iso}T12:00:00Z`).toLocaleDateString("es-MX", { ...o, timeZone: "UTC" }).replace(/\./g, "");
/** "Vie 28 nov" */
export function shortDay(iso: string): string {
  const wd = dayFmt(iso, { weekday: "short" }).replace(",", "");
  return `${wd.charAt(0).toUpperCase()}${wd.slice(1)} ${dayFmt(iso, { day: "numeric", month: "short" }).replace(/ de /g, " ")}`;
}
const WINDOW: Record<Slot["window"], string> = { manana: "mañana", tarde: "tarde" };
const WINDOW_LONG: Record<Slot["window"], string> = { manana: "Mañana, de 9:00 a 13:00", tarde: "Tarde, de 14:00 a 19:00" };
export const slotChip = (s: Slot) => `${shortDay(s.date)} · ${WINDOW[s.window]}`;
export const slotWindowLong = (s: Slot) => WINDOW_LONG[s.window];

const MX = "America/Mexico_City";
/** "viernes 28 de noviembre" (hora de México) */
export function longDay(iso: string): string {
  return new Date(iso).toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long", timeZone: MX }).replace(",", "");
}
/** "entre 16:00 y 18:00" */
export function hourRange(start: string, end: string | null): string {
  const h = (x: string) => new Date(x).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: MX });
  return end ? `entre ${h(start)} y ${h(end)}` : `a las ${h(start)}`;
}

export type Sort = "precio" | "pronto" | "cerca";
/** Ordena las cotizaciones. Las que cotizaron otra cosa van al final: no se comparan con las demás. */
export function sortQuotes(quotes: Quote[], by: Sort): Quote[] {
  const key = (q: Quote): number | string =>
    by === "precio" ? q.price_min ?? Infinity : by === "pronto" ? q.availability[0]?.date ?? "9999" : q.distance_km ?? Infinity;
  return [...quotes].sort((a, b) => (a.matches === "distinto" ? 1 : 0) - (b.matches === "distinto" ? 1 : 0) || (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0));
}
export const TAG_LABEL = { mas_barata: "Más barata", mas_pronto: "Más pronto", mas_cerca: "Más cerca" } as const;

export type Tone = "green" | "blue" | "cobre" | "gray";
/** Etiqueta de estado para la lista de solicitudes. */
export function statusChip(r: Pick<ServiceRequest, "status" | "route" | "quote_count" | "appointment">): { text: string; tone: Tone; icon: string } {
  const ap = r.appointment;
  switch (r.status) {
    case "borrador": return { text: "Falta confirmar", tone: "cobre", icon: "clock" };
    case "buscando": return { text: r.route === "fabricante" ? "Llamando al fabricante" : `Buscando · ${r.quote_count} de 5`, tone: "blue", icon: "phone" };
    case "lista": return { text: `${r.quote_count} cotizaciones listas`, tone: "green", icon: "check" };
    case "sin_respuesta": return { text: "Sin cotizaciones todavía", tone: "cobre", icon: "clock" };
    case "sin_cita": return { text: "Agéndala tú", tone: "cobre", icon: "phone" };
    case "agendada": {
      if (ap?.status === "por_confirmar") return { text: "Esperando confirmación del técnico", tone: "blue", icon: "clock" };
      const d = ap?.starts_at ? longDay(ap.starts_at).split(" ").slice(0, 3).join(" ") : "";
      return { text: ap?.kind === "fabricante" ? `Cita con el fabricante${d ? ` · ${d}` : ""}` : `Visita confirmada${d ? ` · ${d}` : ""}`, tone: "green", icon: ap?.kind === "fabricante" ? "building" : "calendar" };
    }
    case "terminada": return { text: "Terminada · Quedó en el Historial", tone: "gray", icon: "check" };
    default: return { text: "Cancelada", tone: "gray", icon: "x" };
  }
}
export const isLive = (s: ReqStatus) => ["borrador", "buscando", "lista", "sin_respuesta", "sin_cita", "agendada"].includes(s);

/** ¿Hay que seguir preguntando a la API? Mientras se busca o la visita espera confirmación. */
export function shouldPoll(r: Pick<ServiceRequest, "status" | "appointment"> | undefined): boolean {
  return !!r && (r.status === "buscando" || (r.status === "agendada" && r.appointment?.status === "por_confirmar"));
}
export function progressOf(r: Pick<ServiceRequest, "quote_count" | "target_quotes" | "calls">) {
  const calls = r.calls ?? [];
  const done = calls.filter((c) => c.status !== "en_cola").length;
  return { got: r.quote_count, target: r.target_quotes, done, total: calls.length, pct: Math.min(100, Math.round((r.quote_count / Math.max(1, r.target_quotes)) * 100)) };
}
export function callText(c: CallRow): string {
  switch (c.status) {
    case "completada": return c.price_min != null ? `Cotizó: ${priceLabel({ price_min: c.price_min, price_max: c.price_max, price_type: null })}` : "Contestó";
    case "sin_respuesta": return "No contestó. Reintentamos más tarde";
    case "rechazo": return "No atiende este equipo";
    case "cancelada": return "Ya no hizo falta llamar";
    case "llamando": return "Llamando ahora…";
    default: return "En espera";
  }
}

/** Archivo de calendario (.ics) como enlace de datos, para "Agregar al calendario". */
export function icsLink(title: string, startISO: string, endISO: string | null, place?: string | null): string {
  const f = (iso: string) => new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const esc = (t: string) => t.replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");
  const end = endISO ?? new Date(new Date(startISO).getTime() + 2 * 3600_000).toISOString();
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NidoGuard//ES", "BEGIN:VEVENT", `UID:${f(startISO)}-${esc(title).length}@nidoguard.com`,
    `DTSTAMP:${f(new Date().toISOString())}`, `DTSTART:${f(startISO)}`, `DTEND:${f(end)}`, `SUMMARY:${esc(title)}`, ...(place ? [`LOCATION:${esc(place)}`] : []), "END:VEVENT", "END:VCALENDAR"];
  return `data:text/calendar;charset=utf-8,${encodeURIComponent(lines.join("\r\n"))}`;
}
export const mapsLink = (address: string) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;

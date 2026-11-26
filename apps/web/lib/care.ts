// Tipos y reglas de Documentos y Cuidado. Los datos vienen de la API (/assets/{id}/documents y /care);
// mientras esos endpoints no existan, las pantallas muestran su estado vacío en lugar de inventar datos.
// El manual de uso lo busca la IA por marca y modelo; la persona no tiene que subirlo.
export type ManualStatus = "listo" | "buscando" | "no_encontrado";
export type ManualItem = { id: string; title: string; note: string | null; url: string | null; status: ManualStatus };
export type WarrantyInfo = { ends_on: string; provider: string | null; price?: number | null; confirmed: boolean; estimated?: boolean; document_id?: string };
export type WarrantyPending = { document_id: string; filename: string };
export type InvoiceInfo = { id: string; uploaded_at: string; name: string };
export type DocumentsData = { manuals: ManualItem[]; model_confirmed?: boolean; warranty: WarrantyInfo | null; warranty_pending?: WarrantyPending | null; invoice: InvoiceInfo | null };

export type CareSource = "manual" | "sugerencia";
export type Unit = "dia" | "semana" | "mes" | "anio";
export type Every = { n: number; unit: Unit };
export type Priority = "alta" | "media" | "baja";
export type CareTask = { id: string; title: string; detail: string | null; every: Every; next_due: string | null; source: CareSource; instructions: string | null; done_at: string | null; priority?: Priority; confirmed?: boolean; needs_technician?: boolean };
export type CareData = { model_confirmed: boolean; tasks: CareTask[] };

export const SOURCE_LABEL: Record<CareSource, string> = {
  manual: "Fuente: manual del fabricante",
  sugerencia: "Sugerencia de NidoGuard, por confirmar",
};

const DAY = 86_400_000;
/** Días que faltan para el vencimiento (0 si vence hoy, negativo si ya venció). */
export function daysLeft(endsOn: string, now: Date = new Date()): number {
  const end = new Date(`${endsOn}T00:00:00`);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((end.getTime() - today.getTime()) / DAY);
}

export type WarrantyView = { text: string; badge: string; tone: "ok" | "warn" | "off" };
/** Texto y color de la garantía. Solo se alerta si está confirmada; una estimada nunca se presenta como segura. */
export function warrantyView(w: WarrantyInfo, now: Date = new Date()): WarrantyView {
  const d = daysLeft(w.ends_on, now);
  const fecha = new Date(`${w.ends_on}T00:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" }).replace(/\./g, "");
  const prefijo = w.estimated || !w.confirmed ? "Estimada, por confirmar: " : "";
  if (d < 0) return { text: `${prefijo}Venció el ${fecha}`, badge: "Vencida", tone: "off" };
  const badge = d === 0 ? "Vence hoy" : d === 1 ? "1 día" : d <= 60 ? `${d} días` : `${Math.round(d / 30)} meses`;
  return { text: `${prefijo}Vence el ${fecha}`, badge, tone: d <= 60 && w.confirmed && !w.estimated ? "warn" : "ok" };
}
/** La alerta de garantía por vencer en Cuidado solo sale si la garantía está confirmada. */
export function showWarrantyAlert(w: WarrantyInfo | null, now: Date = new Date()): boolean {
  return !!w && w.confirmed && !w.estimated && daysLeft(w.ends_on, now) >= 0 && daysLeft(w.ends_on, now) <= 60;
}

// ---- Frecuencia de los cuidados: diario, semanal, mensual, trimestral, semestral, anual, bianual... ----
const UNIT_DAYS: Record<Unit, number> = { dia: 1, semana: 7, mes: 30, anio: 365 };
export function everyDays(e: Every): number { return e.n * UNIT_DAYS[e.unit]; }

const NAMED: Record<string, string> = {
  "1dia": "Diario", "1semana": "Semanal", "2semana": "Cada 2 semanas", "1mes": "Mensual", "2mes": "Bimestral",
  "3mes": "Trimestral", "4mes": "Cada 4 meses", "6mes": "Semestral", "1anio": "Anual", "2anio": "Bianual (cada 2 años)",
};
const PLURAL: Record<Unit, [string, string]> = { dia: ["día", "días"], semana: ["semana", "semanas"], mes: ["mes", "meses"], anio: ["año", "años"] };
export function everyLabel(e: Every): string {
  return NAMED[`${e.n}${e.unit}`] ?? `Cada ${e.n} ${PLURAL[e.unit][e.n === 1 ? 0 : 1]}`;
}
/** Texto corto para la tarjeta: "Cada 3 meses". */
export function everyShort(e: Every): string {
  return e.n === 1 ? `Cada ${PLURAL[e.unit][0]}` : `Cada ${e.n} ${PLURAL[e.unit][1]}`;
}

export type CareGroup = { key: string; label: string; tasks: CareTask[] };
const BUCKETS: [string, string, number][] = [
  ["diario", "Diario", 1], ["semanal", "Semanal", 14], ["mensual", "Mensual", 45], ["trimestral", "Cada 2 a 3 meses", 100],
  ["semestral", "Cada 4 a 6 meses", 200], ["anual", "Anual", 500], ["largo", "Cada 2 años o más", Infinity],
];
/** Agrupa por frecuencia, de lo más seguido a lo menos seguido. Dentro de cada grupo, primero lo que toca antes. */
export function groupByFrequency(tasks: CareTask[]): CareGroup[] {
  const out: CareGroup[] = BUCKETS.map(([key, label]) => ({ key, label, tasks: [] }));
  for (const t of tasks) {
    const d = everyDays(t.every);
    out[BUCKETS.findIndex(([, , max]) => d <= max)].tasks.push(t);
  }
  for (const g of out) g.tasks.sort((a, b) => (a.next_due ?? "9999").localeCompare(b.next_due ?? "9999") || everyDays(a.every) - everyDays(b.every));
  return out.filter((g) => g.tasks.length > 0);
}

export type DueView = { text: string; tone: "vencido" | "hoy" | "normal" };
/** Cuándo toca un cuidado: "Toca hoy", "Toca mañana", "Próximo: 15 ene" o "Venció el 20 nov". */
export function dueLabel(nextDue: string, now: Date = new Date()): DueView {
  const d = daysLeft(nextDue, now);
  const corta = new Date(`${nextDue}T00:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short" }).replace(/\./g, "");
  if (d < 0) return { text: `Venció el ${corta}`, tone: "vencido" };
  if (d === 0) return { text: "Toca hoy", tone: "hoy" };
  if (d === 1) return { text: "Toca mañana", tone: "normal" };
  return { text: `Próximo: ${corta}`, tone: "normal" };
}

// ---- Pantalla Cuidado del menú ----
const DOW = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const isoOf = (d: Date) => `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
const parse = (iso: string) => new Date(`${iso}T00:00:00Z`);
export function addDaysISO(iso: string, n: number): string { const d = parse(iso); d.setUTCDate(d.getUTCDate() + n); return isoOf(d); }

export type WeekDay = { iso: string; dow: string; num: number };
/** Los 7 días (lunes a domingo) de la semana de `todayISO`, movida `offset` semanas. */
export function weekDays(todayISO: string, offset = 0): WeekDay[] {
  const d = parse(todayISO);
  const lunes = addDaysISO(todayISO, -((d.getUTCDay() + 6) % 7) + offset * 7);
  return Array.from({ length: 7 }, (_, i) => { const iso = addDaysISO(lunes, i); const x = parse(iso); return { iso, dow: DOW[x.getUTCDay()], num: x.getUTCDate() }; });
}
export function monthLabel(iso: string): string {
  const m = parse(iso).toLocaleDateString("es-MX", { month: "long", timeZone: "UTC" });
  return `${m.charAt(0).toUpperCase()}${m.slice(1)} ${parse(iso).getUTCFullYear()}`;
}
/** "jueves 26 de noviembre" */
export function longDate(iso: string): string {
  return parse(iso).toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }).replace(",", "");
}
export function shortDate(iso: string): string {
  return parse(iso).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).replace(/\./g, "");
}

export const PRIORITY_LABEL: Record<Priority, string> = { alta: "Prioridad alta", media: "Prioridad media", baja: "Prioridad baja" };
/** Primer paso de las instrucciones, sin numeración. */
export function firstStep(instructions: string | null): string | null {
  const l = (instructions ?? "").split("\n").map((x) => x.replace(/^\s*(\d+[.)]|[-•*])\s*/, "").trim()).find(Boolean);
  return l || null;
}

export type HouseholdTask = CareTask & { asset_id: string; asset_name: string; space_name: string | null };
/** Vencidas: la fecha ya pasó. Próximas: hoy o después. Ambas ordenadas por fecha. */
export function splitByDue(tasks: HouseholdTask[], todayISO: string): { overdue: HouseholdTask[]; upcoming: HouseholdTask[] } {
  const by = (a: HouseholdTask, b: HouseholdTask) => (a.next_due ?? "").localeCompare(b.next_due ?? "") || a.title.localeCompare(b.title);
  const ok = tasks.filter((t) => t.next_due);
  return { overdue: ok.filter((t) => t.next_due! < todayISO).sort(by), upcoming: ok.filter((t) => t.next_due! >= todayISO).sort(by) };
}

export type MonthCell = { iso: string; num: number } | null;
/** Cuadrícula del mes de `todayISO` movido `offset` meses: filas de lunes a domingo; los huecos van como null. */
export function monthGrid(todayISO: string, offset = 0): { label: string; first: string; cells: MonthCell[] } {
  const base = parse(todayISO);
  const first = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth() + offset, 1));
  const dias = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
  const cells: MonthCell[] = Array((first.getUTCDay() + 6) % 7).fill(null);
  for (let d = 1; d <= dias; d++) cells.push({ iso: isoOf(new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), d))), num: d });
  while (cells.length % 7) cells.push(null);
  return { label: monthLabel(isoOf(first)), first: isoOf(first), cells };
}

// Tipos y reglas de Documentos y Cuidado. Los datos vienen de la API (/assets/{id}/documents y /care);
// mientras esos endpoints no existan, las pantallas muestran su estado vacío en lugar de inventar datos.
export type ManualItem = { id: string; title: string; note: string | null; url: string | null; status: "listo" | "buscando" };
export type WarrantyInfo = { ends_on: string; provider: string | null; confirmed: boolean; estimated?: boolean };
export type InvoiceInfo = { id: string; uploaded_at: string; name: string };
export type DocumentsData = { manuals: ManualItem[]; warranty: WarrantyInfo | null; invoice: InvoiceInfo | null };

export type CareSource = "manual" | "sugerencia";
export type CareTask = { id: string; title: string; detail: string | null; every: string | null; source: CareSource; instructions: string | null; done_at: string | null };
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

import test from "node:test";
import assert from "node:assert/strict";
import { daysLeft, warrantyView, showWarrantyAlert, everyLabel, everyShort, groupByFrequency, dueLabel } from "./care.ts";
import type { CareTask, Every } from "./care.ts";

const hoy = new Date(2026, 10, 25);
test("días que faltan", () => {
  assert.equal(daysLeft("2026-12-23", hoy), 28);
  assert.equal(daysLeft("2026-11-25", hoy), 0);
  assert.equal(daysLeft("2026-11-20", hoy), -5);
});
test("garantía confirmada por vencer", () => {
  const v = warrantyView({ ends_on: "2026-12-23", provider: null, confirmed: true }, hoy);
  assert.equal(v.badge, "28 días"); assert.equal(v.tone, "warn"); assert.match(v.text, /^Vence el 23 dic 2026$/);
});
test("garantía lejana y vencida", () => {
  assert.equal(warrantyView({ ends_on: "2027-11-25", provider: null, confirmed: true }, hoy).tone, "ok");
  assert.equal(warrantyView({ ends_on: "2026-10-01", provider: null, confirmed: true }, hoy).badge, "Vencida");
});
test("estimada o sin confirmar nunca alerta", () => {
  const w = { ends_on: "2026-12-23", provider: null, confirmed: false };
  assert.equal(showWarrantyAlert(w, hoy), false);
  assert.match(warrantyView(w, hoy).text, /^Estimada, por confirmar/);
  assert.equal(showWarrantyAlert({ ...w, confirmed: true }, hoy), true);
  assert.equal(showWarrantyAlert(null, hoy), false);
});

test("etiquetas de frecuencia", () => {
  const casos: [Every, string][] = [
    [{ n: 1, unit: "dia" }, "Diario"], [{ n: 1, unit: "semana" }, "Semanal"], [{ n: 1, unit: "mes" }, "Mensual"],
    [{ n: 3, unit: "mes" }, "Trimestral"], [{ n: 6, unit: "mes" }, "Semestral"], [{ n: 1, unit: "anio" }, "Anual"],
    [{ n: 2, unit: "anio" }, "Bianual (cada 2 años)"], [{ n: 5, unit: "anio" }, "Cada 5 años"], [{ n: 10, unit: "dia" }, "Cada 10 días"],
  ];
  for (const [e, l] of casos) assert.equal(everyLabel(e), l);
  assert.equal(everyShort({ n: 3, unit: "mes" }), "Cada 3 meses");
  assert.equal(everyShort({ n: 1, unit: "semana" }), "Cada semana");
});
test("agrupa de lo más seguido a lo menos seguido", () => {
  const mk = (id: string, every: Every, next_due: string | null = null): CareTask => ({ id, title: id, detail: null, every, next_due, source: "sugerencia", instructions: null, done_at: null });
  const g = groupByFrequency([mk("a", { n: 1, unit: "anio" }), mk("b", { n: 1, unit: "dia" }), mk("c", { n: 3, unit: "mes" }), mk("d", { n: 1, unit: "semana" }), mk("e", { n: 2, unit: "anio" }), mk("f", { n: 1, unit: "mes" }, "2026-12-01"), mk("g", { n: 1, unit: "mes" }, "2026-11-30")]);
  assert.deepEqual(g.map((x) => x.key), ["diario", "semanal", "mensual", "trimestral", "anual", "largo"]);
  assert.deepEqual(g[2].tasks.map((x) => x.id), ["g", "f"]);
});

test("cuándo toca un cuidado", () => {
  assert.deepEqual(dueLabel("2026-11-20", hoy), { text: "Venció el 20 nov", tone: "vencido" });
  assert.deepEqual(dueLabel("2026-11-25", hoy), { text: "Toca hoy", tone: "hoy" });
  assert.deepEqual(dueLabel("2026-11-26", hoy), { text: "Toca mañana", tone: "normal" });
  assert.deepEqual(dueLabel("2027-01-15", hoy), { text: "Próximo: 15 ene", tone: "normal" });
});

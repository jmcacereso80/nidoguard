import test from "node:test";
import assert from "node:assert/strict";
import { daysLeft, warrantyView, showWarrantyAlert } from "./care.ts";

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

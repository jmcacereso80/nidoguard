import test from "node:test";
import assert from "node:assert/strict";
import { priceLabel, priceNote, shortDay, slotChip, sortQuotes, statusChip, shouldPoll, progressOf, callText, distanceLabel, warrantyLabel, invoiceLabel, longDay, hourRange } from "./servicios.ts";
import type { Quote } from "./servicios.ts";

const q = (o: Partial<Quote>): Quote => ({ id: "x", label: "Técnico 1", rating: 4.5, reviews: 10, distance_km: 3, scope_quoted: "x", includes: [], excludes: [], price_min: 500, price_max: 500,
  price_type: "fijo", visit_fee: 0, availability: [{ date: "2026-11-28", window: "tarde" }], warranty_days: 30, invoice: true, payment_methods: [], matches: "igual", summary: null, excerpt: null, tags: [], ...o });

test("precio: fijo, rango y sin precio", () => {
  assert.equal(priceLabel({ price_min: 550, price_max: 550, price_type: "fijo" }), "$550");
  assert.equal(priceLabel({ price_min: 600, price_max: 800, price_type: "rango" }), "$600 a $800");
  assert.equal(priceLabel({ price_min: null, price_max: null, price_type: null }), "Sin precio");
  assert.equal(priceNote("rango"), "según lo que encuentre");
});
test("fechas de los horarios", () => {
  assert.equal(shortDay("2026-11-28"), "Sáb 28 nov");
  assert.equal(slotChip({ date: "2026-11-28", window: "tarde" }), "Sáb 28 nov · tarde");
});
test("fecha y hora de la visita, en hora de México", () => {
  assert.equal(longDay("2026-11-28T22:00:00+00:00"), "sábado 28 de noviembre");
  assert.equal(hourRange("2026-11-28T22:00:00+00:00", "2026-12-01T00:00:00+00:00"), "entre 16:00 y 18:00");
});
test("ordenar: la que cotizó otra cosa va al final aunque sea la más barata", () => {
  const a = q({ id: "a", price_min: 700 }), b = q({ id: "b", price_min: 400, matches: "distinto" }), c = q({ id: "c", price_min: 550 });
  assert.deepEqual(sortQuotes([a, b, c], "precio").map((x) => x.id), ["c", "a", "b"]);
  assert.deepEqual(sortQuotes([q({ id: "a", distance_km: 5 }), q({ id: "b", distance_km: 1 })], "cerca").map((x) => x.id), ["b", "a"]);
  assert.deepEqual(sortQuotes([q({ id: "a", availability: [{ date: "2026-12-02", window: "tarde" }] }), q({ id: "b" })], "pronto").map((x) => x.id), ["b", "a"]);
});
test("estado en la lista", () => {
  assert.equal(statusChip({ status: "buscando", route: "tecnico", quote_count: 2, appointment: null }).text, "Buscando · 2 de 5");
  assert.equal(statusChip({ status: "lista", route: "tecnico", quote_count: 5, appointment: null }).tone, "green");
  assert.equal(statusChip({ status: "sin_cita", route: "fabricante", quote_count: 0, appointment: null }).text, "Agéndala tú");
});
test("se sigue preguntando solo mientras algo está pasando", () => {
  assert.equal(shouldPoll({ status: "buscando", appointment: null }), true);
  assert.equal(shouldPoll({ status: "lista", appointment: null }), false);
  assert.equal(shouldPoll(undefined), false);
});
test("avance de la búsqueda y texto de cada llamada", () => {
  const calls = [{ label: "Técnico 1", distance_km: 2, status: "completada", price_min: 550, price_max: 550 }, { label: "Técnico 2", distance_km: 3, status: "en_cola", price_min: null, price_max: null }];
  assert.deepEqual(progressOf({ quote_count: 1, target_quotes: 5, calls }), { got: 1, target: 5, done: 1, total: 2, pct: 20 });
  assert.equal(callText(calls[0]), "Cotizó: $550");
  assert.equal(callText({ ...calls[0], status: "sin_respuesta" }), "No contestó. Reintentamos más tarde");
});
test("textos cortos", () => {
  assert.equal(distanceLabel(3.44), "3.4 km aprox."); assert.equal(distanceLabel(null), "");
  assert.equal(warrantyLabel(30), "Garantía 30 días"); assert.equal(warrantyLabel(null), "No dijo garantía");
  assert.equal(invoiceLabel(true), "Da factura"); assert.equal(invoiceLabel(null), "No dijo si da factura");
});

import { icsLink, mapsLink } from "./servicios.ts";
test("archivo de calendario y mapa", () => {
  const ics = decodeURIComponent(icsLink("Visita, técnico", "2026-11-28T22:00:00Z", "2026-11-29T00:00:00Z", "Av. Ejemplo 1").replace("data:text/calendar;charset=utf-8,", ""));
  assert.match(ics, /DTSTART:20261128T220000Z/); assert.match(ics, /DTEND:20261129T000000Z/); assert.match(ics, /SUMMARY:Visita\\, técnico/); assert.match(ics, /LOCATION:Av. Ejemplo 1/);
  assert.equal(mapsLink("Av. Juárez 1, CDMX"), "https://www.google.com/maps/search/?api=1&query=Av.%20Ju%C3%A1rez%201%2C%20CDMX");
});

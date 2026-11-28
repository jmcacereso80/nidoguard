import test from "node:test";
import assert from "node:assert/strict";
import type { Me } from "./api.ts";
import { iniciales, lineaDireccion, pendientes, quitarLada } from "./micasa.ts";

const base = (over: Partial<Me["user"]> = {}, completa = true): Me => ({
  user: { id: "1", email: "a@b.mx", name: null, first_name: "Juan Manuel", last_name: "Cáceres", phone: "+525512345678", ...over },
  home: { id: "h", name: "Casa", properties: [{ id: "p", name: "Casa", address: { street: "Calle 1", colony: "Del Valle", postal_code: null, city: "CDMX", state: null, search_radius_km: 15, complete: completa, is_primary: true } }] },
  suggested_spaces: [],
});

test("cuenta lo que falta para pedir un servicio", () => {
  assert.equal(pendientes(base()).listos, 3);
  const p = pendientes(base({ phone: null }, false));
  assert.deepEqual([p.nombre, p.direccion, p.telefono, p.listos], [true, false, false, 1]);
  assert.equal(pendientes(base({ first_name: " " })).nombre, false);
});
test("iniciales y textos", () => {
  assert.equal(iniciales(base()), "JC");
  assert.equal(iniciales(base({ first_name: null, last_name: null, name: "ana" })), "A");
  assert.equal(lineaDireccion({ street: "Calle 1", colony: null, city: "CDMX" }), "Calle 1, CDMX");
  assert.equal(lineaDireccion({ street: null, colony: null, city: null }), "");
  assert.equal(quitarLada("+525512345678"), "5512345678");
});

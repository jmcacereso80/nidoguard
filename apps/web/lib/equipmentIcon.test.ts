import test from "node:test";
import assert from "node:assert/strict";
import { equipmentIcon } from "./equipmentIcon.ts";

const casos: [string, string][] = [
  ["Cafetera Nespresso", "cafetera"], ["Licuadora", "licuadora"], ["Horno de microondas", "microondas"],
  ["Horno eléctrico", "horno"], ["Estufa", "estufa"], ["Lavavajillas", "lavavajillas"], ["Lavadora", "washer"],
  ["Tostador", "tostador"], ["Freidora de aire", "freidora"], ["Batidora", "batidora"], ["Hervidor eléctrico", "hervidor"],
  ["Olla de presión", "olla"], ["Campana extractora", "campana"], ["Refrigerador", "fridge"], ["Televisión", "tv"],
  ["Aire acondicionado", "ac"], ["Aspiradora", "box"],
];
for (const [name, icon] of casos) test(`${name} -> ${icon}`, () => assert.equal(equipmentIcon({ name }), icon));

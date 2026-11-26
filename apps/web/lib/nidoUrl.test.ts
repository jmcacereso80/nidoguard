import test from "node:test";
import assert from "node:assert/strict";
import { parseNidoUrl } from "./nidoUrl.ts";

test("acepta etiquetas y kits de NidoGuard", () => {
  assert.equal(parseNidoUrl("https://nidoguard.com/t/ABCDEF234567"), "/t/ABCDEF234567");
  assert.equal(parseNidoUrl("https://app.nidoguard.com/k/ABCDEF234567"), "/k/ABCDEF234567");
});
test("acepta el codigo corto de un kit, con o sin guion", () => {
  assert.equal(parseNidoUrl("DT5ZK-FL8GE"), "/k/DT5ZKFL8GE");
  assert.equal(parseNidoUrl("dt5zkfl8ge"), "/k/DT5ZKFL8GE");
  assert.equal(parseNidoUrl("0000000000"), "/k/0000000000");
});
test("rechaza codigos que no son de kit", () => {
  assert.equal(parseNidoUrl("C1-0000000000"), null);
  assert.equal(parseNidoUrl("DT5ZK-FL8G"), null);
});
test("rechaza dominios ajenos, rutas raras y http", () => {
  assert.equal(parseNidoUrl("https://evil.com/t/ABCDEF234567"), null);
  assert.equal(parseNidoUrl("https://nidoguard.com.evil.com/t/ABCDEF234567"), null);
  assert.equal(parseNidoUrl("http://nidoguard.com/t/ABCDEF234567"), null);
  assert.equal(parseNidoUrl("https://nidoguard.com/admin"), null);
  assert.equal(parseNidoUrl("https://nidoguard.com/t/x"), null);
  assert.equal(parseNidoUrl("no es url"), null);
});

import test from "node:test";
import assert from "node:assert/strict";
import { parseNidoUrl } from "./nidoUrl.ts";

test("acepta etiquetas y kits de NidoGuard", () => {
  assert.equal(parseNidoUrl("https://nidoguard.com/t/ABCDEF234567"), "/t/ABCDEF234567");
  assert.equal(parseNidoUrl("https://app.nidoguard.com/k/ABCDEF234567"), "/k/ABCDEF234567");
});
test("rechaza dominios ajenos, rutas raras y http", () => {
  assert.equal(parseNidoUrl("https://evil.com/t/ABCDEF234567"), null);
  assert.equal(parseNidoUrl("https://nidoguard.com.evil.com/t/ABCDEF234567"), null);
  assert.equal(parseNidoUrl("http://nidoguard.com/t/ABCDEF234567"), null);
  assert.equal(parseNidoUrl("https://nidoguard.com/admin"), null);
  assert.equal(parseNidoUrl("https://nidoguard.com/t/x"), null);
  assert.equal(parseNidoUrl("no es url"), null);
});

import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type { NextConfig } from "next";

// Lee el .env de la raiz del repo (el mismo que usa la API). Lo leemos a mano:
// loadEnvConfig de Next omite el archivo cuando el proceso padre ya cargo su propio entorno.
// Nunca imprime valores.
function loadRootEnv() {
  const file = path.resolve(__dirname, "../..", ".env");
  if (!fs.existsSync(file)) return;
  for (const raw of fs.readFileSync(file, "utf8").split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq < 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim().replace(/^['"]|['"]$/g, "");
    if (process.env[key] === undefined) process.env[key] = value;
  }
}
loadRootEnv();

// En el .env la clave publicable se llama CLERK_API_KEY. Clerk la busca como
// NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY tanto en servidor como en cliente.
process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ??= process.env.CLERK_API_KEY ?? "";

// Version visible en pantalla: el commit con el que se arranco la web (git rev-parse).
let appVersion = "sin git";
try {
  appVersion = execSync("git rev-parse --short HEAD", { cwd: path.resolve(__dirname, "../..") }).toString().trim();
} catch {}

// En desarrollo todo entra por un solo host (dev.nidoguard.com, por el tunel de Cloudflare).
// La web reenvia /api/* a la API local, asi el celular no necesita un segundo dominio ni CORS.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  transpilePackages: ["@nidoguard/design-tokens"],
  allowedDevOrigins: ["dev.nidoguard.com"],
  env: {
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY,
    NEXT_PUBLIC_APP_VERSION: `dev ${appVersion}`,
    APP_VERSION: `dev ${appVersion}`,  // la ruta /version la devuelve para detectar versiones nuevas
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_INTERNAL_URL}/:path*` }];
  },
};
export default config;

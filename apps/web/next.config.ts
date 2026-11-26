import path from "node:path";
import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";

// Lee el .env de la raiz del repo (el mismo que usa la API).
loadEnvConfig(path.resolve(__dirname, "../.."));

const config: NextConfig = {
  transpilePackages: ["@nidoguard/design-tokens"],
  env: {
    // En el .env la clave publicable se llama CLERK_API_KEY.
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? process.env.CLERK_API_KEY ?? "",
  },
};
export default config;

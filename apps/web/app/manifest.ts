import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NidoGuard", short_name: "NidoGuard", lang: "es-MX", start_url: "/inicio", display: "standalone",
    background_color: "#f6f2ec", theme_color: "#183b56",
    icons: [],
  };
}

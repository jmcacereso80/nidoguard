"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

// Si el servidor tiene una version mas nueva que la que esta abierta, se recarga la app una vez.
// Asi no hace falta borrar los datos del sitio para ver los cambios.
function revisarVersion() {
  const actual = process.env.NEXT_PUBLIC_APP_VERSION;
  if (!actual) return;
  fetch(`/version?t=${Date.now()}`, { cache: "no-store" })
    .then((r) => r.json())
    .then(({ version }) => {
      const clave = `ng:recargado:${version}`;
      if (version && version !== actual && !sessionStorage.getItem(clave)) {
        sessionStorage.setItem(clave, "1");
        location.reload();
      }
    })
    .catch(() => {});
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 15_000 } } }));
  useEffect(() => {
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
    revisarVersion();
    const alVolver = () => { if (document.visibilityState === "visible") revisarVersion(); };
    document.addEventListener("visibilitychange", alVolver);
    return () => document.removeEventListener("visibilitychange", alVolver);
  }, []);
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

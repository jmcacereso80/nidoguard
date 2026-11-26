// Service worker minimo: la app se instala como PWA. El cache sin conexion llega con Serwist.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

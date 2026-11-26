const APP_HOSTS = ["nidoguard.com", "app.nidoguard.com", "localhost"];

/** Solo acepta URLs de NidoGuard con la forma /t/<token> o /k/<codigo>. Devuelve la ruta interna. */
export function parseNidoUrl(text: string): string | null {
  try {
    const u = new URL(text);
    if (!APP_HOSTS.includes(u.hostname)) return null;
    if (u.protocol !== "https:" && u.hostname !== "localhost") return null;
    const m = u.pathname.match(/^\/(t|k)\/([A-Za-z0-9]{6,64})$/);
    return m ? `/${m[1]}/${m[2]}` : null;
  } catch { return null; }
}

const APP_HOSTS = ["nidoguard.com", "app.nidoguard.com", "dev.nidoguard.com", "localhost"];

/** Codigo corto de kit tal como va en el QR: XXXXX-XXXXX (el guion es opcional). */
const SHORT_CODE = /^([A-Z0-9]{5})-?([A-Z0-9]{5})$/i;

/**
 * Acepta lo que puede leer el escaner y devuelve la ruta interna:
 * - Codigo corto de kit (p. ej. DT5ZK-FL8GE)  -> /k/DT5ZKFL8GE
 * - URL de NidoGuard con /t/<token> o /k/<codigo> -> misma ruta
 */
export function parseNidoUrl(text: string): string | null {
  const bare = text.trim().match(SHORT_CODE);
  if (bare) return `/k/${(bare[1] + bare[2]).toUpperCase()}`;
  try {
    const u = new URL(text);
    if (!APP_HOSTS.includes(u.hostname)) return null;
    if (u.protocol !== "https:" && u.hostname !== "localhost") return null;
    const m = u.pathname.match(/^\/(t|k)\/([A-Za-z0-9]{6,64})$/);
    return m ? `/${m[1]}/${m[2]}` : null;
  } catch { return null; }
}

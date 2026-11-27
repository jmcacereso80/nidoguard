// Version del servidor. Nunca se guarda en cache: la app la compara al abrirse para saber si hay una version nueva.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(
    { version: process.env.APP_VERSION ?? "sin versión" },
    { headers: { "Cache-Control": "no-store, no-cache, must-revalidate" } },
  );
}

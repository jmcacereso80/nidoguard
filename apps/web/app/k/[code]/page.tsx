"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { CreateHome } from "@/components/CreateHome";
import { useMe } from "@/components/useHome";
import { Kit, useApi } from "@/lib/api";

export default function ClaimKit({ params }: { params: Promise<{ code: string }> }) {
  const { code: raw } = use(params);
  const manual = raw === "activar";
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const api = useApi();
  const me = useMe();
  const [typed, setTyped] = useState("");
  const [kit, setKit] = useState<Kit | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace(`/sign-up?redirect_url=${encodeURIComponent(`/k/${raw}`)}`);
  }, [isLoaded, isSignedIn, raw, router]);

  async function claim(code: string) {
    setBusy(true); setErr(null);
    try { setKit(await api<Kit>("/kits/claim", { method: "POST", body: JSON.stringify({ code }) })); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => { if (!manual && me.data?.home && !kit && !busy && !err) claim(raw); /* eslint-disable-next-line */ }, [me.data?.home]);

  if (!isLoaded || me.isLoading) return <Shell title="Activa tu kit"><p>Cargando…</p></Shell>;
  if (!me.data?.home) return <Shell title="Activa tu kit"><p className="mb-3">Primero crea tu hogar y enseguida activamos tu kit.</p><CreateHome /></Shell>;
  if (kit) return (
    <Shell title="¡Kit activado!">
      <Card>
        <p className="text-lg font-extrabold text-ink">Tienes {kit.tags_total} etiquetas listas.</p>
        <p className="mt-1 text-muted">Escanea una, toma la foto de la placa del equipo y listo.</p>
        <button className="btn btn-copper mt-4 w-full" onClick={() => router.push("/escanear")}>Empezar a registrar</button>
      </Card>
    </Shell>
  );
  return (
    <Shell title="Activa tu kit" back="/inicio">
      <Card>
        {manual ? (
          <form onSubmit={(e) => { e.preventDefault(); claim(typed); }} className="flex flex-col gap-3">
            <label htmlFor="c" className="font-extrabold text-ink">Escribe el código de tu hoja</label>
            <input id="c" className="field text-center text-xl tracking-widest" value={typed} autoCapitalize="characters"
                   onChange={(e) => setTyped(e.target.value)} placeholder="XXXXX-XXXXX" />
            <button className="btn" disabled={busy || typed.length < 6}>{busy ? "Activando…" : "Activar kit"}</button>
          </form>
        ) : <p>{busy ? "Activando tu kit…" : "Preparando…"}</p>}
        <ErrorNote text={err} />
      </Card>
    </Shell>
  );
}

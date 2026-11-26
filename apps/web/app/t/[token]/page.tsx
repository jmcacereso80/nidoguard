"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { useApi } from "@/lib/api";

type Resolved =
  | { state: "necesita_sesion" } | { state: "ajena" } | { state: "disponible"; tag_id: string }
  | { state: "vinculada"; asset: { id: string; name: string; status: string } };

export default function Tag({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const { isLoaded, isSignedIn } = useAuth();
  const api = useApi();
  const router = useRouter();
  const [r, setR] = useState<Resolved | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    api<Resolved>(`/tags/${encodeURIComponent(token)}`).then(setR).catch((e) => setErr(e.message));
  }, [isLoaded, isSignedIn, token, api]);

  useEffect(() => {
    if (r?.state === "disponible") router.replace(`/alta/${token}`);
    if (r?.state === "vinculada") router.replace(`/equipos/${r.asset.id}`);
  }, [r, token, router]);

  if (err) return <Shell title="Etiqueta"><Card><ErrorNote text={err} /></Card></Shell>;
  if (!r) return <Shell title="Etiqueta"><p>Revisando la etiqueta…</p></Shell>;
  if (r.state === "necesita_sesion") return (
    <Shell title="Etiqueta NidoGuard">
      <Card>
        <p className="font-bold text-navy">Inicia sesión para ver este equipo.</p>
        <Link className="btn mt-4 w-full" href={`/sign-in?redirect_url=${encodeURIComponent(`/t/${token}`)}`}>Iniciar sesión</Link>
      </Card>
    </Shell>
  );
  if (r.state === "ajena") return (
    <Shell title="Etiqueta NidoGuard">
      <Card><p className="text-ink/80">Esta etiqueta no está registrada en tu hogar. Si encontraste este equipo, contacta a su dueño.</p></Card>
    </Shell>
  );
  return <Shell title="Etiqueta"><p>Abriendo…</p></Shell>;
}

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth, UserButton } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { Shell, Card } from "@/components/Shell";
import { CreateHome } from "@/components/CreateHome";
import { useMe } from "@/components/useHome";
import { Asset, Kit, useApi } from "@/lib/api";

export default function Inicio() {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const api = useApi();
  const me = useMe();
  const home = me.data?.home;
  const kits = useQuery({ queryKey: ["kits"], queryFn: () => api<Kit[]>("/kits"), enabled: !!home });
  const pending = useQuery({ queryKey: ["pending"], queryFn: () => api<Asset[]>("/assets?status=por_confirmar"), enabled: !!home });
  useEffect(() => { if (isLoaded && !isSignedIn) router.replace("/sign-in"); }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || me.isLoading) return <Shell><p>Cargando…</p></Shell>;
  if (!home) return <Shell title="Bienvenido"><CreateHome /></Shell>;

  const used = kits.data?.reduce((n, k) => n + k.tags_used, 0) ?? 0;
  const total = kits.data?.reduce((n, k) => n + k.tags_total, 0) ?? 0;
  return (
    <Shell title={home.name}>
      <div className="absolute right-4 top-6"><UserButton /></div>
      <div className="flex flex-col gap-4">
        <Card>
          <p className="text-sm font-semibold text-sky">Tus etiquetas</p>
          <p className="text-3xl font-extrabold text-navy">{total ? `${used} de ${total}` : "Sin kit todavía"}</p>
          <div className="mt-4 flex flex-col gap-3">
            {total > 0 && <Link href="/escanear" className="btn btn-copper">Escanear una etiqueta</Link>}
            <Link href="/k/activar" className="btn btn-ghost">Activar un kit</Link>
          </div>
        </Card>
        {!!pending.data?.length && (
          <Card>
            <p className="font-bold text-navy">{pending.data.length} equipo(s) por confirmar</p>
            <p className="text-sm text-ink/70">Revisa lo que leímos de la placa y confírmalo con un toque.</p>
            <Link href="/por-confirmar" className="btn mt-3">Revisar</Link>
          </Card>
        )}
      </div>
    </Shell>
  );
}

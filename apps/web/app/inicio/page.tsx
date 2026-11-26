"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth, UserButton } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "@/components/Shell";
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
  const free = total - used;  // etiquetas todavia sin equipo
  return (
    <Shell title="NidoGuard" nav="inicio">
      <div className="absolute right-4 top-6"><UserButton /></div>
      <div className="gs flex h-[54px] items-center gap-2.5 rounded-[27px] px-5 text-xl font-extrabold text-navy">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /></svg>
        {home.name}
      </div>
      <div className="mt-5">
        <h2 className="text-[32px] font-extrabold leading-[1.1] tracking-[-0.8px]">Cuida lo tuyo.</h2>
        <p className="mt-1.5 text-sm text-muted">Tus equipos, tu inversión, tu tranquilidad.</p>
      </div>
      <div className="mt-[18px] flex gap-3">
        <div className="gd flex min-h-[144px] flex-[1.35] flex-col justify-between rounded-[30px] px-5 py-[18px]">
          <p className="text-sm font-semibold opacity-90">Mis etiquetas</p>
          <p className="flex items-baseline gap-2"><span className="text-5xl font-extrabold leading-none tracking-[-1.5px]">{total ? used : 0}</span><span className="text-sm font-semibold opacity-90">{total ? `de ${total} usadas` : "sin kit todavía"}</span></p>
        </div>
        <div className="g flex flex-1 flex-col justify-between rounded-[30px] p-[18px]">
          <p className="text-sm font-semibold text-muted">Por confirmar</p>
          <p className="text-5xl font-extrabold leading-none tracking-[-1.5px] text-navy">{pending.data?.length ?? 0}</p>
          <p className="text-sm font-semibold text-muted">equipos</p>
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-3">
        {total === 0 && (
          <Link href="/k/activar" className="btn btn-copper w-full">Activar tu kit</Link>
        )}
        {free > 0 && (
          <Link href="/escanear" className="btn btn-copper w-full">Agregar un equipo</Link>
        )}
        {total > 0 && <p className="text-center text-xs text-muted">Escanea la etiqueta que va pegada al equipo, no la hoja del kit.</p>}
        {total > 0 && <Link href="/k/activar" className="btn btn-ghost w-full">Activar otro kit</Link>}
      </div>
      {!!pending.data?.length && (
        <>
          <h2 className="mt-6 text-[19px] font-extrabold">Necesitan tu atención</h2>
          <Link href="/por-confirmar" className="g mt-2.5 flex h-[62px] items-center gap-3 rounded-[22px] px-3.5">
            <span className="icon-tile"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10" /></svg></span>
            <span className="min-w-0 flex-1"><span className="block text-[15px] font-bold leading-tight">{pending.data.length} equipo(s) por confirmar</span><span className="block text-[12.5px] text-muted">Ya leímos sus datos</span></span>
            <span className="chip">Revisar</span>
          </Link>
        </>
      )}
    </Shell>
  );
}

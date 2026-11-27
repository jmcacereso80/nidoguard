"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth, UserButton } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "@/components/Shell";
import { AppVersion } from "@/components/AppVersion";
import { CreateHome } from "@/components/CreateHome";
import { Icon } from "@/components/Icon";
import { Logo } from "@/components/Logo";
import { useMe } from "@/components/useHome";
import { Asset, Kit, Space, useApi } from "@/lib/api";

export default function Inicio() {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const api = useApi();
  const me = useMe();
  const home = me.data?.home;
  const kits = useQuery({ queryKey: ["kits"], queryFn: () => api<Kit[]>("/kits"), enabled: !!home });
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => api<Asset[]>("/assets"), enabled: !!home });
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces"), enabled: !!home });
  useEffect(() => { if (isLoaded && !isSignedIn) router.replace("/sign-in"); }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || me.isLoading) return <Shell><p>Cargando…</p></Shell>;
  if (!home) return <Shell title="Bienvenido"><CreateHome /></Shell>;

  const list = assets.data ?? [];
  const used = kits.data?.reduce((n, k) => n + k.tags_used, 0) ?? 0;
  const total = kits.data?.reduce((n, k) => n + k.tags_total, 0) ?? 0;
  const free = total - used;  // etiquetas todavia sin equipo
  const hasKit = total > 0;
  // Separa lo que todavia se esta leyendo de lo que ya necesita tu revision.
  const reading = list.filter((a) => a.status === "registrado" || a.status === "leido").length;
  const attention = list.filter((a) => ["por_confirmar", "necesita_foto", "faltan_datos"].includes(a.status)).length;
  const top = (
    <div className="flex h-11 items-center justify-between">
      <div className="flex items-center gap-2"><Logo size={30} /><span className="text-lg font-extrabold tracking-tight text-navy">NidoGuard</span></div>
      <div className="g grid h-11 w-11 place-items-center rounded-full"><UserButton /></div>
    </div>
  );
  const pill = (
    <Link href="/hogar" aria-label={`${home.name}: ver mis datos y direcciones`} className="gs mt-4 flex h-[54px] items-center gap-2.5 rounded-[27px] px-5 text-xl font-extrabold text-navy">
      <Icon name="home" />{home.name}<span className="ml-auto"><Icon name="chevron" size={20} stroke={2.4} /></span>
    </Link>
  );

  if (assets.isSuccess && list.length === 0) {
    return (
      <main className="mx-auto w-full max-w-md px-4 pb-32 pt-6">
        {top}{pill}
        <div className="g mt-4 flex flex-col items-center rounded-[34px] px-6 py-8 text-center">
          <span className="grid h-28 w-28 place-items-center rounded-full bg-white/70"><Logo size={64} /></span>
          <h2 className="mt-4 text-[26px] font-extrabold leading-tight tracking-tight">Tu hogar comienza aquí.</h2>
          <p className="mt-2 text-sm text-muted">Registra tu primer equipo y empieza a cuidar lo que tanto te ha costado construir.</p>
          {hasKit && free > 0
            ? <Link href="/escanear" className="btn mt-5 w-full"><Icon name="scan" size={20} />Registrar mi primer equipo</Link>
            : <Link href="/k/activar" className="btn mt-5 w-full"><Icon name="tag" size={20} />Activar mi kit</Link>}
        </div>
        <ol className="g mt-3 flex flex-col gap-3 rounded-[26px] p-4">
          {["Pega la etiqueta en tu equipo", "Escanéala y toma una foto de la placa", "Revisa y confirma los datos"].map((t, i) => (
            <li key={t} className="flex items-center gap-3"><span className="grid h-7 w-7 flex-none place-items-center rounded-full bg-navy text-sm font-extrabold text-white">{i + 1}</span><span className="text-[15px] font-bold">{t}</span></li>
          ))}
        </ol>
        <BottomNavSlot />
      </main>
    );
  }

  const counts = new Map<string, number>();
  list.forEach((a) => a.space_id && counts.set(a.space_id, (counts.get(a.space_id) ?? 0) + 1));
  return (
    <main className="mx-auto w-full max-w-md px-4 pb-32 pt-6">
      {top}{pill}
      <AppVersion className="mt-2 mb-3 text-muted/80" />
      <div className="mt-5">
        <h2 className="text-[32px] font-extrabold leading-[1.1] tracking-[-0.8px]">Cuida lo tuyo.</h2>
        <p className="mt-1.5 text-sm text-muted">Tus equipos, tu inversión, tu tranquilidad.</p>
      </div>
      <div className="mt-[18px] flex gap-3">
        <div className="gd flex min-h-[144px] flex-[1.35] flex-col justify-between rounded-[30px] px-5 py-[18px]">
          <p className="text-sm font-semibold opacity-90">Mis equipos</p>
          <p className="flex items-baseline gap-2"><span className="text-5xl font-extrabold leading-none tracking-[-1.5px]">{list.length}</span><span className="text-sm font-semibold opacity-90">registrados</span></p>
          <span className="inline-flex items-center gap-1.5 self-start rounded-xl bg-white/20 px-2.5 py-1 text-xs font-bold"><Icon name="clock" size={13} stroke={2.4} />Valor estimado: muy pronto</span>
        </div>
        <Link href="/por-confirmar" className="g flex flex-1 flex-col justify-between rounded-[30px] p-[18px]">
          <p className="text-sm font-semibold text-muted">Por revisar</p>
          <p className="text-5xl font-extrabold leading-none tracking-[-1.5px] text-navy">{attention}</p>
          <p className="text-sm font-semibold text-muted">{reading ? `${reading} leyendo` : "equipos"}</p>
        </Link>
      </div>
      {reading > 0 && (
        <p className="g mt-3 rounded-[22px] px-4 py-3 text-sm text-navy">
          <b>{reading === 1 ? "Un equipo" : `${reading} equipos`}</b> {reading === 1 ? "se está leyendo" : "se están leyendo"}. Cuando termine, aparecerá en <b>Por revisar</b>. Recarga la pantalla para ver el avance.
        </p>
      )}
      <div className="mt-3 flex flex-col gap-3">
        {free > 0 && <Link href="/escanear" className="btn btn-copper w-full"><Icon name="scan" size={20} />Agregar un equipo</Link>}
        {free > 0 && <p className="text-center text-xs text-muted">Escanea la etiqueta que va pegada al equipo, no la hoja del kit.</p>}
        <Link href="/k/activar" className="btn btn-ghost w-full">{hasKit ? "Activar otro kit" : "Activar tu kit"}</Link>
      </div>
      <Link href="/servicios" className="g mt-3 flex items-center gap-3.5 rounded-[28px] py-3.5 pl-4 pr-3.5">
        <span className="grid h-12 w-12 flex-none place-items-center rounded-full text-ink" style={{ background: "linear-gradient(145deg,#E9C7A3,#C18B58)" }}><Icon name="sparkle" size={24} /></span>
        <span className="flex-1"><span className="block text-base font-extrabold">¿En qué te puedo ayudar?</span><span className="block text-[13px] text-muted">Estoy aquí para cuidar tus equipos.</span></span>
        <span className="grid h-9 w-9 place-items-center rounded-full bg-[rgba(24,59,86,.08)] text-navy"><Icon name="chevron" size={18} stroke={2.4} /></span>
      </Link>
      {attention > 0 && (
        <>
          <div className="mt-6 flex items-baseline justify-between"><h2 className="text-[19px] font-extrabold">Necesitan tu atención</h2></div>
          <Link href="/por-confirmar" className="g mt-2.5 flex h-[62px] items-center gap-3 rounded-[22px] px-3.5">
            <span className="icon-tile"><Icon name="check" size={19} /></span>
            <span className="min-w-0 flex-1"><span className="block text-[15px] font-bold leading-tight">{attention} {attention === 1 ? "equipo por revisar" : "equipos por revisar"}</span><span className="block text-[12.5px] text-muted">Revisa lo que leímos de la placa</span></span>
            <span className="chip"><Icon name="check" size={13} stroke={2.4} />Revisar</span>
          </Link>
        </>
      )}
      {!!spaces.data?.length && (
        <>
          <h2 className="mt-6 text-[19px] font-extrabold">Mis espacios</h2>
          <div className="-mx-4 mt-2.5 flex gap-2.5 overflow-x-auto px-4 pb-2">
            {spaces.data.map((s, i) => (
              <Link key={s.id} href={`/equipos?espacio=${s.id}`} className="g flex h-[104px] w-[132px] flex-none flex-col justify-between rounded-[26px] p-3.5 text-navy"
                    style={{ background: i % 2 ? "linear-gradient(145deg,rgba(241,226,211,.85),rgba(227,195,163,.7))" : "linear-gradient(145deg,rgba(228,237,244,.8),rgba(185,207,224,.7))" }}>
                <Icon name={s.icon ?? "home"} size={26} stroke={1.8} />
                <span><span className="block text-[15px] font-extrabold text-ink">{s.name}</span><span className="block text-[12.5px] text-muted">{counts.get(s.id) ?? 0} equipos</span></span>
              </Link>
            ))}
          </div>
        </>
      )}
      <BottomNavSlot />
    </main>
  );
}

import { BottomNav } from "@/components/BottomNav";
function BottomNavSlot() { return <BottomNav active="inicio" />; }

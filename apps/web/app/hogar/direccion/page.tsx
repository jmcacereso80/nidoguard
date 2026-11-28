"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { useMe } from "@/components/useHome";
import { useApi } from "@/lib/api";

const RADIOS = [10, 15, 25] as const;
const NOMBRES = ["Casa", "Oficina", "Casa de mamá"] as const;
const VACIO = { street: "", colony: "", postal_code: "", city: "", state: "", search_radius_km: 15 };

function Form() {
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const sp = useSearchParams(); const volver = sp.get("volver"); const esNueva = sp.get("nueva") === "1";
  const me = useMe();
  const props = me.data?.home?.properties ?? [];
  const prop = esNueva ? undefined : props.find((p) => p.id === sp.get("p")) ?? props[0];
  const [f, setF] = useState(VACIO);
  const [nombre, setNombre] = useState<string>("");
  const [otro, setOtro] = useState(false);
  const [principal, setPrincipal] = useState(false);
  const [creada, setCreada] = useState<string | null>(null);
  const [quitar, setQuitar] = useState(false);
  const [destino, setDestino] = useState("");
  useEffect(() => {
    if (esNueva) { setNombre(props.length === 0 ? "Casa" : ""); setOtro(props.length > 0); setPrincipal(false); return; }
    if (!prop) return;
    const a = prop.address;
    setF(a?.street ? { street: a.street ?? "", colony: a.colony ?? "", postal_code: a.postal_code ?? "", city: a.city ?? "", state: a.state ?? "", search_radius_km: a.search_radius_km } : VACIO);
    setNombre(prop.name); setOtro(!(NOMBRES as readonly string[]).includes(prop.name)); setPrincipal(!!a?.is_primary);
  }, [prop?.id, prop?.name, prop?.address?.street, prop?.address?.search_radius_km, esNueva, props.length]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  const guardar = useMutation({
    mutationFn: async () => {
      let id = creada ?? prop?.id;
      if (!id) { id = (await api<{ id: string }>("/properties", { method: "POST", body: JSON.stringify({ name: nombre.trim() }) })).id; setCreada(id); }
      return api(`/properties/${id}/address`, { method: "PUT", body: JSON.stringify({ ...f, colony: f.colony || null, postal_code: f.postal_code || null, state: f.state || null, name: nombre.trim(), is_primary: principal || undefined }) });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["me"] }); router.push(volver ?? "/hogar"); },
  });
  const eliminar = useMutation({
    mutationFn: () => api(`/properties/${prop!.id}${destino ? `?move_to=${destino}` : ""}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["me"] }); router.push("/hogar"); },
  });
  const otras = props.filter((p) => p.id !== prop?.id);
  const listo = nombre.trim().length >= 1 && f.street.trim().length >= 3 && f.city.trim().length >= 2 && (!f.postal_code || /^\d{5}$/.test(f.postal_code));
  const campo = (id: keyof typeof f, label: string, extra: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div className="flex-1"><label htmlFor={id} className="mx-2 text-[13px] font-extrabold">{label}</label><input id={id} className="field mt-1" value={f[id] as string} onChange={set(id)} {...extra} /></div>
  );
  const chipCls = (on: boolean) => `flex min-h-11 items-center rounded-full px-[18px] text-[14px] ${on ? "gd font-extrabold" : "g font-bold text-navy"}`;
  return (
    <Shell title={esNueva ? "Nueva dirección" : prop?.name ?? "Dirección"} subtitle="Dirección" back={volver ?? "/hogar"}>
      <h2 className="mx-2 mb-2 mt-1 text-[17px] font-extrabold">¿Cómo la llamas?</h2>
      <div role="radiogroup" aria-label="Nombre de la dirección" className="flex flex-wrap gap-2">
        {NOMBRES.map((n) => <button key={n} type="button" role="radio" aria-checked={!otro && nombre === n} className={chipCls(!otro && nombre === n)} onClick={() => { setNombre(n); setOtro(false); }}>{n}</button>)}
        <button type="button" role="radio" aria-checked={otro} className={chipCls(otro)} onClick={() => { setOtro(true); if ((NOMBRES as readonly string[]).includes(nombre)) setNombre(""); }}>Otra</button>
      </div>
      {otro && <div className="mt-2"><label htmlFor="nom" className="sr-only">Nombre de la dirección</label><input id="nom" className="field" placeholder="Ej. Casa de la playa" maxLength={60} value={nombre} onChange={(e) => setNombre(e.target.value)} /></div>}

      <div className="mt-4 flex flex-col gap-3">
        {campo("street", "Calle y número", { autoComplete: "street-address", placeholder: "Gabriel Mancera 123" })}
        <div className="flex gap-2.5">{campo("colony", "Colonia", { placeholder: "Del Valle Centro" })}{campo("postal_code", "Código postal", { inputMode: "numeric", maxLength: 5, placeholder: "03100" })}</div>
        <div className="flex gap-2.5">{campo("city", "Ciudad", { placeholder: "Ciudad de México" })}{campo("state", "Estado", { placeholder: "CDMX" })}</div>
      </div>
      <div className="g mt-3 flex items-start gap-3 rounded-[22px] p-3"><span className="mt-0.5 text-navy"><Icon name="lock" size={18} /></span>
        <p className="text-[13px] leading-snug">Al buscar la ubicamos en el mapa. <b>Al técnico solo le decimos la colonia.</b> Tu dirección exacta la ve solo el que tú elijas.</p></div>

      <h2 className="mx-2 mb-2 mt-5 text-[14px] font-extrabold">Qué tan lejos buscamos técnicos</h2>
      <div role="radiogroup" aria-label="Distancia" className="g flex rounded-[22px] p-1">
        {RADIOS.map((r) => <button key={r} type="button" role="radio" aria-checked={f.search_radius_km === r} onClick={() => setF({ ...f, search_radius_km: r })}
          className={`h-10 flex-1 rounded-full text-[14px] ${f.search_radius_km === r ? "gd font-extrabold" : "font-bold text-navy"}`}>{r} km</button>)}
      </div>

      {(props.length > 0 || creada) && !(prop?.address?.is_primary) && (
        <label className="g mt-4 flex min-h-14 items-center gap-3 rounded-[24px] px-4 py-3">
          <span className="flex-1"><span className="block text-[14.5px] font-extrabold">Es mi dirección principal</span><span className="block text-[12.5px] text-muted">La que usamos si no eliges otra</span></span>
          <input type="checkbox" role="switch" checked={principal} onChange={(e) => setPrincipal(e.target.checked)} className="h-7 w-7 accent-[#183B56]" />
        </label>
      )}
      <ErrorNote text={guardar.isError ? (guardar.error as Error).message : null} />
      <button type="button" className="btn mt-5 w-full" disabled={!listo || guardar.isPending} onClick={() => guardar.mutate()}>
        <Icon name="check" size={20} stroke={2.2} />{guardar.isPending ? "Buscando tu dirección…" : "Guardar dirección"}</button>

      {prop && !esNueva && props.length > 1 && !quitar && (
        <button type="button" onClick={() => setQuitar(true)} className="mt-1 flex min-h-11 w-full items-center justify-center text-[14px] font-extrabold text-[#8F2F2F]">Eliminar esta dirección</button>
      )}
      {quitar && prop && (
        <div className="g mt-3 rounded-[24px] p-4">
          <p className="text-[14px] font-extrabold">¿Eliminar “{prop.name}”?</p>
          {(prop.assets_count ?? 0) > 0 ? (<>
            <p className="mt-1 text-[13px] leading-snug text-muted">Tus {prop.assets_count} equipos no se borran. Elige a qué dirección pasarlos.</p>
            <label htmlFor="dest" className="sr-only">Pasar equipos a</label>
            <select id="dest" className="field mt-2" value={destino} onChange={(e) => setDestino(e.target.value)}>
              <option value="">Elige una dirección</option>{otras.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select></>)
            : <p className="mt-1 text-[13px] text-muted">No tiene equipos.</p>}
          <ErrorNote text={eliminar.isError ? (eliminar.error as Error).message : null} />
          <div className="mt-3 flex gap-2"><button type="button" className="btn btn-ghost flex-1" onClick={() => setQuitar(false)}>Cancelar</button>
            <button type="button" className="btn flex-1" disabled={((prop.assets_count ?? 0) > 0 && !destino) || eliminar.isPending} onClick={() => eliminar.mutate()}>Eliminar</button></div>
        </div>
      )}
    </Shell>
  );
}
export default function Direccion() { return <Suspense><Form /></Suspense>; }

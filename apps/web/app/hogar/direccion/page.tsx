"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { Note } from "@/components/servicios/ui";
import { useMe } from "@/components/useHome";
import { useApi } from "@/lib/api";

const RADIOS = [10, 15, 25] as const;
const VACIO = { street: "", colony: "", postal_code: "", city: "", state: "", search_radius_km: 15 };

function Form() {
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const sp = useSearchParams(); const volver = sp.get("volver");
  const me = useMe();
  const props = me.data?.home?.properties ?? [];
  const [sel, setSel] = useState<string | null>(sp.get("p") || null);
  const prop = props.find((p) => p.id === sel) ?? props[0];
  const [f, setF] = useState(VACIO);
  const [nuevo, setNuevo] = useState<string | null>(null);
  const [tel, setTel] = useState(""); const [telOk, setTelOk] = useState(false);
  useEffect(() => { const a = prop?.address; setF(a?.street ? { street: a.street ?? "", colony: a.colony ?? "", postal_code: a.postal_code ?? "", city: a.city ?? "", state: a.state ?? "", search_radius_km: a.search_radius_km } : VACIO); }, [prop?.id, prop?.address?.street, prop?.address?.search_radius_km]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (me.data?.user.phone) setTel(me.data.user.phone.replace(/^\+52/, "")); }, [me.data?.user.phone]);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const guardar = useMutation({
    mutationFn: () => api(`/properties/${prop!.id}/address`, { method: "PUT", body: JSON.stringify({ ...f, colony: f.colony || null, postal_code: f.postal_code || null, state: f.state || null }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["me"] }); router.push(volver ?? "/servicios"); },
  });
  const agregar = useMutation({
    mutationFn: (name: string) => api<{ id: string }>("/properties", { method: "POST", body: JSON.stringify({ name }) }),
    onSuccess: (p) => { qc.invalidateQueries({ queryKey: ["me"] }); setSel(p.id); setNuevo(null); },
  });
  const telefono = useMutation({
    mutationFn: () => api("/me/phone", { method: "PUT", body: JSON.stringify({ phone: tel }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["me"] }); setTelOk(true); },
  });
  const listo = f.street.trim().length >= 3 && f.city.trim().length >= 2 && (!f.postal_code || /^\d{5}$/.test(f.postal_code));
  const campo = (id: keyof typeof f, label: string, extra: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div><label htmlFor={id} className="mx-1.5 text-[12.5px] font-bold text-muted">{label}</label><input id={id} className="field mt-1" value={f[id] as string} onChange={set(id)} {...extra} /></div>
  );
  return (
    <Shell title="Mi hogar" subtitle="Direcciones y teléfono" back={volver ?? "/inicio"} nav="inicio">
      <h2 className="mx-1.5 mb-2 mt-1 text-[14px] font-extrabold">Tus direcciones</h2>
      <div role="tablist" aria-label="Direcciones" className="flex flex-wrap gap-2">
        {props.map((p) => (
          <button key={p.id} type="button" role="tab" aria-selected={prop?.id === p.id} onClick={() => setSel(p.id)}
            className={`min-h-11 rounded-full px-4 text-[13.5px] font-bold ${prop?.id === p.id ? "gd font-extrabold" : "g text-navy"}`}>{p.name}</button>
        ))}
        {props.length < 5 && nuevo === null && <button type="button" onClick={() => setNuevo("")} className="g flex min-h-11 items-center gap-1.5 rounded-full px-4 text-[13.5px] font-bold text-navy"><Icon name="plus" size={16} stroke={2.4} />Otra dirección</button>}
      </div>
      {nuevo !== null && (
        <div className="g mt-2 flex items-center gap-2 rounded-[22px] p-2.5">
          <label className="sr-only" htmlFor="nueva">Nombre de la dirección</label>
          <input id="nueva" className="field !min-h-11 flex-1" placeholder="Ej. Casa de mamá" value={nuevo} onChange={(e) => setNuevo(e.target.value)} />
          <button type="button" className="btn !min-h-11 !px-4" disabled={nuevo.trim().length < 1 || agregar.isPending} onClick={() => agregar.mutate(nuevo.trim())}>Crear</button>
        </div>
      )}
      <ErrorNote text={agregar.isError ? (agregar.error as Error).message : null} />
      <div className="g mt-3 flex items-start gap-3 rounded-[26px] p-3.5"><span className="icon-tile"><Icon name="pin" size={20} /></span>
        <p className="flex-1 text-[13.5px] leading-snug">Usamos tu zona para encontrar técnicos cerca. <b>Al técnico solo le decimos la colonia.</b> Tu dirección exacta la ve solo el que tú elijas.</p></div>
      <div className="mt-4 flex flex-col gap-3">
        {campo("street", "Calle y número", { autoComplete: "street-address", placeholder: "Gabriel Mancera 123" })}
        {campo("colony", "Colonia", { placeholder: "Del Valle Centro" })}
        {campo("postal_code", "Código postal", { inputMode: "numeric", maxLength: 5, placeholder: "03100" })}
        {campo("city", "Ciudad", { placeholder: "Ciudad de México" })}
        {campo("state", "Estado", { placeholder: "CDMX" })}
      </div>
      <h2 className="mx-1.5 mb-2 mt-5 text-[14px] font-extrabold">Qué tan lejos buscamos</h2>
      <div role="radiogroup" aria-label="Distancia" className="g flex rounded-[22px] p-1">
        {RADIOS.map((r) => <button key={r} type="button" role="radio" aria-checked={f.search_radius_km === r} onClick={() => setF({ ...f, search_radius_km: r })}
          className={`h-10 flex-1 rounded-full text-[14px] font-bold ${f.search_radius_km === r ? "gd !rounded-full font-extrabold" : "text-navy"}`}>{r} km</button>)}
      </div>
      <ErrorNote text={guardar.isError ? (guardar.error as Error).message : null} />
      <button type="button" className="btn mt-5 w-full" disabled={!listo || !prop || guardar.isPending} onClick={() => guardar.mutate()}>{guardar.isPending ? "Buscando tu dirección…" : "Guardar dirección"}</button>

      <h2 className="mx-1.5 mb-2 mt-7 text-[14px] font-extrabold">Tu teléfono para agendar</h2>
      <div className="g rounded-[26px] p-4">
        <label htmlFor="tel" className="text-[12.5px] text-muted">A 10 dígitos</label>
        <div className="mt-1 flex items-center gap-2">
          <input id="tel" inputMode="tel" autoComplete="tel" placeholder="55 1234 5678" value={tel} onChange={(e) => { setTel(e.target.value); setTelOk(false); }} className="field !min-h-11 flex-1" />
          <button type="button" className="btn !min-h-11 !px-4" disabled={telefono.isPending} onClick={() => telefono.mutate()}>{telOk ? "Guardado" : "Guardar"}</button>
        </div>
        <p className="mt-2 text-[12.5px] leading-snug text-muted">No se lo damos a nadie por defecto. Al agendar, tú decides si el técnico lo recibe cuando confirme la visita. Para el fabricante sí es obligatorio.</p>
        <ErrorNote text={telefono.isError ? (telefono.error as Error).message : null} />
      </div>
      <Note icon="lock">Guardamos tu dirección solo para buscar técnicos cerca y para que el fabricante o el técnico que elijas llegue a tu casa.</Note>
    </Shell>
  );
}
export default function Direccion() { return <Suspense><Form /></Suspense>; }

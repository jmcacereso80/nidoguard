"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { Note } from "@/components/servicios/ui";
import { useMe } from "@/components/useHome";
import { useApi } from "@/lib/api";

const RADIOS = [10, 15, 25] as const;

function Form() {
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const volver = useSearchParams().get("volver");
  const me = useMe();
  const prop = me.data?.home?.properties[0];
  const [f, setF] = useState({ street: "", colony: "", postal_code: "", city: "", state: "", search_radius_km: 15 });
  useEffect(() => {
    const a = prop?.address;
    if (a) setF({ street: a.street ?? "", colony: a.colony ?? "", postal_code: a.postal_code ?? "", city: a.city ?? "", state: a.state ?? "", search_radius_km: a.search_radius_km });
  }, [prop?.address?.street, prop?.address?.search_radius_km]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const guardar = useMutation({
    mutationFn: () => api(`/properties/${prop!.id}/address`, { method: "PUT", body: JSON.stringify({ ...f, colony: f.colony || null, postal_code: f.postal_code || null, state: f.state || null }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["me"] }); router.push(volver ?? "/servicios"); },
  });
  const listo = f.street.trim().length >= 3 && f.city.trim().length >= 2 && (!f.postal_code || /^\d{5}$/.test(f.postal_code));
  const campo = (id: keyof typeof f, label: string, extra: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div><label htmlFor={id} className="mx-1.5 text-[12.5px] font-bold text-muted">{label}</label><input id={id} className="field mt-1" value={f[id] as string} onChange={set(id)} {...extra} /></div>
  );
  return (
    <Shell title="Mi hogar" subtitle="Dirección para buscar técnicos" back={volver ?? "/inicio"} nav="inicio">
      <div className="g flex items-start gap-3 rounded-[26px] p-3.5"><span className="icon-tile"><Icon name="pin" size={20} /></span>
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
      <Note icon="lock">Guardamos tu dirección solo para buscar técnicos cerca y para que el fabricante o el técnico que elijas llegue a tu casa.</Note>
    </Shell>
  );
}
export default function Direccion() { return <Suspense><Form /></Suspense>; }

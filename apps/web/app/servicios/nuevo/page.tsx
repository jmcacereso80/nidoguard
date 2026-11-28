"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon, equipmentIcon } from "@/components/Icon";
import { Callout, Label } from "@/components/servicios/ui";
import { Asset, Space, useApi } from "@/lib/api";
import { ServiceRequest, URGENCY_LABEL, Urgency } from "@/lib/servicios";

const OTRO = "otro";

function Form() {
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const pre = useSearchParams().get("equipo");
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => api<Asset[]>("/assets") });
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });
  const sp = new Map((spaces.data ?? []).map((s) => [s.id, s.name]));
  const [equipo, setEquipo] = useState<string>(pre ?? "");
  const [otro, setOtro] = useState("");
  const [texto, setTexto] = useState("");
  const [urg, setUrg] = useState<Urgency>("semana");
  const crear = useMutation({
    mutationFn: () => api<ServiceRequest>("/service-requests", { method: "POST", body: JSON.stringify({
      asset_id: equipo && equipo !== OTRO ? equipo : null, equipment_label: equipo === OTRO ? otro.trim() : null, symptom: texto.trim(), urgency: urg }) }),
    onSuccess: (r) => { qc.setQueryData(["svc", r.id], r); qc.invalidateQueries({ queryKey: ["svc-list"] }); router.push(`/servicios/${r.id}`); },
  });
  const listo = (equipo === OTRO ? otro.trim().length >= 2 : !!equipo) && texto.trim().length >= 5;
  return (
    <Shell title="Pedir un servicio" subtitle="Cuéntanos qué necesitas" back="/servicios" nav="servicios">
      <Callout tone="red" icon="alert">Si hueles a gas o ves chispas, no uses el equipo y llama al 911.</Callout>
      <Label>¿De qué equipo se trata?</Label>
      <div role="radiogroup" aria-label="Equipo" className="flex flex-col gap-2">
        {[...(assets.data ?? []), { id: OTRO, name: "Otro equipo", space_id: null } as Asset].map((a) => (
          <label key={a.id} className="g flex min-h-[60px] items-center gap-3 rounded-[22px] px-3.5 py-2.5">
            <input type="radio" name="equipo" checked={equipo === a.id} onChange={() => setEquipo(a.id)} className="h-[22px] w-[22px] flex-none accent-[#183B56]" />
            <span className="icon-tile"><Icon name={a.id === OTRO ? "plus" : equipmentIcon(a)} size={19} /></span>
            <span className="min-w-0 flex-1 text-[14.5px] font-extrabold leading-tight">{a.name}<span className="block text-[12.5px] font-semibold text-muted">{a.id === OTRO ? "No está en mi lista" : sp.get(a.space_id ?? "") ?? ""}</span></span>
          </label>
        ))}
      </div>
      {equipo === OTRO && <><label htmlFor="otro" className="sr-only">¿Qué equipo es?</label><input id="otro" className="field mt-2" placeholder="¿Qué equipo es? (p. ej. bomba de agua)" value={otro} onChange={(e) => setOtro(e.target.value)} /></>}
      <Label>¿Qué pasa?</Label>
      <label className="sr-only" htmlFor="que">Describe qué pasa</label>
      <textarea id="que" rows={4} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Ejemplo: gotea agua por dentro de la casa y ya no enfría bien."
        className="g block w-full resize-none rounded-[22px] px-4 py-3.5 text-[15px] font-semibold leading-snug text-ink" />
      <Label>¿Qué tan urgente es?</Label>
      <div role="radiogroup" aria-label="Urgencia" className="g flex rounded-[22px] p-1">
        {(Object.keys(URGENCY_LABEL) as Urgency[]).map((u) => (
          <button key={u} type="button" role="radio" aria-checked={urg === u} onClick={() => setUrg(u)} className={`h-[38px] flex-1 rounded-full text-[13px] font-bold ${urg === u ? "gd !rounded-full font-extrabold" : "text-navy"}`}>{URGENCY_LABEL[u]}</button>
        ))}
      </div>
      <ErrorNote text={crear.isError ? (crear.error as Error).message : null} />
      <button type="button" className="btn mt-5 w-full" disabled={!listo || crear.isPending} onClick={() => crear.mutate()}>{crear.isPending ? "Un momento…" : "Continuar"}</button>
    </Shell>
  );
}
export default function Nuevo() { return <Suspense><Form /></Suspense>; }

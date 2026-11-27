"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { useMe } from "@/components/useHome";
import { useApi } from "@/lib/api";
import { quitarLada } from "@/lib/micasa";

function Form() {
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const volver = useSearchParams().get("volver");
  const me = useMe();
  const [f, setF] = useState({ first_name: "", last_name: "", phone: "" });
  const [listo, setListo] = useState(false);
  useEffect(() => {
    if (me.data && !listo) { setF({ first_name: me.data.user.first_name ?? "", last_name: me.data.user.last_name ?? "", phone: quitarLada(me.data.user.phone) }); setListo(true); }
  }, [me.data, listo]);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const guardar = useMutation({
    mutationFn: () => api("/me/profile", { method: "PUT", body: JSON.stringify({ first_name: f.first_name, last_name: f.last_name || null, phone: f.phone || null }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["me"] }); router.push(volver ?? "/hogar"); },
  });
  return (
    <Shell title="Mis datos" subtitle="Para agendar y para que el servicio llegue bien" back={volver ?? "/hogar"}>
      <div className="mt-2 flex flex-col gap-3.5">
        <div><label htmlFor="n" className="mx-2 text-[13px] font-extrabold">Nombre o nombres</label><input id="n" className="field mt-1" autoComplete="given-name" value={f.first_name} onChange={set("first_name")} /></div>
        <div><label htmlFor="a" className="mx-2 text-[13px] font-extrabold">Apellidos</label><input id="a" className="field mt-1" autoComplete="family-name" value={f.last_name} onChange={set("last_name")} /></div>
        <div><label htmlFor="t" className="mx-2 text-[13px] font-extrabold">Teléfono celular</label>
          <div className="field mt-1 flex items-center gap-2 !px-2.5"><span className="rounded-full bg-[rgba(24,59,86,.08)] px-3 py-1.5 text-[14px] font-extrabold">+52</span>
            <input id="t" inputMode="tel" autoComplete="tel" placeholder="55 1234 5678" value={f.phone} onChange={set("phone")} className="min-w-0 flex-1 bg-transparent text-[16px] font-semibold outline-none" /></div>
          <p className="mx-2 mt-1.5 text-[12.5px] leading-snug text-muted">Solo para agendar. No se lo damos a ningún técnico a menos que tú lo permitas.</p></div>
        <div><label htmlFor="c" className="mx-2 text-[13px] font-extrabold">Correo</label>
          <div className="field mt-1 flex items-center !bg-white/40"><input id="c" readOnly value={me.data?.user.email ?? ""} className="min-w-0 flex-1 bg-transparent text-[16px] font-semibold text-muted outline-none" /><Icon name="lock" size={18} /></div>
          <p className="mx-2 mt-1.5 text-[12.5px] leading-snug text-muted">Es el de tu cuenta. Para cambiarlo, escríbenos.</p></div>
      </div>
      <div className="g mt-5 flex items-start gap-3 rounded-[26px] p-3.5"><span className="mt-0.5 text-navy"><Icon name="eye" size={20} /></span>
        <p className="text-[13.5px] leading-snug">Así te ve un técnico: <b>“{f.first_name.trim().split(" ")[0] || "tu nombre"}”</b>. Tus apellidos solo los usa el fabricante cuando agenda una cita de garantía. <a href="/hogar/privacidad" className="font-extrabold underline">Ver quién ve qué</a></p></div>
      <ErrorNote text={guardar.isError ? (guardar.error as Error).message : null} />
      <button type="button" className="btn mt-5 w-full" disabled={!f.first_name.trim() || guardar.isPending} onClick={() => guardar.mutate()}><Icon name="check" size={20} stroke={2.2} />{guardar.isPending ? "Guardando…" : "Guardar mis datos"}</button>
      <button type="button" onClick={() => router.push(volver ?? "/hogar")} className="mt-1 flex min-h-11 w-full items-center justify-center text-[14px] font-extrabold text-navy">Ahora no</button>
    </Shell>
  );
}
export default function Datos() { return <Suspense><Form /></Suspense>; }

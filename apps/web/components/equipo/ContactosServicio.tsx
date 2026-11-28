"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ErrorNote } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { ServiceContacts, useApi } from "@/lib/api";

const sinLada = (p: string | null | undefined) => (p ?? "").replace(/^\+52/, "");

/** Teléfono y nombre del fabricante y de la tienda donde se compró. Ej. Liverpool el primer año y después el fabricante. */
export function ContactosServicio({ id, contacts }: { id: string; contacts?: ServiceContacts }) {
  const api = useApi(); const qc = useQueryClient();
  const [f, setF] = useState({
    maker_name: contacts?.maker?.name ?? "", maker_phone: sinLada(contacts?.maker?.phone),
    store_name: contacts?.store?.name ?? "", store_phone: sinLada(contacts?.store?.phone), store_until: contacts?.store?.until ?? "",
  });
  const [msg, setMsg] = useState<string | null>(null); const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => { setF({ ...f, [k]: e.target.value }); setMsg(null); };
  async function guardar() {
    setBusy(true); setErr(null); setMsg(null);
    try {
      await api(`/assets/${id}/service-contacts`, { method: "PUT", body: JSON.stringify({
        maker_name: f.maker_name || null, maker_phone: f.maker_phone || null, store_name: f.store_name || null, store_phone: f.store_phone || null, store_until: f.store_until || null }) });
      await qc.invalidateQueries({ queryKey: ["asset", id] });
      setMsg("Guardado. Lo usamos cuando pidas ayuda con este equipo.");
    } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="g mt-4 rounded-[26px] p-4">
      <p className="flex items-center gap-2 text-[15px] font-extrabold"><Icon name="phone" size={19} stroke={2.2} />Servicio y garantía</p>
      <p className="mt-1 text-[12.5px] leading-snug text-muted">Guarda a quién llamar. Si lo compraste en una tienda, a veces la garantía del primer año es con ella y después con el fabricante.</p>
      <p className="mt-3 text-[13px] font-extrabold">Fabricante</p>
      <div className="mt-1.5 grid grid-cols-2 gap-2">
        <input aria-label="Nombre del fabricante" placeholder="Ej. Samsung" value={f.maker_name} onChange={set("maker_name")} maxLength={80} className="field" />
        <input aria-label="Teléfono del fabricante" inputMode="tel" placeholder="Teléfono" value={f.maker_phone} onChange={set("maker_phone")} maxLength={30} className="field" />
      </div>
      <p className="mt-3 text-[13px] font-extrabold">Tienda donde lo compraste</p>
      <div className="mt-1.5 grid grid-cols-2 gap-2">
        <input aria-label="Nombre de la tienda" placeholder="Ej. Liverpool" value={f.store_name} onChange={set("store_name")} maxLength={80} className="field" />
        <input aria-label="Teléfono de la tienda" inputMode="tel" placeholder="Teléfono" value={f.store_phone} onChange={set("store_phone")} maxLength={30} className="field" />
      </div>
      <label htmlFor="store-until" className="mt-3 block text-[13px] font-bold">La tienda cubre la garantía hasta (opcional)</label>
      <input id="store-until" type="date" value={f.store_until} onChange={set("store_until")} className="field mt-1.5 w-full" />
      <p className="mt-1.5 text-[12px] leading-snug text-muted">Mientras la tienda cubra la garantía, te decimos que agendes con ella. Después, con el fabricante.</p>
      <button type="button" className="btn mt-3 w-full" disabled={busy} onClick={guardar}><Icon name="check" size={19} stroke={2.4} />Guardar</button>
      {msg && <p role="status" className="mt-2 text-center text-[13px] font-bold text-[#235A3B]">{msg}</p>}
      <ErrorNote text={err} />
      <p className="mt-2 text-[12px] leading-snug text-muted">Estos números son tuyos: te los mostramos para que llames tú. Nuestro asistente no llama a números que escribes aquí.</p>
    </div>
  );
}

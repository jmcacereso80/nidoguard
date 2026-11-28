"use client";
import { useState } from "react";
import { Icon } from "@/components/Icon";
import { API_URL, useApi } from "@/lib/api";
import { CalEvent, googleCalLink, outlookCalLink } from "@/lib/servicios";

/** Agregar la visita o la cita al calendario de Apple, Google u Outlook, con toda la información. */
export function AgregarCalendario({ evento }: { evento: CalEvent; archivo?: string }) {
  const api = useApi();
  const [busy, setBusy] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  /** El iPhone no abre enlaces de datos: se pide un enlace .ics real y se abre en la misma pestaña (sale "Agregar a Calendario"). */
  async function apple() {
    setBusy(true); setFallo(null);
    try {
      const { path } = await api<{ path: string }>("/calendar/link", { method: "POST", body: JSON.stringify({ title: evento.title, start: evento.start, end: evento.end, location: evento.location, details: evento.details }) });
      window.location.href = `${API_URL}${path}`;
    } catch { setFallo("No pudimos preparar el archivo. Inténtalo de nuevo o usa Google u Outlook."); }
    finally { setBusy(false); }
  }
  const cls = "btn btn-ghost !min-h-12 !px-2 text-[14px]";
  return (
    <div className="g rounded-[26px] p-4">
      <p className="flex items-center gap-2 text-[15px] font-extrabold"><Icon name="calendar" size={19} stroke={2.2} />Agregar a tu calendario</p>
      <p className="mt-1 text-[12.5px] leading-snug text-muted">Se guarda con la fecha, el técnico, lo acordado y el precio. Te avisa una hora antes.</p>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <button type="button" className={cls} onClick={apple} disabled={busy}>{busy ? "Preparando…" : "Apple"}</button>
        <a className={cls} target="_blank" rel="noopener noreferrer" href={googleCalLink(evento)}>Google</a>
        <a className={cls} target="_blank" rel="noopener noreferrer" href={outlookCalLink(evento)}>Outlook</a>
      </div>
      {fallo && <p role="alert" className="mt-2 text-[12.5px] font-bold text-red-700">{fallo}</p>}
      <p className="mt-2 text-[12px] leading-snug text-muted">
        <b>Apple</b> abre tu Calendario para que toques "Agregar" (también sirve para Outlook de escritorio). ¿Outlook del trabajo? <a className="font-extrabold underline" target="_blank" rel="noopener noreferrer" href={outlookCalLink(evento, true)}>Microsoft 365</a>.
      </p>
    </div>
  );
}

"use client";
import { Icon } from "@/components/Icon";
import { CalEvent, googleCalLink, icsFor, outlookCalLink } from "@/lib/servicios";

/** Agregar la visita o la cita al calendario de Apple, Google u Outlook, con toda la información. */
export function AgregarCalendario({ evento, archivo }: { evento: CalEvent; archivo: string }) {
  const cls = "btn btn-ghost !min-h-12 !px-2 text-[14px]";
  return (
    <div className="g rounded-[26px] p-4">
      <p className="flex items-center gap-2 text-[15px] font-extrabold"><Icon name="calendar" size={19} stroke={2.2} />Agregar a tu calendario</p>
      <p className="mt-1 text-[12.5px] leading-snug text-muted">Se guarda con la fecha, el técnico, lo acordado y el precio. Te avisa una hora antes.</p>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <a className={cls} download={archivo} href={icsFor(evento)}>Apple</a>
        <a className={cls} target="_blank" rel="noopener noreferrer" href={googleCalLink(evento)}>Google</a>
        <a className={cls} target="_blank" rel="noopener noreferrer" href={outlookCalLink(evento)}>Outlook</a>
      </div>
      <p className="mt-2 text-[12px] leading-snug text-muted">
        <b>Apple</b> descarga un archivo que abre tu Calendario (también sirve para Outlook de escritorio). ¿Outlook del trabajo? <a className="font-extrabold underline" target="_blank" rel="noopener noreferrer" href={outlookCalLink(evento, true)}>Microsoft 365</a>.
      </p>
    </div>
  );
}

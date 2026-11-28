"use client";
import { useEffect, useRef, useState } from "react";

/** Textos del aviso según lo que se va a cancelar. */
const TEXTOS = {
  solicitud: { titulo: "¿Cancelar la solicitud?", cuerpo: "Dejamos de buscar y de llamar a técnicos. Si ya habías pedido una visita confirmada, le avisamos al técnico por teléfono.", si: "Sí, cancelar" },
  visita: { titulo: "¿Cancelar la visita?", cuerpo: "Si el técnico ya la había confirmado, le llamamos para avisarle. Después puedes elegir otra cotización.", si: "Sí, cancelar visita" },
  cambiar: { titulo: "¿Elegir otra cotización u horario?", cuerpo: "Se cancela esta visita y, si el técnico ya la había confirmado, le llamamos para avisarle. Vuelves a tus cotizaciones.", si: "Sí, cancelar esta visita" },
  cita: { titulo: "¿Cancelar la cita?", cuerpo: "Se cancela aquí en NidoGuard. Si ya quedaste con el fabricante, avísale tú directo.", si: "Sí, cancelar" },
} as const;
export type KindCancelar = keyof typeof TEXTOS;

/** Enlace que pide confirmación antes de cancelar: nada se cancela con un solo toque. */
export function ConfirmLink({ kind, onConfirm, children, danger = true }: { kind: KindCancelar; onConfirm: () => void; children: React.ReactNode; danger?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  const t = TEXTOS[kind];
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={`mx-auto flex min-h-11 items-center px-3 text-[14px] font-extrabold ${danger ? "text-[var(--ng-danger)]" : "text-navy"}`}>{children}</button>
      <dialog ref={ref} onClose={() => setOpen(false)} aria-labelledby={`cf-${kind}`}
        className="g m-auto w-[min(92vw,380px)] rounded-[28px] p-5 text-navy backdrop:bg-[rgba(24,59,86,.45)] backdrop:backdrop-blur-sm">
        <h2 id={`cf-${kind}`} className="text-[18px] font-extrabold leading-snug">{t.titulo}</h2>
        <p className="mt-2 text-[14px] leading-relaxed text-muted">{t.cuerpo}</p>
        <div className="mt-5 flex flex-col gap-2">
          <button type="button" className="btn" autoFocus onClick={() => setOpen(false)}>No, volver</button>
          <button type="button" className="btn btn-ghost !text-[var(--ng-danger)]" onClick={() => { setOpen(false); onConfirm(); }}>{t.si}</button>
        </div>
      </dialog>
    </>
  );
}

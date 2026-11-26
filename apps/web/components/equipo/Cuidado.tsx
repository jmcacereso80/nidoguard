"use client";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/Icon";
import { ErrorNote } from "@/components/Shell";
import { ApiError, useApi } from "@/lib/api";
import { CareData, CareTask, SOURCE_LABEL, dueLabel, everyShort, groupByFrequency, showWarrantyAlert, warrantyView } from "@/lib/care";
import { useDocumentos } from "./Documentos";

const hoyISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

/** `ready`: el equipo ya terminó de leerse. Los cuidados se preparan solos la primera vez que se abre la pestaña. */
export function Cuidado({ id, ready = true }: { id: string; ready?: boolean }) {
  const api = useApi(); const qc = useQueryClient();
  const docs = useDocumentos(id);
  const care = useQuery({
    queryKey: ["care", id],
    queryFn: async () => {
      try { return await api<CareData>(`/assets/${id}/care`); }
      catch (x) { if (x instanceof ApiError && (x.status === 404 || x.status === 501)) return null; throw x; }
    },
  });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["care", id] }); qc.invalidateQueries({ queryKey: ["asset", id] }); qc.invalidateQueries({ queryKey: ["care-all"] }); };

  const generar = useMutation({
    mutationFn: () => api<CareData>(`/assets/${id}/care/generate`, { method: "POST" }),
    onSuccess: (d) => qc.setQueryData(["care", id], d),
  });
  const intentado = useRef(false);
  useEffect(() => {
    if (ready && care.data && care.data.tasks.length === 0 && !intentado.current) { intentado.current = true; generar.mutate(); }
  }, [ready, care.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const [open, setOpen] = useState<string | null>(null);
  const [resched, setResched] = useState<string | null>(null);
  const [fecha, setFecha] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const accion = useMutation({
    mutationFn: async (a: { path: string; body?: unknown; ok?: (r: CareTask) => string }) => {
      const r = await api<CareTask>(a.path, { method: "POST", body: a.body ? JSON.stringify(a.body) : undefined });
      return { r, ok: a.ok };
    },
    onSuccess: ({ r, ok }) => { setErr(null); setResched(null); setAviso(ok && r ? ok(r) : null); refresh(); },
    onError: (x) => { setAviso(null); setErr((x as Error).message); },
  });
  const descartar = useMutation({
    mutationFn: (taskId: string) => api(`/care/${taskId}/dismiss`, { method: "POST" }),
    onSuccess: () => { setErr(null); setAviso("Listo, no te lo volveremos a sugerir."); refresh(); },
    onError: (x) => setErr((x as Error).message),
  });

  const warranty = docs.data?.warranty ?? null;
  const groups = groupByFrequency(care.data?.tasks ?? []);
  const unconfirmed = care.data && !care.data.model_confirmed;
  const preparando = generar.isPending || (ready && care.data?.tasks.length === 0 && !generar.isError && !generar.isSuccess);

  return (
    <div className="flex flex-col gap-5">
      {showWarrantyAlert(warranty) && warranty && (
        <div className="g flex items-center gap-3 rounded-[22px] p-3.5">
          <span className="icon-tile"><Icon name="shield" size={20} /></span>
          <div className="min-w-0 flex-1">
            <p className="text-[15px] font-extrabold">Garantía del fabricante</p>
            <p className="text-[13px] text-muted">{warrantyView(warranty).text}</p>
          </div>
          <span className="chip text-[var(--ng-warn)]"><Icon name="clock" size={13} stroke={2.4} />{warrantyView(warranty).badge}</span>
        </div>
      )}

      {groups.length > 0 && (
        <p className="flex items-start gap-2 px-1 text-[12.5px] text-muted"><Icon name="sparkle" size={14} />
          <span>{unconfirmed ? "Basado en datos sin confirmar: confirma marca y modelo para un plan más preciso. " : ""}
            Algunas sugerencias las genera la IA. Revisa el manual antes de seguirlas.</span></p>
      )}
      {aviso && <p role="status" className="px-1 text-[13px] font-bold text-[var(--ng-ok)]">{aviso}</p>}
      <ErrorNote text={err} />

      {groups.map((g) => (
        <section key={g.key} aria-label={g.label}>
          <h2 className="mb-2 px-1 text-[15px] font-extrabold text-navy">{g.label}</h2>
          <div className="flex flex-col gap-3">
            {g.tasks.map((t) => {
              const due = t.next_due ? dueLabel(t.next_due) : null;
              const porConfirmar = t.source === "sugerencia" && !t.confirmed;
              const ocupado = accion.isPending || descartar.isPending;
              return (
                <article key={t.id} className="g rounded-[22px] p-4">
                  <div className="flex items-start gap-3">
                    <span className="icon-tile"><Icon name="wrench" size={20} /></span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[15px] font-extrabold">{t.title}</p>
                      <p className="text-[13px] text-muted">
                        {everyShort(t.every)}{due ? <> · <span className={due.tone === "normal" ? "" : "font-bold text-[var(--ng-warn)]"}>{due.text}</span></> : null}
                      </p>
                      {t.detail && <p className="mt-0.5 text-[13px] text-muted">{t.detail}</p>}
                      <span className={`chip mt-2 ${t.source === "manual" || t.confirmed ? "text-[var(--ng-ok)]" : ""}`}>
                        <Icon name={t.source === "manual" || t.confirmed ? "check" : "sparkle"} size={13} stroke={2.4} />
                        {t.confirmed && t.source === "sugerencia" ? "Confirmado por ti" : SOURCE_LABEL[t.source]}</span>
                    </div>
                  </div>
                  <button type="button" aria-expanded={open === t.id} onClick={() => setOpen(open === t.id ? null : t.id)}
                    className="mt-3 flex h-10 w-full items-center justify-between rounded-full px-1 text-[14px] font-bold text-navy">
                    Ver instrucciones y opciones<Icon name="chevrondown" size={16} stroke={2.4} />
                  </button>
                  {open === t.id && (
                    <div className="flex flex-col gap-3 px-1 pb-1">
                      {t.instructions && <p className="whitespace-pre-line text-[14px] leading-relaxed text-[var(--ng-body)]">{t.instructions}</p>}
                      <div className="flex gap-2">
                        <button type="button" disabled={ocupado} className="btn !min-h-11 flex-1 !px-3 !text-[14px]"
                          onClick={() => accion.mutate({ path: `/care/${t.id}/done`, ok: (r) => `Listo. La próxima vez: ${dueLabel(r.next_due ?? "").text.replace("Próximo: ", "")}.` })}>
                          <Icon name="check" size={17} stroke={2.4} />Marcar como realizado</button>
                        <button type="button" disabled={ocupado} className="btn btn-ghost !min-h-11 !px-4 !text-[14px]"
                          onClick={() => { setResched(resched === t.id ? null : t.id); setFecha(t.next_due ?? hoyISO()); }}>Reprogramar</button>
                      </div>
                      {resched === t.id && (
                        <div className="flex items-center gap-2">
                          <label className="sr-only" htmlFor={`f-${t.id}`}>Nueva fecha</label>
                          <input id={`f-${t.id}`} type="date" className="field !min-h-11 flex-1" min={hoyISO()} value={fecha} onChange={(e) => setFecha(e.target.value)} />
                          <button type="button" disabled={ocupado || !fecha} className="btn !min-h-11 !px-4 !text-[14px]"
                            onClick={() => accion.mutate({ path: `/care/${t.id}/reschedule`, body: { next_due: fecha }, ok: () => "Listo, cambiamos la fecha." })}>Guardar</button>
                        </div>
                      )}
                      {porConfirmar && (
                        <div className="flex gap-2">
                          <button type="button" disabled={ocupado} className="btn btn-ghost !min-h-11 flex-1 !px-3 !text-[14px]"
                            onClick={() => accion.mutate({ path: `/care/${t.id}/confirm`, ok: () => "Gracias, lo marcamos como útil." })}>Me sirve</button>
                          <button type="button" disabled={ocupado} className="btn btn-ghost !min-h-11 flex-1 !px-3 !text-[14px]"
                            onClick={() => descartar.mutate(t.id)}>No aplica</button>
                        </div>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      ))}

      {groups.length === 0 && preparando && (
        <div className="g rounded-[26px] p-6 text-center" role="status">
          <span className="icon-tile mx-auto"><Icon name="sparkle" size={22} /></span>
          <p className="mt-3 text-[16px] font-extrabold">Estamos preparando el cuidado de tu equipo</p>
          <p className="mt-1 text-[13.5px] text-muted">Tarda unos segundos. Verás qué hacerle y cada cuánto: diario, semanal, mensual o anual.</p>
        </div>
      )}
      {groups.length === 0 && !preparando && !generar.isError && (
        <div className="g rounded-[26px] p-6 text-center">
          <span className="icon-tile mx-auto"><Icon name="heart" size={22} /></span>
          <p className="mt-3 text-[16px] font-extrabold">Aún no hay cuidados</p>
          <p className="mt-1 text-[13.5px] text-muted">{ready ? "Cuando la lectura de tu equipo termine, aquí verás qué hacerle y cada cuánto." : "Estamos leyendo la placa de tu equipo. En cuanto termine, prepararemos sus cuidados."}</p>
        </div>
      )}
      {generar.isError && (
        <div className="g rounded-[26px] p-6 text-center">
          <p className="text-[16px] font-extrabold">No pudimos preparar los cuidados</p>
          <p className="mt-1 text-[13.5px] text-muted">{(generar.error as Error).message}</p>
          <button type="button" className="btn mt-4" onClick={() => generar.mutate()}>Intentar de nuevo</button>
        </div>
      )}
    </div>
  );
}

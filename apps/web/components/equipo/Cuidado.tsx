"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/Icon";
import { ApiError, useApi } from "@/lib/api";
import { CareData, SOURCE_LABEL, everyShort, groupByFrequency, showWarrantyAlert, warrantyView } from "@/lib/care";
import { useDocumentos } from "./Documentos";

export function Cuidado({ id }: { id: string }) {
  const api = useApi();
  const docs = useDocumentos(id);
  const care = useQuery({
    queryKey: ["care", id],
    queryFn: async () => {
      try { return await api<CareData>(`/assets/${id}/care`); }
      catch (x) { if (x instanceof ApiError && (x.status === 404 || x.status === 501)) return null; throw x; }
    },
  });
  const [open, setOpen] = useState<string | null>(null);
  const warranty = docs.data?.warranty ?? null;
  const groups = groupByFrequency(care.data?.tasks ?? []);
  const unconfirmed = care.data && !care.data.model_confirmed;

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

      {groups.map((g) => (
        <section key={g.key} aria-label={g.label}>
          <h2 className="mb-2 px-1 text-[15px] font-extrabold text-navy">{g.label}</h2>
          <div className="flex flex-col gap-3">
            {g.tasks.map((t) => (
              <article key={t.id} className="g rounded-[22px] p-4">
                <div className="flex items-start gap-3">
                  <span className="icon-tile"><Icon name="wrench" size={20} /></span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] font-extrabold">{t.title}</p>
                    <p className="text-[13px] text-muted">
                      {everyShort(t.every)}{t.next_due ? ` · Próximo: ${new Date(`${t.next_due}T00:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short" }).replace(/\./g, "")}` : ""}
                    </p>
                    {t.detail && <p className="mt-0.5 text-[13px] text-muted">{t.detail}</p>}
                    <span className={`chip mt-2 ${t.source === "manual" ? "text-[var(--ng-ok)]" : ""}`}>
                      <Icon name={t.source === "manual" ? "check" : "sparkle"} size={13} stroke={2.4} />{SOURCE_LABEL[t.source]}</span>
                  </div>
                </div>
                {t.instructions && (
                  <>
                    <button type="button" aria-expanded={open === t.id} onClick={() => setOpen(open === t.id ? null : t.id)}
                      className="mt-3 flex h-10 w-full items-center justify-between rounded-full px-1 text-[14px] font-bold text-navy">
                      Ver instrucciones<Icon name="chevrondown" size={16} stroke={2.4} />
                    </button>
                    {open === t.id && <p className="whitespace-pre-line px-1 pb-1 text-[14px] leading-relaxed text-[var(--ng-body)]">{t.instructions}</p>}
                  </>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}

      {groups.length === 0 && (
        <div className="g rounded-[26px] p-6 text-center">
          <span className="icon-tile mx-auto"><Icon name="heart" size={22} /></span>
          <p className="mt-3 text-[16px] font-extrabold">Estamos preparando el cuidado de tu equipo</p>
          <p className="mt-1 text-[13.5px] text-muted">Cuando confirmes marca y modelo verás aquí qué hacerle: diario, semanal, mensual o anual, con la fuente de cada recomendación.</p>
        </div>
      )}
    </div>
  );
}

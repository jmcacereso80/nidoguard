"use client";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/Icon";
import { ErrorNote } from "@/components/Shell";
import { useApi } from "@/lib/api";
import { ServiceRequest } from "@/lib/servicios";

/** Cuidado que conviene hacer con un técnico: avisa y deja pedir cotizaciones. */
export function QuoteButton({ taskId, compact = false }: { taskId: string; compact?: boolean }) {
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const m = useMutation({
    mutationFn: () => api<ServiceRequest>(`/care/${taskId}/quote-request`, { method: "POST" }),
    onSuccess: (r) => { qc.setQueryData(["svc", r.id], r); qc.invalidateQueries({ queryKey: ["svc-list"] }); router.push(`/servicios/${r.id}`); },
  });
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-start gap-2.5 rounded-[18px] px-3 py-2.5" style={{ background: "rgba(193,139,88,.16)" }}>
        <span className="mt-px text-[#8F5A1F]"><Icon name="wrench" size={18} stroke={2.2} /></span>
        <p className="text-[13px] leading-snug text-[#5E3B12]"><b>Conviene que lo haga un técnico.</b>{compact ? "" : " Hay partes que es fácil dañar si no se tiene experiencia."}</p>
      </div>
      <button type="button" disabled={m.isPending} onClick={() => m.mutate()} className="btn btn-copper !min-h-11 w-full !text-[14px]"><Icon name="phone" size={17} stroke={2.2} />{m.isPending ? "Un momento…" : "Obtener cotización"}</button>
      {!compact && <p className="text-center text-[12px] text-muted">Llamamos a técnicos cercanos por ti y te mostramos hasta 5 cotizaciones.</p>}
      <ErrorNote text={m.isError ? (m.error as Error).message : null} />
    </div>
  );
}

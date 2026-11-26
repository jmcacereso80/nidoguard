"use client";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "@/components/Shell";
import { QuoteDetail } from "@/components/servicios/views";
import { useApi } from "@/lib/api";
import { Quote, distanceLabel } from "@/lib/servicios";

export default function Cotizacion({ params }: { params: Promise<{ id: string; qid: string }> }) {
  const { id, qid } = use(params);
  const api = useApi();
  const q = useQuery({ queryKey: ["svc-quote", id, qid], queryFn: () => api<{ quote: Quote; scope_text: string | null }>(`/service-requests/${id}/quotes/${qid}`) });
  const d = q.data;
  return (
    <Shell title={d?.quote.label ?? "Cotización"} subtitle={d ? [distanceLabel(d.quote.distance_km), d.quote.rating != null ? `${d.quote.rating.toFixed(1)} de 5 (${d.quote.reviews} reseñas)` : ""].filter(Boolean).join(" · ") : undefined}
      back={`/servicios/${id}`} nav="servicios">
      {q.isLoading && <p className="text-muted">Cargando…</p>}
      {q.isError && <p role="alert" className="g rounded-2xl p-4 text-sm font-bold text-[var(--ng-danger)]">No encontramos esta cotización.</p>}
      {d && <QuoteDetail q={d.quote} scope={d.scope_text} rid={id} />}
    </Shell>
  );
}

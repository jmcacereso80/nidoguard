"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/lib/api";
import { ServiceRequest, shouldPoll } from "@/lib/servicios";

/** La solicitud, con avance automático mientras se busca o la visita espera confirmación. */
export function useRequest(id: string) {
  const api = useApi();
  return useQuery({
    queryKey: ["svc", id], queryFn: () => api<ServiceRequest>(`/service-requests/${id}`),
    refetchInterval: (q) => (shouldPoll(q.state.data) ? 4000 : false),
  });
}

/** Acción POST sobre la solicitud: guarda la respuesta en caché y refresca la lista. */
export function useRequestAction(id: string) {
  const api = useApi(); const qc = useQueryClient();
  return useMutation({
    mutationFn: (a: { path: string; body?: unknown }) => api<ServiceRequest>(a.path.replace("{id}", id), { method: "POST", body: a.body ? JSON.stringify(a.body) : undefined }),
    onSuccess: (d) => { qc.setQueryData(["svc", id], d); qc.invalidateQueries({ queryKey: ["svc-list"] }); },
  });
}

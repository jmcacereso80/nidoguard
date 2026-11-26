"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Asset, useApi } from "@/lib/api";

const LABEL: Record<string, string> = {
  registrado: "Leyendo la placa…", leido: "Listo para revisar", por_confirmar: "Listo para confirmar",
  necesita_foto: "Necesita otra foto", faltan_datos: "Faltan datos",
};

export default function PorConfirmar() {
  const api = useApi(); const qc = useQueryClient();
  const list = useQuery({ queryKey: ["pending"], queryFn: () => api<Asset[]>("/assets?status=por_confirmar"), refetchInterval: 8000 });
  const [err, setErr] = useState<string | null>(null);
  const ready = list.data?.filter((a) => a.status === "por_confirmar") ?? [];
  async function confirm(ids: string[]) {
    setErr(null);
    try {
      await api("/assets/confirm-bulk", { method: "POST", body: JSON.stringify({ ids }) });
      qc.invalidateQueries({ queryKey: ["pending"] });
    } catch (x) { setErr((x as Error).message); }
  }
  return (
    <Shell title="Por confirmar" back="/inicio">
      {ready.length > 1 && <button className="btn mb-4 w-full" onClick={() => confirm(ready.map((a) => a.id))}>Confirmar los {ready.length} listos</button>}
      <div className="flex flex-col gap-3">
        {list.data?.map((a) => (
          <Card key={a.id}>
            <Link href={`/equipos/${a.id}`} className="font-bold text-navy">{a.name}</Link>
            <p className="text-sm text-ink/70">{[a.brand, a.model].filter(Boolean).join(" · ") || LABEL[a.status]}</p>
            {a.status === "por_confirmar" && <button className="btn mt-3 w-full" onClick={() => confirm([a.id])}>Confirmar</button>}
            {a.status !== "por_confirmar" && <Link href={`/equipos/${a.id}`} className="btn btn-ghost mt-3 w-full">{LABEL[a.status]}</Link>}
          </Card>
        ))}
        {list.data?.length === 0 && <Card><p>No tienes nada pendiente. 🎉</p></Card>}
      </div>
      <ErrorNote text={err} />
    </Shell>
  );
}

"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Icon, equipmentIcon } from "@/components/Icon";
import { Asset, Space, useApi } from "@/lib/api";

const CHIP: Record<string, { t: string; ok?: boolean }> = {
  registrado: { t: "Leyendo…" }, leido: { t: "Por revisar" }, por_confirmar: { t: "Lista", ok: true },
  necesita_foto: { t: "Foto borrosa" }, faltan_datos: { t: "Faltan datos" },
};
const CTA: Record<string, string> = { necesita_foto: "Tomar otra foto", faltan_datos: "Completar", leido: "Revisar", registrado: "Ver" };

export default function PorConfirmar() {
  const api = useApi(); const qc = useQueryClient();
  const list = useQuery({ queryKey: ["pending"], queryFn: () => api<Asset[]>("/assets?status=por_confirmar"), refetchInterval: 8000 });
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });
  const place = new Map((spaces.data ?? []).map((s) => [s.id, s.name]));
  const [err, setErr] = useState<string | null>(null);
  const ready = list.data?.filter((a) => a.status === "por_confirmar") ?? [];
  async function confirm(ids: string[]) {
    setErr(null);
    try {
      await api("/assets/confirm-bulk", { method: "POST", body: JSON.stringify({ ids }) });
      qc.invalidateQueries({ queryKey: ["pending"] }); qc.invalidateQueries({ queryKey: ["assets"] });
    } catch (x) { setErr((x as Error).message); }
  }
  return (
    <Shell title="Por confirmar" subtitle="Ya leímos los datos. Revísalos con un toque." back="/inicio" nav="inicio">
      {ready.length > 1 && <button className="btn mb-4 w-full" onClick={() => confirm(ready.map((a) => a.id))}><Icon name="check" size={18} stroke={2.6} />Confirmar los {ready.length} que están listos</button>}
      <div className="flex flex-col gap-3">
        {list.data?.map((a) => {
          const c = CHIP[a.status] ?? { t: a.status };
          const data = [a.brand, a.model].filter(Boolean).join(" · ");
          return (
            <Card key={a.id} className="!p-4">
              <div className="flex items-center gap-3">
                <span className="icon-tile"><Icon name={equipmentIcon(a)} size={20} /></span>
                <Link href={`/equipos/${a.id}`} className="min-w-0 flex-1"><span className="block text-[16px] font-extrabold leading-tight">{a.name}</span><span className="block text-[12.5px] text-muted">{place.get(a.space_id ?? "") ?? ""}</span></Link>
                <span className={`chip ${c.ok ? "!bg-[rgba(47,107,74,.14)] !text-[var(--ng-ok)]" : "!bg-[rgba(193,139,88,.22)] !text-[var(--ng-warn)]"}`}>{c.ok && <Icon name="check" size={13} stroke={2.6} />}{c.t}</span>
              </div>
              <p className="mt-2.5 text-[13px] leading-snug text-[var(--ng-body)]">{data ? `Leímos: ${data}${a.serial ? `, serie ${a.serial}` : ""}.` : "Todavía no tenemos datos de este equipo."}</p>
              <div className="mt-3 flex gap-2.5">
                {a.status === "por_confirmar"
                  ? <button className="btn !min-h-11 flex-1 !text-[15px]" onClick={() => confirm([a.id])}>Confirmar</button>
                  : <Link href={`/equipos/${a.id}`} className="btn !min-h-11 flex-1 !text-[15px]">{CTA[a.status] ?? "Ver"}</Link>}
                <Link href={`/equipos/${a.id}`} className="btn btn-ghost !min-h-11 flex-1 !text-[15px]">{a.status === "por_confirmar" ? "Editar" : "Escribir a mano"}</Link>
              </div>
            </Card>
          );
        })}
        {list.data?.length === 0 && <Card><p className="font-extrabold">No tienes nada pendiente.</p><p className="text-sm text-muted">Cuando registres equipos nuevos, aparecen aquí para confirmarlos.</p></Card>}
      </div>
      <ErrorNote text={err} />
    </Shell>
  );
}

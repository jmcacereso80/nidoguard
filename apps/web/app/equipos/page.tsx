"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "@/components/Shell";
import { Icon, equipmentIcon } from "@/components/Icon";
import { Asset, Space, useApi } from "@/lib/api";
import { statusInfo } from "@/lib/assetStatus";

function Lista() {
  const api = useApi();
  const sp = useSearchParams();
  const [q, setQ] = useState("");
  const [space, setSpace] = useState(sp.get("espacio") ?? "");
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => api<Asset[]>("/assets") });
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });
  const byId = new Map((spaces.data ?? []).map((s) => [s.id, s.name]));
  const term = q.trim().toLowerCase();
  const shown = (assets.data ?? []).filter((a) => (!space || a.space_id === space) &&
    (!term || [a.name, a.brand, a.model].some((v) => v?.toLowerCase().includes(term))));
  return (
    <Shell title="Equipos" big nav="equipos" right={<Link href="/escanear" className="btn !min-h-10 !px-4 !text-sm"><Icon name="plus" size={16} stroke={2.4} />Agregar</Link>}>
      <label className="g mt-4 flex h-[52px] items-center gap-2.5 rounded-[26px] px-4 text-muted">
        <Icon name="search" size={20} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por nombre, marca o modelo" aria-label="Buscar equipos" className="w-full bg-transparent text-[15px] font-semibold text-ink outline-none placeholder:font-medium placeholder:text-muted" />
      </label>
      <div className="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 pb-1">
        {[{ id: "", name: "Todos" }, ...(spaces.data ?? [])].map((s) => (
          <button key={s.id} onClick={() => setSpace(s.id)} aria-pressed={space === s.id}
            className={`h-10 flex-none rounded-full px-4 text-sm font-bold ${space === s.id ? "gd" : "g text-navy"}`} style={{ borderRadius: 999 }}>{s.name}</button>
        ))}
      </div>
      <p className="mb-3 mt-3 text-[13px] font-semibold text-muted">{shown.length} {shown.length === 1 ? "equipo" : "equipos"}</p>
      {assets.isSuccess && shown.length === 0 && <div className="g rounded-[26px] p-5 text-sm text-muted">{assets.data.length ? "No encontramos equipos con ese filtro." : "Aún no registras equipos. Toca Agregar para empezar."}</div>}
      <div className="grid grid-cols-2 gap-3">
        {shown.map((a, i) => (
          <Link key={a.id} href={`/equipos/${a.id}`} className="g flex min-h-[190px] flex-col justify-between rounded-[26px] p-3.5"
                style={{ background: ((i + Math.floor(i / 2)) % 2) ? "linear-gradient(145deg,rgba(241,226,211,.85),rgba(227,195,163,.7))" : "linear-gradient(145deg,rgba(228,237,244,.8),rgba(185,207,224,.7))" }}>
            <span className="grid h-20 place-items-center text-navy"><Icon name={equipmentIcon(a)} size={44} stroke={1.5} /></span>
            <span><span className="block text-base font-extrabold leading-tight">{a.name}</span><span className="block text-[12.5px] text-muted">{byId.get(a.space_id ?? "") ?? ""}</span>
              <span className={`mt-1.5 flex items-center gap-1 text-[12px] font-bold ${statusInfo(a.status).tone === "ok" ? "text-[var(--ng-ok)]" : statusInfo(a.status).tone === "action" ? "text-[var(--ng-warn)]" : "text-muted"}`}><Icon name={statusInfo(a.status).tone === "ok" ? "check" : "clock"} size={13} stroke={2.4} />{statusInfo(a.status).label}</span></span>
          </Link>
        ))}
      </div>
    </Shell>
  );
}

export default function Equipos() { return <Suspense><Lista /></Suspense>; }

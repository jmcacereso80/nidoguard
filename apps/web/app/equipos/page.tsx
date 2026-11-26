"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Shell, Card } from "@/components/Shell";
import { Asset, useApi } from "@/lib/api";
import { statusInfo } from "@/lib/assetStatus";

// Lista de todos los equipos del hogar, confirmados o no.
export default function Equipos() {
  const api = useApi();
  const q = useQuery({ queryKey: ["assets"], queryFn: () => api<Asset[]>("/assets") });
  const items = q.data ?? [];

  return (
    <Shell title="Mis equipos" back="/inicio">
      {q.isLoading && <p className="text-muted">Cargando…</p>}
      {!q.isLoading && items.length === 0 && (
        <Card className="flex flex-col gap-3">
          <p className="font-extrabold text-ink">Todavía no tienes equipos.</p>
          <p className="text-sm text-muted">Pega una etiqueta de tu kit en un equipo, escanéala y registra sus datos.</p>
          <Link href="/escanear" className="btn btn-copper w-full">Agregar un equipo</Link>
        </Card>
      )}
      <div className="flex flex-col gap-3">
        {items.map((a) => {
          const info = statusInfo(a.status);
          const tone = info.tone === "ok" ? "text-[var(--ng-ok)]" : info.tone === "action" ? "text-[var(--ng-warn)]" : "text-muted";
          const detalle = [a.brand, a.model].filter(Boolean).join(" · ");
          return (
            <Link key={a.id} href={`/equipos/${a.id}`} className="g flex items-center gap-3 rounded-[22px] px-4 py-3.5">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[16px] font-bold text-navy">{a.name}</span>
                <span className="block truncate text-[13px] text-muted">{detalle || "Sin marca ni modelo todavía"}</span>
              </span>
              <span className={`text-right text-[12px] font-bold ${tone}`}>{info.label}</span>
            </Link>
          );
        })}
      </div>
    </Shell>
  );
}

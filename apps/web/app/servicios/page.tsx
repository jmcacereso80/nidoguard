"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { Chip } from "@/components/servicios/ui";
import { useApi } from "@/lib/api";
import { ServiceRequest, isLive, statusChip } from "@/lib/servicios";

function Row({ r }: { r: ServiceRequest }) {
  const s = statusChip(r);
  return (
    <Link href={`/servicios/${r.id}`} className="g block rounded-[26px] p-4">
      <div className="flex items-start gap-3">
        <span className="icon-tile"><Icon name={r.route === "fabricante" ? "building" : "wrench"} size={20} /></span>
        <div className="min-w-0 flex-1"><p className="text-[15px] font-extrabold leading-snug">{r.scope_text ?? r.equipment_label}</p>
          <p className="mt-0.5 text-[12.5px] text-muted">{r.equipment_label}</p></div>
        <Icon name="chevron" size={18} />
      </div>
      <div className="mt-2.5"><Chip tone={s.tone} icon={s.icon}>{s.text}</Chip></div>
    </Link>
  );
}

export default function Servicios() {
  const api = useApi();
  const q = useQuery({ queryKey: ["svc-list"], queryFn: () => api<{ requests: ServiceRequest[] }>("/service-requests"),
    refetchInterval: (x) => (x.state.data?.requests.some((r) => r.status === "buscando") ? 5000 : false) });
  const all = q.data?.requests ?? [];
  const live = all.filter((r) => isLive(r.status)), past = all.filter((r) => !isLive(r.status) && r.status !== "cancelada");
  return (
    <Shell title="Servicios" subtitle="Tus solicitudes y visitas." big nav="servicios">
      <Link href="/servicios/nuevo" className="btn mt-1 w-full"><Icon name="plus" size={19} stroke={2.4} />Pedir un servicio</Link>
      {q.isSuccess && all.length === 0 && (
        <div className="g mt-4 rounded-[26px] p-6 text-center">
          <span className="icon-tile mx-auto"><Icon name="headset" size={22} /></span>
          <p className="mt-3 text-[16px] font-extrabold">Aún no pides ningún servicio</p>
          <p className="mt-1 text-[13.5px] text-muted">Cuéntanos qué le pasa a un equipo y llamamos a técnicos cercanos por ti. NidoGuard no cobra por el servicio: pagas directo al técnico.</p>
        </div>
      )}
      {live.length > 0 && <><h2 className="mb-2 mt-5 px-1 text-[17px] font-extrabold">En curso</h2><div className="flex flex-col gap-2.5">{live.map((r) => <Row key={r.id} r={r} />)}</div></>}
      {past.length > 0 && <><h2 className="mb-2 mt-5 px-1 text-[17px] font-extrabold">Terminadas</h2><div className="flex flex-col gap-2.5">{past.map((r) => <Row key={r.id} r={r} />)}</div></>}
    </Shell>
  );
}

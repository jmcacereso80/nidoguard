"use client";
import { use, useState } from "react";
import { Shell } from "@/components/Shell";
import { useRequest, useRequestAction } from "@/components/servicios/hooks";
import { Alerta, Cerrada, CitaFabricante, Comparar, Confirmar, FabricanteDatos, FabricanteLlamando, FabricanteManual, Progreso, SinRespuesta, Visita } from "@/components/servicios/views";
import { ServiceRequest } from "@/lib/servicios";

function meta(r: ServiceRequest, verCotizaciones: boolean): { title: string; sub?: string } {
  if (r.status === "borrador") return r.safety && !r.safety.acknowledged ? { title: "Antes de seguir", sub: "Tu seguridad primero" }
    : r.route === "fabricante" ? { title: "Servicio con el fabricante", sub: r.equipment_label ?? undefined } : { title: "Esto vamos a cotizar", sub: "Revísalo antes de llamar" };
  if (r.status === "buscando") return r.route === "fabricante" ? { title: "Llamando al fabricante", sub: r.equipment_label ?? undefined }
    : verCotizaciones ? { title: "Tus cotizaciones", sub: `${r.quote_count} hasta ahora` } : { title: "Buscando cotizaciones", sub: r.equipment_label ?? undefined };
  if (r.status === "lista") return { title: "Tus cotizaciones", sub: `${r.quote_count} técnicos cotizaron` };
  if (r.status === "sin_respuesta") return { title: "Sin cotizaciones todavía", sub: r.equipment_label ?? undefined };
  if (r.status === "sin_cita") return { title: "No pudimos agendar", sub: r.equipment_label ?? undefined };
  if (r.status === "agendada") return r.appointment?.kind === "fabricante" ? { title: "Cita agendada", sub: r.equipment_label ?? undefined }
    : r.appointment?.status === "confirmada" ? { title: "Visita confirmada", sub: r.equipment_label ?? undefined } : { title: "Visita pedida", sub: r.equipment_label ?? undefined };
  return { title: r.status === "terminada" ? "Servicio terminado" : "Solicitud cancelada", sub: r.equipment_label ?? undefined };
}

export default function Solicitud({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useRequest(id); const m = useRequestAction(id);
  const [ver, setVer] = useState(false);
  if (q.isLoading) return <Shell title="Servicios" back="/servicios" nav="servicios"><p className="text-muted">Cargando…</p></Shell>;
  if (q.isError || !q.data) return <Shell title="Servicios" back="/servicios" nav="servicios"><p role="alert" className="g rounded-2xl p-4 text-sm font-bold text-[var(--ng-danger)]">No encontramos esta solicitud.</p></Shell>;
  const r = q.data;
  const act = (path: string, body?: unknown) => m.mutateAsync({ path, body }).catch(() => undefined);
  const p = { r, act, busy: m.isPending, err: m.isError ? (m.error as Error).message : null };
  const { title, sub } = meta(r, ver);
  let view: React.ReactNode;
  if (r.status === "borrador") view = r.safety && !r.safety.acknowledged ? <Alerta {...p} /> : r.route === "fabricante" ? <FabricanteDatos {...p} /> : <Confirmar {...p} />;
  else if (r.status === "buscando") view = r.route === "fabricante" ? <FabricanteLlamando {...p} /> : ver && r.quote_count > 0 ? <Comparar r={r} act={act} /> : <Progreso {...p} onSee={() => setVer(true)} />;
  else if (r.status === "lista") view = <Comparar r={r} act={act} />;
  else if (r.status === "sin_respuesta") view = <SinRespuesta {...p} />;
  else if (r.status === "sin_cita") view = <FabricanteManual {...p} />;
  else if (r.status === "agendada" && r.appointment) view = r.appointment.kind === "fabricante" ? <CitaFabricante {...p} /> : <Visita {...p} />;
  else view = <Cerrada r={r} />;
  return <Shell title={title} subtitle={sub} back={ver && r.status === "buscando" ? undefined : "/servicios"} nav="servicios">{view}</Shell>;
}

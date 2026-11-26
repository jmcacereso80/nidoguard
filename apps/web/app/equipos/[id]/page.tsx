"use client";
import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Asset, useApi } from "@/lib/api";

type Detail = Asset & {
  reading: { status: string; source: string; fields: Record<string, string>; confidence: Record<string, number>; confirmed: boolean } | null;
  events: { type: string; at: string; payload: Record<string, unknown> }[];
};
const EVENT: Record<string, string> = { registro: "Registrado", lectura_ia: "Placa leída", confirmado: "Datos confirmados", datos_manuales: "Datos escritos a mano" };

export default function Equipo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const api = useApi(); const qc = useQueryClient();
  const q = useQuery({ queryKey: ["asset", id], queryFn: () => api<Detail>(`/assets/${id}`) });
  const [form, setForm] = useState({ brand: "", model: "", serial: "" });
  const [err, setErr] = useState<string | null>(null);
  const a = q.data;
  if (!a) return <Shell title="Equipo" back="/inicio"><p>Cargando…</p></Shell>;
  const needs = a.status !== "completo";

  async function save(path: "manual" | "confirm", body: object) {
    setErr(null);
    try { await api(`/assets/${id}/${path}`, { method: path === "manual" ? "PATCH" : "POST", body: JSON.stringify(body) });
      qc.invalidateQueries({ queryKey: ["asset", id] }); qc.invalidateQueries({ queryKey: ["pending"] }); }
    catch (x) { setErr((x as Error).message); }
  }
  return (
    <Shell title={a.name} back="/inicio">
      <div className="flex flex-col gap-4">
        <Card>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            {([["Marca", a.brand], ["Modelo", a.model], ["Serie", a.serial], ["Tipo", a.category]] as const).map(([k, v]) => (
              <div key={k} className="contents"><dt className="text-muted">{k}</dt><dd className="font-semibold">{v ?? "—"}</dd></div>
            ))}
          </dl>
          {a.status === "por_confirmar" && <button className="btn mt-4 w-full" onClick={() => save("confirm", {})}>Confirmar datos</button>}
          {a.status === "necesita_foto" && <p className="mt-3 text-sm text-[var(--ng-warn)]">La foto no se leyó bien. Escribe los datos o toma otra foto.</p>}
        </Card>
        {needs && (
          <Card className="flex flex-col gap-3">
            <p className="font-extrabold text-ink">Escribir los datos a mano</p>
            {(["brand", "model", "serial"] as const).map((k) => (
              <input key={k} className="field" placeholder={{ brand: "Marca", model: "Modelo", serial: "Número de serie" }[k]}
                     value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            ))}
            <button className="btn btn-ghost" onClick={() => save("manual", Object.fromEntries(Object.entries(form).filter(([, v]) => v.trim())))}>Guardar datos</button>
          </Card>
        )}
        <Card>
          <p className="mb-2 font-extrabold text-ink">Historial</p>
          <ol className="flex flex-col gap-2 text-sm">
            {a.events.map((e, i) => <li key={i}><span className="font-semibold">{EVENT[e.type] ?? e.type}</span> · {new Date(e.at).toLocaleDateString("es-MX")}</li>)}
          </ol>
        </Card>
        <ErrorNote text={err} />
      </div>
    </Shell>
  );
}
